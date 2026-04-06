import json
import numpy as np
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")

with open("rag_knowledge.json", "r", encoding="utf-8") as f:
    knowledge = json.load(f)

texts = [item["text"] for item in knowledge]
embeddings = model.encode(texts)

def retrieve_relevant_context(query: str, top_k: int = 3):
    query_embedding = model.encode([query])[0]

    scores = np.dot(embeddings, query_embedding)

    top_indices = np.argsort(scores)[-top_k:]

    results = []
    for i in reversed(top_indices):
        item = knowledge[i]
        results.append({
            "text": item["text"],
            "label": item["label"],
            "risk": item["risk"],
            "score": float(scores[i])
        })

    return results