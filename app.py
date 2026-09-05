import streamlit as st
import pandas as pd
import time
import requests
import google.generativeai as genai
from duckduckgo_search import DDGS

st.set_page_config(layout="wide")
st.title("Deep Search B2B Lead Generator")

# Connect to Gemini securely
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
    ai_ready = True
except Exception as e:
    ai_ready = False
    st.error("⚠️ AI Key not found. Please add GEMINI_API_KEY to your Streamlit Secrets.")

st.write("### 1. Upload your list")
uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])

def find_company_column(df):
    possible_names = ['company', 'organization', 'account', 'client', 'name', 'employer', 'brand']
    for col in df.columns:
        if str(col).lower().strip() in possible_names:
            return col
    return df.columns[0]

def verify_link(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        return response.status_code == 200
    except:
        return False

# Initialize the spreadsheet
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(
        columns=["Company", "Careers Page", "Contact Name", "LinkedIn Profile", "Email Guess", "Status", "My Notes"]
    )

if uploaded_file is not None and "file_loaded" not in st.session_state:
    uploaded_df = pd.read_csv(uploaded_file)
    company_col = find_company_column(uploaded_df)
    uploaded_df.rename(columns={company_col: "Company"}, inplace=True)
    
    for col in ["Careers Page", "Contact Name", "LinkedIn Profile", "Email Guess", "Status", "My Notes"]:
        if col not in uploaded_df.columns:
            uploaded_df[col] = ""
            
    st.session_state.df = uploaded_df
    st.session_state.file_loaded = True

def enrich_data(df):
    ddgs = DDGS()
    for index, row in df.iterrows():
        company = str(row["Company"]).strip()
        
        if pd.isna(company) or company == "":
            continue
            
        st.toast(f"Extensive search started for {company}...")
        
        # AGENT TASK 1: Find Careers Page
        if pd.isna(row["Careers Page"]) or str(row["Careers Page"]).strip() == "":
            try:
                c_results = ddgs.text(f'{company} official site careers OR jobs', max_results=3)
                for result in c_results:
                    if verify_link(result['href']):
                        df.at[index, "Careers Page"] = result['href']
                        break
            except:
                pass
            time.sleep(2)
            
        # AGENT TASK 2: Deep LinkedIn Search
        if ai_ready and (pd.isna(row["Contact Name"]) or str(row["Contact Name"]).strip() == ""):
            try:
                # Broadened the search query and increased max_results to 10
                search_query = f'{company} (HR OR Recruiter OR "Talent Acquisition" OR "Human Resources") site:linkedin.com/in/'
                li_results = ddgs.text(search_query, max_results=10)
                
                match_found = False
                if li_results:
                    for result in li_results:
                        snippet = str(result['body'])
                        title = str(result['title'])
                        
                        # Gemini Prompt is now more forgiving
                        prompt = f"""
                        You are a lead generation assistant. 
                        Read this LinkedIn profile search snippet: "{snippet}" and Title: "{title}"
                        Does this text suggest this person currently works in HR, Recruiting, or Talent Acquisition at a company related to '{company}'?
                        Reply with EXACTLY the word YES or NO.
                        """
                        
                        ai_response = model.generate_content(prompt).text.strip().upper()
                        
                        if "YES" in ai_response:
                            # Extract name cleanly
                            clean_name = title.split('-')[0].split('|')[0].replace('LinkedIn', '').strip()
                            df.at[index, "Contact Name"] = clean_name
                            df.at[index, "LinkedIn Profile"] = result['href']
                            
                            # Guess Email
                            domain = str(df.at[index, "Careers Page"]).split('/')[2].replace('www.', '') if not pd.isna(df.at[index, "Careers Page"]) and df.at[index, "Careers Page"] != "" else "company.com"
                            df.at[index, "Email Guess"] = f"{clean_name.lower().replace(' ', '.')}@{domain}"
                            
                            match_found = True
                            st.toast(f"✅ Found contact for {company}!")
                            break # Found a match, stop looking through the 10 results
                            
                if not match_found:
                    st.toast(f"⚠️ Checked 10 profiles for {company} but found no exact HR match.")
            except Exception as e:
                st.toast(f"Error searching {company}: {e}")
                pass
            time.sleep(3) # Pause longer to avoid getting blocked during deep searches
            
    return df

st.write("### 2. Run the Agent")
if st.button("Run AI Agent (Deep Search)", type="primary"):
    with st.spinner("Executing deep search and AI verification... this will take a moment."):
        st.session_state.df = enrich_data(st.session_state.df)
        st.success("Deep search complete!")

st.write("### 3. Your Leads Database")
st.session_state.df = st.data_editor(
    st.session_state.df,
    num_rows="dynamic",
    use_container_width=True
)

csv = st.session_state.df.to_csv(index=False).encode('utf-8')
st.download_button(
    label="Download Updated Spreadsheet",
    data=csv,
    file_name='deep_search_leads.csv',
    mime='text/csv',
)
