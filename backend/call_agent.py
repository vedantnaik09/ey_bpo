import os
import faiss
import numpy as np
import pickle
import google.generativeai as genai
from groq import Groq
from dotenv import load_dotenv
from database import DatabaseManager

# Load environment variables
load_dotenv()
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
database = DatabaseManager()

def create_and_persist_index(data_path, persist_dir):
    # Load and process documents
    with open(data_path, 'r') as f:
        text = f.read()
    
    # Simple text splitting (modify as needed)
    chunks = [chunk for chunk in text.split('\n\n') if chunk.strip()]
    
    # Generate embeddings
    embeddings = []
    for chunk in chunks:
        response = genai.embed_content(
            model="models/embedding-001",
            content=chunk
        )
        embeddings.append(response['embedding'])
    
    # Convert to numpy array
    embeddings_np = np.array(embeddings).astype('float32')
    
    # Create FAISS index
    dimension = embeddings_np.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings_np)
    
    # Create storage directory if not exists
    os.makedirs(persist_dir, exist_ok=True)
    
    # Save index and metadata
    faiss.write_index(index, os.path.join(persist_dir, 'faiss.index'))
    with open(os.path.join(persist_dir, 'chunks.pkl'), 'wb') as f:
        pickle.dump(chunks, f)
    
    return index, chunks

def load_existing_index(persist_dir):
    index = faiss.read_index(os.path.join(persist_dir, 'faiss.index'))
    with open(os.path.join(persist_dir, 'chunks.pkl'), 'rb') as f:
        chunks = pickle.load(f)
    return index, chunks

def query_index(query, index, chunks, top_k=3):
    # Generate query embedding
    query_embedding = genai.embed_content(
        model="models/embedding-001",
        content=query
    )['embedding']
    
    # Convert to numpy array
    query_np = np.array([query_embedding]).astype('float32')
    
    # Search FAISS index
    distances, indices = index.search(query_np, top_k)
    
    # Get relevant context
    context = "\n".join([chunks[i] for i in indices[0]])
    
    # Query Groq LLM
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    response = client.chat.completions.create(
        messages=[{
            "role": "user",
            "content": f"Context:\n{context}\n\nQuestion: {query}\nAnswer:"
        }],
        model="llama3-70b-8192",
    )
    return response.choices[0].message.content

def resolve_db(query):
    persist_dir = './STORAGE'
    data_path = './data/knowledge_base.txt'
    
    try:
        index, chunks = load_existing_index(persist_dir)
        print("Loaded existing index.")
    except Exception as e:
        print(f"Index load failed: {e}. Creating new index.")
        index, chunks = create_and_persist_index(data_path, persist_dir)
    
    response = query_index(query, index, chunks)
    print("Query Response:", response)
    return response

def resolve(num, prblm_description):
    
    os.system(f'lk dispatch create --new-room --agent-name outbound-caller --metadata "{num}"')

# Example usage