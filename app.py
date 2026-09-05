import streamlit as st
import pandas as pd
import time
from duckduckgo_search import DDGS

st.set_page_config(layout="wide")
st.title("Free B2B Lead Generator")

# Initialize the spreadsheet in the app
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(
        columns=["Company", "Careers Page", "Contact Name", "LinkedIn Profile", "Email Guess", "Status", "My Notes"]
    )

def enrich_data(df):
    ddgs = DDGS()
    
    # Check each row in your spreadsheet
    for index, row in df.iterrows():
        company = row["Company"]
        
        # Skip empty rows
        if pd.isna(company) or company == "":
            continue
        # Skip rows that already have a careers page
        if not pd.isna(row["Careers Page"]) and row["Careers Page"] != "":
            continue
            
        st.toast(f"Agent searching for {company}...")
        
        # Search for Careers Page
        careers_query = f'"{company}" official site careers OR jobs'
        try:
            careers_results = ddgs.text(careers_query, max_results=1)
            if careers_results:
                df.at[index, "Careers Page"] = careers_results[0]['href']
        except:
            pass
            
        time.sleep(1.5) # Pause so we don't get blocked
        
        # Search for HR Personnel on LinkedIn
        linkedin_query = f'site:linkedin.com/in/ "{company}" "HR" OR "Talent Acquisition" OR "Recruiter"'
        try:
            li_results = ddgs.text(linkedin_query, max_results=1)
            if li_results:
                # Get the name from the search title
                raw_title = li_results[0]['title']
                name = raw_title.split('-')[0].strip()
                
                df.at[index, "Contact Name"] = name
                df.at[index, "LinkedIn Profile"] = li_results[0]['href']
                
                # Guess the email
                domain = str(df.at[index, "Careers Page"]).split('/')[2].replace('www.', '') if not pd.isna(df.at[index, "Careers Page"]) else "company.com"
                email_guess = f"{name.lower().replace(' ', '.')}@{domain}"
                df.at[index, "Email Guess"] = email_guess
        except:
            pass
            
        time.sleep(1.5)
        
    return df

# The Button to start the search
if st.button("Run AI Agent (Search Web)", type="primary"):
    with st.spinner("Scraping search results... this takes a few seconds per company."):
        st.session_state.df = enrich_data(st.session_state.df)
        st.success("Search complete!")

st.write("### Your Leads Database")
st.caption("Type company names into the empty 'Company' boxes below. Then click the button above to search.")

# The Interactive Spreadsheet
st.session_state.df = st.data_editor(
    st.session_state.df,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Status": st.column_config.SelectboxColumn(
            "Status",
            options=["To Contact", "Emailed", "Meeting Booked", "Not Interested"]
        )
    }
)

# Download button
csv = st.session_state.df.to_csv(index=False).encode('utf-8')
st.download_button(
    label="Download Spreadsheet as CSV",
    data=csv,
    file_name='b2b_leads.csv',
    mime='text/csv',
)
