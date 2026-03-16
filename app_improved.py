import streamlit as st

# Session state for maintaining user inputs
if 'data' not in st.session_state:
    st.session_state.data = None

if 'error' not in st.session_state:
    st.session_state.error = None

# Function to process financial data
def process_data(input_data):
    try:
        # Simulate processing input data for analysis
        if not input_data:
            raise ValueError("Input data is empty")
        
        # Example RAG implementation based on input value
        value = float(input_data)
        if value < 0: 
            return "Red: Poor performance", "Red"
        elif 0 <= value < 10:
            return "Amber: Average performance", "Amber"
        else:
            return "Green: Good performance", "Green"

    except Exception as e:
        st.session_state.error = str(e)
        return None, "Red"

# File cleanup function
def clean_files():
    import os
    files_to_remove = ['temp_data.json']  # List any temp files here
    for f in files_to_remove:
        if os.path.exists(f):
            os.remove(f)

st.title("Finance PPT AI Analyst")

# User input
data_input = st.text_input("Enter your data for analysis:")
if st.button("Analyze"):
    result, color = process_data(data_input)
    clean_files()
    
    if st.session_state.error:
        st.error(st.session_state.error)
    else:
        st.success(result)
        st.markdown(f"<h1 style='color: {color};'>{result}</h1>", unsafe_allow_html=True)
