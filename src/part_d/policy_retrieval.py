from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.config import POLICY_DIR


def chunk_policy(text: str, chunk_size: int = 40, overlap: int = 10):
    words = text.split()
    chunks = []
    if not words:
        return chunks
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(' '.join(words[start:end]))
        if end == len(words):
            break
        start += chunk_size - overlap
    return chunks


def load_policy_documents():
    docs = {}
    for path in sorted(POLICY_DIR.glob('*.txt')):
        text = path.read_text(encoding='utf-8')
        docs[path.name] = text
    return docs


def retrieve_policy(query: str, k: int = 3, chunk_size: int = 40, overlap: int = 10):
    docs = load_policy_documents()
    corpus = []
    meta = []
    for name, text in docs.items():
        for chunk in chunk_policy(text, chunk_size=chunk_size, overlap=overlap):
            corpus.append(chunk)
            meta.append(name)
    vectorizer = TfidfVectorizer(stop_words='english')
    X = vectorizer.fit_transform(corpus + [query])
    q = X[-1]
    sims = cosine_similarity(q, X[:-1])[0]
    ranked = sorted(enumerate(sims), key=lambda x: x[1], reverse=True)[:k]
    results = [{'doc': meta[i], 'text': corpus[i], 'score': float(score)} for i, score in ranked]
    return {'results': results}


def answer(question: str):
    matches = retrieve_policy(question, k=3)
    context = '\n\n'.join(f"[{r['doc']}]\n{r['text']}" for r in matches['results'])
    system_msg = {
        'role': 'system',
        'content': 'POLICY ASSISTANT: Answer only using the supplied context. If the answer is absent, say: I could not find that information in the policy documents.'
    }
    user_msg = {
        'role': 'user',
        'content': f"CONTEXT:\n{context}\n\nQUESTION:\n{question}"
    }
    import mock_llm
    response = mock_llm.chat([system_msg, user_msg])
    answer_text = response['content'] if isinstance(response['content'], str) else response['content'].get('content', '')
    return {'answer': answer_text, 'sources_used': [r['doc'] for r in matches['results']]}
