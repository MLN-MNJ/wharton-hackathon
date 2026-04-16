import os
import csv
import json
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

API_KEY = "AIzaSyDTW_RByDEBimPeTYkmH03rzPZX6MD0yII"
os.environ["GOOGLE_API_KEY"] = API_KEY
os.environ["TOKENIZERS_PARALLELISM"] = "false"

def main():
    print("Loading datasets...")
    bounties = []
    if os.path.exists("bounties_db.json"):
        with open("bounties_db.json", 'r', encoding='utf-8') as f:
            bounties = json.load(f)
            
    valid_pids = {b['eg_property_id'] for b in bounties}
    
    docs = []
    print("Reading and filtering reviews...")
    with open("Reviews_PROC.csv", "r", encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = row.get("eg_property_id")
            text = row.get("review_text", "")
            if pid in valid_pids and text.strip():
                # We store pid explicitly so retriever can filter!
                metadata = {"eg_property_id": pid}
                docs.append(Document(page_content=text, metadata=metadata))

    print(f"Loaded {len(docs)} total reviews for our 13 properties.")
    
    print("Chunking documents...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    chunks = text_splitter.split_documents(docs)
    print(f"Total chunks created: {len(chunks)}")
    
    print("Embedding chunks and building FAISS vector store (May take 30-60 secs)...")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    vectorstore = FAISS.from_documents(chunks, embeddings)
    
    print("Saving FAISS index locally...")
    vectorstore.save_local("faiss_index")
    print("Ingestion complete. Vector store ready!")

if __name__ == "__main__":
    main()
