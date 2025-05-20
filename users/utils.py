from sentence_transformers import SentenceTransformer
import numpy as np
import pickle

model = SentenceTransformer('all-MiniLM-L6-v2')

def embed_text(text):
    embedding = model.encode([text])[0]
    return pickle.dumps(embedding) 

def load_embedding(binary):
    return pickle.loads(binary)
