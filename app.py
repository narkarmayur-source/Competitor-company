import streamlit as st
import pandas as pd
import time
from duckduckgo_search import DDGS

st.set_page_config(layout="wide")
st.title("Free B2B Lead Generator")

st.write("### 1. Upload your list")
st.caption("Upload a CSV file. It MUST have a column named exactly 'Company' (with a capital C).")

# Add the File Uploader
uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])

# Initialize the spreadsheet
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(
        columns=["Company", "Careers Page", "Contact Name", "LinkedIn Profile", "Email Guess", "Status", "My Notes"]
    )

# If a file is uploaded, load it into the app
if uploaded_file is not None and "file_loaded" not in st.session_state:
    uploaded_df = pd.read_csv(uploaded_file)
    
    # Check if the column is named correctly
    if "Company" in uploaded_df.columns:
        # Add the agent columns if they don't exist yet
        for col in ["Careers Page", "Contact Name", "LinkedIn Profile", "Email Guess", "Status", "My Notes"]:
            if col not in uploaded_df.columns:
                uploaded_df[col] = ""
        st.session_state.df = uploaded_df
        st.session_state.file_loaded = True
    else:
        st.error("Error: Your uploaded file does not have a column named 'Company'. Please fix your file and re-upload.")

def enrich_data(df):
    ddgs = DDGS()
    for index, row in df.iterrows():
        company = row["Company"]
        
        # Skip empty rows
        if pd.isna(company) or str(company).strip() == "":
            continue
            
        st.toast(f"Agent searching for {company}...")
        
        # Search for Careers Page
        if pd.isna(row["Careers Page"]) or str(row["Careers Page"]).strip() == "":
            try:
                c_results = ddgs.text(f'"{company}" official site careers OR jobs', max_results=1)
                if c_results:
                    df.at[index, "Careers Page"] = c_results[0]['href']
            except:
                pass
            time.sleep(2) # Pausing slightly longer to prevent getting blocked
            
        # Search for HR on LinkedIn (Tweaked for better accuracy)
        if pd.isna(row["Contact Name"]) or str(row["Contact Name"]).strip() == "":
            try:
                li_results = ddgs.text(f'site:linkedin.com/in/ "{company}" HR OR Recruiter', max_results=1)
                if li_results:
                    title = li_results[0]['title']
                    name = title.split('-')[0].split('|')[0].strip()
                    df.at[index, "Contact Name"] = name
                    df.at[index, "LinkedIn Profile"] = li_results[0]['href']
                    
                    # Guess Email
                    domain = str(df.at[index, "Careers Page"]).split('/')[2].replace('www.', '') if not pd.isna(df.at[index, "Careers Page"]) and df.at[index, "Careers Page"] != "" else "company.com"
                    df.at[index, "Email Guess"] = f"{name.lower().replace(' ', '.')}@{domain}"
            except:
                pass
            time.sleep(2)
            
    return df

st.write("### 2. Run the Agent")
if st.button("Run AI Agent (Search Web)", type="primary"):
    with st.spinner("Scraping search results... Please wait."):
        st.session_state.df = enrich_data(st.session_state.df)
        st.success("Search complete! Review your results below.")

st.write("### 3. Your Leads Database")
# The Interactive Spreadsheet
st.session_state.df = st.data_editor(
    st.session_state.df,
    num_rows="dynamic",
    use_container_width=True
)

# Download button
csv = st.session_state.df.to_csv(index=False).encode('utf-8')
st.download_button(
    label="Download Updated Spreadsheet as CSV",
    data=csv,
    file_name='b2b_leads_updated.csv',
    mime='text/csv',
)
