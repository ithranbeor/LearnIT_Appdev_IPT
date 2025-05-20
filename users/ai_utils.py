import torch
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

model = SentenceTransformer('all-MiniLM-L6-v2')

def get_semantic_matches(videos, query, threshold=0.6):
    if not query:
        return videos.none()

    query_embedding = model.encode(query)

    matched_ids = []
    for video in videos:
        if not video.embedding:
            continue
        video_embedding = np.frombuffer(video.embedding, dtype=np.float32)
        similarity = cosine_similarity([query_embedding], [video_embedding])[0][0]
        if similarity >= threshold:
            matched_ids.append(video.id)

    return videos.filter(id__in=matched_ids)
