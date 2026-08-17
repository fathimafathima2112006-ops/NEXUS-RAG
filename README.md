# NEXUS RAG — AI Knowledge Intelligence Platform

Final-year project architecture for a production-style multi-document RAG application.

## Core features

- Permanent account using email or international phone
- PBKDF2 password hashing
- Forgot-password OTP flow
- SMTP email OTP
- Optional Twilio SMS OTP
- Persistent SQLite accounts and chat history
- Multi-PDF knowledge base
- Smart paragraph-aware chunking
- Sentence Transformer embeddings
- FAISS vector search
- Hybrid semantic + keyword retrieval
- CrossEncoder reranking
- Groq grounded generation
- Source file/page attribution
- Premium Streamlit UI
- Automated tests

## Setup

### 1. Create virtual environment

```bash
python -m venv .venv
```

Windows:
```bash
.venv\Scripts\activate
```

Linux/macOS:
```bash
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

Copy `.env.example` to `.env`.

At minimum, for Groq:

```text
GROQ_API_KEY=your_key
```

For email OTP, configure SMTP. With Gmail, use a Google App Password rather than your normal account password.

For SMS OTP, configure Twilio.

### 4. Run

```bash
streamlit run app.py
```

### 5. Test

```bash
pytest
```

## Free/local LLM option

If you want to avoid a cloud LLM during development, run a local model through Ollama and replace `src/llm/generator.py` with an Ollama client. The rest of the RAG pipeline remains the same.

## Production upgrade

For public deployment, replace SQLite with PostgreSQL/Supabase, store PDFs in object storage, add rate limiting/CAPTCHA to OTP flows, use HTTPS, and never commit `.env`.
