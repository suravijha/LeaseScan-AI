import streamlit as st
import fitz 
import google.generativeai as genai
import json

api_key = st.secrets["GEMINI_KEY"]
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.5-flash')

st.set_page_config(page_title="LeaseScan AI", layout="wide")

# Custom CSS for a cleaner look
st.markdown("""
    <style>
    .reportview-container { background: #f0f2f6; }
    .stMetric { background-color: #000; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ LeaseScan AI")
st.caption("Automated Legal Risk Assessment")

uploaded_file = st.file_uploader("Drop your lease PDF here", type="pdf")

if uploaded_file:
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    text = "".join([page.get_text() for page in doc])

    if st.button("Run Audit"):
        # The Secret Sauce: Prompting for JSON
        prompt = f"""
                    You are an expert Tenant Advocate. Analyze the lease text provided.
                        
                    CRITICAL INSTRUCTIONS:
                    1. Be realistic. Standard clauses (like requiring a security deposit or 30-day notice) are NOT red flags.
                    2. Only flag items that are actually predatory, illegal, or highly unusual.
                    3. If the lease is a standard government-approved template, the score should be ABOVE 80.

                    Return ONLY a JSON object:
                    {{
                    "score": (0-100 rating. 100 = Very Tenant Friendly, 0 = Predatory),
                    "summary": "1 sentence overview of the lease",
                    "flags": [
                        {{"issue": "short name", "risk": "1 sentence explanation", "level": "HIGH/MED/LOW"}}
                    ]
                    }}
                    Text: {text[:10000]}
                """
        
        with st.spinner("Analyzing..."):
            raw_response = model.generate_content(prompt).text
            # Clean response if AI adds markdown backticks
            clean_json = raw_response.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_json)

        # UI Layout: Summary Cards
        col1, col2, col3 = st.columns(3)
        col1.metric("Safety Score", f"{data['score']}/100")
        col2.metric("Red Flags Found", len(data['flags']))
        col3.metric("Status", "Review Required" if data['score'] < 70 else "Safe")

        st.divider()

        # UI Layout: High-Impact List
        for item in data['flags']:
            color = "🔴" if item['level'] == "HIGH" else "🟡"
            with st.expander(f"{color} {item['issue'].upper()} ({item['level']})"):
                st.write(item['risk'])