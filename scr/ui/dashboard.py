import re
import streamlit as st

from src.database import db
from src.documents.processor import sha256_bytes
from src.rag.indexer import build
from src.rag.retriever import retrieve
from src.llm.generator import generate
from src.utils.config import DOC_DIR, MAX_UPLOAD_MB

def inject_css():
    st.markdown("""
    <style>
    .stApp {
      background:
        radial-gradient(circle at 10% 0%, rgba(124,58,237,.20), transparent 28%),
        radial-gradient(circle at 90% 10%, rgba(37,99,235,.16), transparent 28%),
        #060912;
    }
    [data-testid="stSidebar"] {
      background:#080c16 !important;
      border-right:1px solid rgba(255,255,255,.09);
    }
    .hero {
      padding:34px;
      border:1px solid rgba(255,255,255,.11);
      border-radius:28px;
      background:linear-gradient(135deg,rgba(124,58,237,.16),rgba(37,99,235,.08));
      box-shadow:0 25px 70px rgba(0,0,0,.28);
    }
    .hero h1 { font-size:2.7rem; margin:0; color:#c9c3f0; }
    .muted { color:#94a3b8 !important; }
    .metric {
      padding:18px;
      border:1px solid rgba(255,255,255,.09);
      border-radius:18px;
      background:rgba(15,23,42,.72);
    }
    .metric b { color:#c9c3f0; }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
      color:#c9c3f0 !important;
    }
    .stApp h3 { color:#c9c3f0; }
    .source {
      padding:12px 15px;
      margin:8px 0;
      border-left:3px solid #8b5cf6;
      background:rgba(124,58,237,.08);
      border-radius:10px;
    }
    </style>
    """, unsafe_allow_html=True)

def safe_filename(name):
    return re.sub(r"[^a-zA-Z0-9_.-]", "_", name)

def sidebar():
    with st.sidebar:
        st.markdown("## 🧠 NEXUS RAG")
        st.caption(
            f"Signed in as {st.session_state.display_name}"
        )
        st.caption(st.session_state.identifier)
        st.divider()

        st.markdown("### 📚 Knowledge Base")
        uploads = st.file_uploader(
            "Upload PDF files",
            type=["pdf"],
            accept_multiple_files=True
        )

        if uploads:
            changed = False
            for upload in uploads:
                if upload.size > MAX_UPLOAD_MB * 1024 * 1024:
                    st.error(
                        f"{upload.name} exceeds {MAX_UPLOAD_MB} MB."
                    )
                    continue

                target = DOC_DIR / safe_filename(upload.name)
                data = upload.getvalue()
                new_hash = sha256_bytes(data)

                old_hash = (
                    sha256_bytes(target.read_bytes())
                    if target.exists() else None
                )
                if new_hash != old_hash:
                    target.write_bytes(data)
                    changed = True

            if changed:
                with st.spinner("Indexing documents..."):
                    build(force=True)
                st.success("Knowledge base updated.")
                st.rerun()

        documents = list(DOC_DIR.glob("*.pdf"))
        st.metric("Documents", len(documents))

        if st.button("🧹 Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

        if st.button("🚪 Sign Out", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user_id = None
            st.rerun()

def render_dashboard():
    inject_css()
    sidebar()

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if not st.session_state.messages:
        for row in db.recent_chats(st.session_state.user_id):
            st.session_state.messages.append({
                "role": "user",
                "content": row["question"]
            })
            st.session_state.messages.append({
                "role": "assistant",
                "content": row["answer"],
                "sources": []
            })

    st.markdown("""
    <div class="hero">
      <h1>Ask your knowledge base anything.</h1>
      <p class="muted">
        Multi-document RAG with hybrid retrieval, neural reranking,
        grounded generation and source attribution.
      </p>
    </div>
    """, unsafe_allow_html=True)

    st.write("")

    a,b,c,d = st.columns(4)
    with a:
        st.markdown(
            "<div class='metric'><b>🤖 AI Engine</b><br>"
            "<span class='muted'>Grounded Generation</span></div>",
            unsafe_allow_html=True
        )
    with b:
        st.markdown(
            "<div class='metric'><b>🔎 Retrieval</b><br>"
            "<span class='muted'>Hybrid + Reranking</span></div>",
            unsafe_allow_html=True
        )
    with c:
        st.markdown(
            "<div class='metric'><b>📚 Evidence</b><br>"
            "<span class='muted'>File + Page Sources</span></div>",
            unsafe_allow_html=True
        )
    with d:
        st.markdown(
            "<div class='metric'><b>🔐 Security</b><br>"
            "<span class='muted'>Persistent Accounts</span></div>",
            unsafe_allow_html=True
        )

    st.markdown("### 💬 Knowledge Assistant")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant":
                sources = message.get("sources", [])
                if sources:
                    with st.expander("📚 Evidence & Sources"):
                        for s in sources:
                            score = s.get(
                                "rerank_score",
                                s.get("hybrid_score", 0)
                            )
                            st.markdown(
                                f"<div class='source'>"
                                f"<b>📄 {s['source']}</b> · Page {s['page']} "
                                f"· Relevance {float(score):.3f}"
                                f"</div>",
                                unsafe_allow_html=True
                            )
                            st.caption(s["text"][:1000])

    question = st.chat_input(
        "Ask a question about your documents..."
    )
    if not question:
        return

    st.session_state.messages.append({
        "role": "user", "content": question
    })
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("🔎 Retrieving evidence..."):
            results = retrieve(question)

        with st.spinner("🧠 Generating grounded answer..."):
            answer = generate(
                question,
                results,
                st.session_state.messages[:-1]
            )

        st.markdown(answer)

        if results:
            with st.expander("📚 Evidence & Sources"):
                for s in results:
                    score = s.get(
                        "rerank_score",
                        s.get("hybrid_score", 0)
                    )
                    st.markdown(
                        f"<div class='source'>"
                        f"<b>📄 {s['source']}</b> · Page {s['page']} "
                        f"· Relevance {float(score):.3f}"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                    st.caption(s["text"][:1000])

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "sources": results
    })

    db.save_chat(
        st.session_state.user_id,
        question,
        answer,
        results
    )