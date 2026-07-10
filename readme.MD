# 🛡️ LeaseScan AI

An AI-powered legal document analyzer that performs **retrieval-augmented, multi-agent analysis** of lease agreements — surfacing high-risk clauses with evidence-backed explanations, letting you chat with the lease directly, and generating a downloadable audit report.

## Why this exists

A single "send the whole PDF to an LLM and print the JSON" script is easy to build but doesn't scale, doesn't explain itself, and can't answer follow-up questions. LeaseScan AI instead:

- **Retrieves** only the clauses relevant to a question or specialty (RAG), instead of stuffing the whole document into every prompt.
- **Delegates** analysis across five focused specialist agents rather than one do-everything prompt.
- **Cites its evidence** — every flag points to a page number and a verbatim quote, so nothing is a black box.
- **Answers follow-up questions** interactively, grounded in the actual document text.

## Architecture

```
PDF upload
   │
   ▼
Text extraction (PyMuPDF) ──► OCR fallback (Tesseract) for scanned pages
   │
   ▼
Page-aware chunking
   │
   ▼
Embeddings (sentence-transformers) ──► FAISS vector index
   │
   ▼
Multi-agent retrieval + analysis (Gemini 2.5 Flash)
   ├── Financial Agent
   ├── Privacy & Access Agent
   ├── Termination & Renewal Agent
   ├── Maintenance & Repairs Agent
   └── Legal & Liability Agent
   │
   ▼
Coordinator agent ──► overall score + summary
   │
   ├──► Plotly risk dashboard (radar + severity chart)
   ├──► RAG chat over the lease
   ├──► PDF audit report (ReportLab)
   └──► SQLite analysis history
```

## Tech stack

| Layer | Tool |
|---|---|
| UI | Streamlit |
| LLM | Google Gemini 2.5 Flash |
| PDF parsing | PyMuPDF |
| OCR | Tesseract (via pytesseract) |
| Embeddings | sentence-transformers (`all-MiniLM-L6-v2`) |
| Vector search | FAISS |
| Dashboard | Plotly |
| Report export | ReportLab |
| History | SQLite |

## Project structure

```
lease-scan-ai/
├── app.py                     # Streamlit UI
├── modules/
│   ├── pdf_processor.py       # text extraction + OCR fallback
│   ├── chunking.py            # page-aware chunking
│   ├── vectorstore.py         # embeddings + FAISS retrieval
│   ├── agents.py              # multi-agent analysis pipeline
│   ├── qa_chat.py             # RAG chat over the lease
│   ├── dashboard.py           # Plotly visualizations
│   ├── report_generator.py    # PDF report export
│   └── history.py             # SQLite analysis history
├── requirements.txt
├── packages.txt                # system deps for Streamlit Cloud (tesseract)
```

## Notes

- Analysis quality depends entirely on Gemini's reasoning — this is a decision-support tool, not legal advice.
- The vector index and chat history are rebuilt each session; only the summary metrics persist (in `lease_history.db`).
