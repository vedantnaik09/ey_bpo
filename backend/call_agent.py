import os
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, ServiceContext, StorageContext, load_index_from_storage
from llama_index.llms.groq import Groq
import os
from dotenv import load_dotenv
load_dotenv() 
os.environ['OPENAI_API_KEY']=os.getenv('OPENAI_API_KEY')
from database import DatabaseManager
database=DatabaseManager()

# Define the function to create and persist the index
def create_and_persist_index(documents, persist_dir):
    # Initialize the Groq LLM
    llm = Groq(model="llama3-70b-8192", api_key=os.getenv("GROQ_API_KEY"))

    # Create a service context
    service_context = ServiceContext.from_defaults(llm=llm)

    # Create a vector store index from the documents
    index = VectorStoreIndex.from_documents(documents, service_context=service_context)

    # Persist the index to disk
    index.storage_context.persist(persist_dir=persist_dir)
    return index

# Define the function to load the existing index from disk
def load_existing_index(persist_dir):
    # Load the index from storage
    storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
    index = load_index_from_storage(storage_context)
    return index

# Define the function to query the index
def query_index(index, query):
    # Retrieve relevant documents based on the query
    query_engine=index.as_query_engine()
    response = query_engine.query(query)
    return response

# Main logic to load documents and create/load the index
def main(query):
    # Path to the directory containing documents
    persist_dir = './STORAGE'
    data_dir='./data'
    documents = SimpleDirectoryReader(input_files=['./data/knowledge_base.txt']).load_data()

    # Directory where the index will be persisted
    

    # Try to load the existing index if it exists
    try:
        index = load_existing_index(persist_dir)
        print("Loaded existing index.")
    except Exception as e:
        print(f"Error loading index: {e}. Creating a new index.")
        # Create and persist a new index if not found
        index = create_and_persist_index(documents, persist_dir)

    # Query the index with your custom query
    response = query_index(index, query)
    print("Query Response:", response)
    return response




def resolve(num,prblm_description):
  # Your function logic here
  str(num)
  solution=main(prblm_description)
  database.upload_solution(num,str(solution))
  # Execute the shell command
  os.system(f"lk dispatch create --new-room --agent-name outbound-caller --metadata {num}")

