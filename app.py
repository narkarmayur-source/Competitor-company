import streamlit as st
import pandas as pd
import requests
import time
import google.generativeai as genai
from duckduckgo_search import DDGS

st.set_page_config(layout="wide")
st.title("AI Sales Agent (Apollo + Gemini)")

# Securely load both API keys
apollo_key = st.secrets.get("APOLLO_API_KEY")
gemini_key = st.secrets.get("GEMINI_API_KEY")

# Initialize Gemini if the key is present
if gemini_key:
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.error("⚠️ GEMINI_API_KEY is missing from Streamlit Secrets.")

st.write("### 1. Configure Your Pitch")
st.caption("Tell the AI what you are selling so it can write your emails.")
my_pitch = st.text_area("Product/Service Description:", "A software tool that helps HR teams automate their candidate sourcing process.")

st.write("### 2. Upload your list")
uploaded_file = st.file_uploader("Choose a CSV file containing company names", type=["csv"])

def find_company_column(df):
    possible_names = ['company', 'organization', 'account', 'client', 'name', 'employer', 'brand']
    for col in df.columns:
        if str(col).lower().strip() in possible_names:
            return col
    return df.columns[0]

# Initialize spreadsheet with the new Draft Email column
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(
        columns=["Company", "Careers Page", "Contact Name", "Job Title", "Contact Email", "LinkedIn Profile", "Draft Email", "Status", "My Notes"]
    )

if uploaded_file is not None and "file_loaded" not in st.session_state:
    uploaded_df = pd.read_csv(uploaded_file)
    company_col = find_company_column(uploaded_df)
    uploaded_df.rename(columns={company_col: "Company"}, inplace=True)
    
    for col in ["Careers Page", "Contact Name", "Job Title", "Contact Email", "LinkedIn Profile", "Draft Email", "Status", "My Notes"]:
        if col not in uploaded_df.columns:
            uploaded_df[col] = ""
            
    st.session_state.df = uploaded_df
    st.session_state.file_loaded = True

def get_careers_page(company):
    try:
        ddgs = DDGS()
        results = ddgs.text(f'"{company}" official site careers OR jobs', max_results=1)
        if results:
            return results[0]['href']
    except:
        pass
    return ""

def search_apollo(company_name, api_key):
    url = "https://api.apollo.io/v1/mixed_people/search"
    headers = {
        'Cache-Control': 'no-cache',
        'Content-Type': 'application/json',
        'X-Api-Key': api_key
    }
    payload = {
        "q_keywords": company_name,
        "person_titles": ["HR", "Recruiter", "Human Resources", "Talent Acquisition", "Talent", "HR Manager"],
        "per_page": 1
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'people' in data and len(data['people']) > 0:
                return data['people'][0]
            elif 'contacts' in data and len(data['contacts']) > 0:
                return data['contacts'][0]
    except Exception as e:
        pass
    return None

def write_email(name, title, company, pitch):
    prompt = f"""
    Write a concise, 3-sentence B2B cold email to {name}, who is the {title} at {company}.
    Context: I am selling {pitch}.
    Goal: Get them interested in a quick chat.
    Tone: Professional, direct, and completely natural. 
    Rule: Do not include a Subject line. Do not include placeholder brackets like [Your Name]. Just write the core email body.
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except:
        return "Error generating email."

def enrich_data(df, ap_key, pitch_text):
    for index, row in df.iterrows():
        company = str(row["Company"]).strip()
        
        if pd.isna(company) or company == "":
            continue
            
        st.toast(f"Extracting data & writing email for {company}...")
        
        # 1. Get Careers Page
        if pd.isna(row["Careers Page"]) or str(row["Careers Page"]).strip() == "":
            df.at[index, "Careers Page"] = get_careers_page(company)
            time.sleep(1)
            
        # 2. Get Apollo Data
        if pd.isna(row["Contact Name"]) or str(row["Contact Name"]).strip() == "":
            person = search_apollo(company, ap_key)
            
            if person:
                first_name = person.get('first_name', '')
                last_name = person.get('last_name', '')
                name = f"{first_name} {last_name}".strip()
                title = person.get('title', '')
                
                df.at[index, "Contact Name"] = name
                df.at[index, "Job Title"] = title
                df.at[index, "LinkedIn Profile"] = person.get('linkedin_url', '')
                
                apollo_email = person.get('email', '')
                if apollo_email and apollo_email != "":
                    df.at[index, "Contact Email"] = apollo_email
                else:
                    domain = str(df.at[index, "Careers Page"]).split('/')[2].replace('www.', '') if df.at[index, "Careers Page"] != "" else "company.com"
                    df.at[index, "Contact Email"] = f"{first_name.lower()}.{last_name.lower()}@{domain}"
                
                # 3. Ask Gemini to write the custom email
                if gemini_key:
                    df.at[index, "Draft Email"] = write_email(name, title, company, pitch_text)
                
                st.toast(f"✅ Full profile and email generated for {company}")
            else:
                st.toast(f"⚠️ No HR match found on Apollo for {company}")
                
            time.sleep(1.5)
            
    return df

st.write("### 3. Run the Agent")
if not apollo_key:
    st.error("⚠️ APOLLO_API_KEY is missing from Streamlit Secrets.")
else:
    if st.button("Fetch Leads & Write Emails", type="primary"):
        with st.spinner("Extracting data and generating AI emails..."):
            st.session_state.df = enrich_data(st.session_state.df, apollo_key, my_pitch)
            st.success("Complete! Scroll down to see your drafts.")

st.write("### 4. Your Leads Database")
st.session_state.df = st.data_editor(
    st.session_state.df,
    num_rows="dynamic",
    use_container_width=True
)

csv = st.session_state.df.to_csv(index=False).encode('utf-8')
st.download_button(
    label="Download Complete Spreadsheet",
    data=csv,
    file_name='ai_sales_leads.csv',
    mime='text/csv',
)
