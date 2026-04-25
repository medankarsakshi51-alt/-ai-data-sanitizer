import streamlit as st
import pandas as pd
import requests
import re

# --- CORE CLEANING LOGIC (The Global Auto-Pilot) ---
def auto_clean_logic(df):
    # 1. Housekeeping: Remove duplicates and completely empty rows
    df = df.drop_duplicates().dropna(how='all')
    
    # Clean headers (lowercase, no spaces)
    df.columns = [str(c).lower().replace(' ', '_').strip() for c in df.columns]

    for col in df.columns:
        # --- A. NUMERIC HANDLING (Task: Fill NaN with 0) ---
        if pd.api.types.is_numeric_dtype(df[col]):
            df[col] = df[col].fillna(0)
            continue

        # --- B. DATE & TIME HANDLING (Task: Specific dd/mm/yyyy and hh:mm AM/PM) ---
        # Convert column to string first to avoid errors during date detection
        temp_col = pd.to_datetime(df[col], errors='coerce')
        
        if temp_col.notnull().sum() > (len(df) * 0.5): # If >50% of col looks like a date
            # Check if it contains time info
            if temp_col.dt.hour.any() or temp_col.dt.minute.any():
                df[col] = temp_col.dt.strftime('%I:%M %p') # 02:30 PM
            else:
                df[col] = temp_col.dt.strftime('%d/%m/%Y') # 15/04/2024
            continue

        # --- C. TEXT HANDLING (Task: Trim, Single Case, Currency) ---
        if df[col].dtype == 'object':
            # Convert to string and Trim spaces
            df[col] = df[col].astype(str).str.strip().str.replace(r'\s+', ' ', regex=True)

            # Check for Currency (Task: Standardize to $)
            if df[col].str.contains(r'[\$\£\€]|USD|EUR|INR', na=False).any():
                # Extract numbers and decimals only, then add $
                df[col] = df[col].str.replace(r'[^\d.]', '', regex=True)
                df[col] = '$' + df[col]
            else:
                # Default Text Rule: First letter Capital, rest small
                # .str.capitalize() does exactly this
                df[col] = df[col].str.capitalize()
    
    return df

# --- AI LOGIC ---
def ai_custom_clean(text, instruction, api_key):
    url = "https://huggingface.co"
    headers = {"Authorization": f"Bearer {api_key}"}
    prompt = f"[INST] Task: {instruction}\nInput: {text} [/INST] Answer:"
    try:
        r = requests.post(url, headers=headers, json={"inputs": prompt, "parameters": {"max_new_tokens": 50, "return_full_text": False}}, timeout=15)
        return r.json()[0]['generated_text'].replace("Answer:", "").strip() if r.status_code == 200 else text
    except:
        return text

# --- STREAMLIT UI ---
st.set_page_config(page_title="AI Data Sanitizer Pro", layout="wide")
st.title("🪄 Professional Data Sanitizer")

# Sidebar
st.sidebar.header("Configuration")
api_key = st.sidebar.text_input("Hugging Face API Key", type="password")

uploaded_file = st.file_uploader("Upload Messy Excel File", type="xlsx")

if uploaded_file:
    # Initialize Session State
    if "df" not in st.session_state:
        st.session_state.df = pd.read_excel(uploaded_file)

    tab1, tab2 = st.tabs(["🚀 Global Auto-Clean", "🛠️ Manual Tuning"])

    with tab1:
        st.subheader("One-Click Universal Fix")
        st.markdown("""
        **This will automatically:**
        - Trim extra spaces and fix casing (First letter capital).
        - Fill empty numbers with **0**.
        - Standardize Dates to **DD/MM/YYYY**.
        - Standardize Time to **HH:MM AM/PM**.
        - Detect and standardize **Currency**.
        """)
        
        if st.button("🪄 Run Global Clean"):
            with st.spinner("Processing entire dataset..."):
                try:
                    st.session_state.df = auto_clean_logic(st.session_state.df)
                    st.success("Global cleaning applied!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error during cleaning: {e}")

    with tab2:
        st.subheader("Targeted Column Fixes")
        col_to_fix = st.selectbox("Select Column", st.session_state.df.columns)
        
        choice = st.radio("Fix Method:", ["Standard Pandas Rules", "Custom AI Command"])

        if choice == "Standard Pandas Rules":
            rule = st.selectbox("Action:", ["UPPERCASE", "lowercase", "Proper Case", "Remove Symbols", "Remove Underscores"])
            if st.button("Apply Action"):
                if rule == "UPPERCASE": st.session_state.df[col_to_fix] = st.session_state.df[col_to_fix].astype(str).str.upper()
                elif rule == "lowercase": st.session_state.df[col_to_fix] = st.session_state.df[col_to_fix].astype(str).str.lower()
                elif rule == "Proper Case": st.session_state.df[col_to_fix] = st.session_state.df[col_to_fix].astype(str).str.title()
                elif rule == "Remove Symbols": st.session_state.df[col_to_fix] = st.session_state.df[col_to_fix].astype(str).str.replace(r'[^\w\s]', '', regex=True)
                elif rule == "Remove Underscores": st.session_state.df[col_to_fix] = st.session_state.df[col_to_fix].astype(str).str.replace('_', ' ')
                st.success(f"Applied {rule} to {col_to_fix}!")
                st.rerun()
        
        else:
            user_cmd = st.text_input("Ask the AI to do something specific:", placeholder="e.g. Translate to German, Extract Zip Code")
            if st.button("Run AI Command"):
                if api_key:
                    with st.spinner("AI is thinking..."):
                        st.session_state.df[col_to_fix] = st.session_state.df[col_to_fix].apply(lambda x: ai_custom_clean(x, user_cmd, api_key))
                        st.rerun()
                else:
                    st.warning("Please enter your API Key in the sidebar.")

    # --- PREVIEW & DOWNLOAD ---
    st.divider()
    st.write("### Data Preview (Latest Version)")
    st.dataframe(st.session_state.df.head(10)) # Use st.dataframe for better scrolling
    
    csv = st.session_state.df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Cleaned CSV", csv, "final_cleaned_data.csv", "text/csv")

    if st.sidebar.button("🔄 Reset to Original File"):
        del st.session_state.df
        st.rerun()
