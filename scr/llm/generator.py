import streamlit as st
from groq import Groq
from src.utils.config import GROQ_API_KEY, GROQ_MODEL

@st.cache_resource
def client():
    if not GROQ_API_KEY:
        return None
    return Groq(api_key=GROQ_API_KEY)

def generate(question, results, history):
    if not results:
        return (
            "I couldn't find sufficient evidence in the uploaded documents "
            "to answer this question."
        )

    api = client()
    if api is None:
        return "GROQ_API_KEY is not configured."

    context = "\n\n".join(
        f"""SOURCE {i}
File: {r['source']}
Page: {r['page']}
Evidence:
{r['text']}"""
        for i, r in enumerate(results, 1)
    )

    recent = "\n".join(
        f"{m['role']}: {m['content']}"
        for m in history[-6:]
    )

    prompt = f"""
You are NEXUS RAG, a strict document-grounded AI assistant.

Rules:
- Use only the supplied evidence for factual claims.
- Never invent information or citations.
- If evidence is insufficient, say so clearly.
- Answer in the user's language when possible.
- Be concise and professional.
- Mention source file/page when useful.

Conversation:
{recent}

Evidence:
{context}

Question:
{question}
"""

    try:
        response = api.chat.completions.create(
            model=GROQ_MODEL,
            temperature=0.1,
            max_tokens=1400,
            messages=[
                {"role": "system", "content": "You are a precise RAG assistant."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        return f"Generation error: {exc}"
