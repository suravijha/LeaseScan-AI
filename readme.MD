# 🛡️ LeaseScan AI: Legal Risk Auditor
An AI-powered tool that parses unstructured legal PDF data into structured risk metrics for tenants.

## 🚀 The Problem
Legal contracts are intentionally dense and difficult for students/tenants to read, often hiding predatory clauses.

## ✨ Features
- **PDF Extraction**: Uses PyMuPDF to process multi-page legal documents.
- **AI Risk Scoring**: Leverages Gemini 1.5 Pro to identify "Red Flags" using JSON-based prompt engineering.
- **Dashboard UI**: A clean, high-speed interface built with Streamlit.

## 🛠️ Tech Stack
- **Language**: Python
- **AI**: Google Gemini API
- **UI**: Streamlit
- **Parsing**: PyMuPDF

## ⚙️ Setup
1. Clone the repo: `git clone https://github.com/suravijha/lease-scan-ai`
2. Install requirements: `pip install -r requirements.txt`
3. Add your `API_KEY` to secrets.
4. Run: `streamlit run app.py`