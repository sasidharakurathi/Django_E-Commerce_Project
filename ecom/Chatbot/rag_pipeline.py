import os
import json
import time
import google.generativeai as genai
from langchain.schema import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from dotenv import load_dotenv
from django.conf import settings

# --- Configuration ---
# Load environment variables from a .env file
load_dotenv()


KNOWLEDGE_BASE_PATH = "ecom/Chatbot/knowledge_base.jsonl"
# KNOWLEDGE_BASE_PATH = "./knowledge_base.jsonl"
VECTOR_STORE_PATH = "ecom/Chatbot/chroma_db_jsonl"
# VECTOR_STORE_PATH = "./chroma_db_jsonl"
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
GEMINI_MODEL = "gemini-2.5-flash"
RESULTS_FILE_PATH = "./results.json"

# --- Global Variables ---
retriever = None
_rag_initialized = False

# --- Loader for JSONL Knowledge Base ---
def load_structured_knowledge_base(file_path: str) -> list[Document]:
    """
    Loads documents and metadata from a .jsonl file.
    Each line is a JSON object with 'content' and 'metadata'.
    """
    docs = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            # Creating a LangChain Document with content and metadata
            doc = Document(
                page_content=data['content'],
                metadata=data.get('metadata', {})
            )
            docs.append(doc)
    return docs

def initialize_rag_pipeline():
    """
    Initializes the RAG pipeline using the structured JSONL loader,
    HuggingFace embeddings, and a Chroma vector store.
    """
    global retriever, _rag_initialized

    if _rag_initialized and retriever is not None:
        return

    try:
        print("🚀 Initializing RAG pipeline with structured JSONL data...")

        # 1. Load Documents using the NEW custom loader
        documents = load_structured_knowledge_base(KNOWLEDGE_BASE_PATH)
        print(f"✅ Loaded {len(documents)} structured documents from JSONL.")

        # 2. Initialize Embeddings Model
        try:
            print("🔄 Loading sentence transformer model...")
            embeddings = HuggingFaceEmbeddings(
                model_name=EMBEDDING_MODEL_NAME,
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )
            print("✅ Sentence transformer model loaded successfully!")
        except Exception as e:
            # TF-IDF fallback (incase of embeddings failed)
            print(f"⚠️ Failed to load sentence transformer: {e}. Falling back to TF-IDF.")
            from sklearn.feature_extraction.text import TfidfVectorizer
            from langchain.embeddings.base import Embeddings

            class TFIDFEmbeddings(Embeddings):
                def __init__(self):
                    self.vectorizer = TfidfVectorizer(max_features=384, stop_words='english')
                    self.fitted = False
                def embed_documents(self, texts):
                    if not self.fitted:
                        self.vectorizer.fit(texts)
                        self.fitted = True
                    return self.vectorizer.transform(texts).toarray().tolist()
                def embed_query(self, text):
                    if not self.fitted: return [0.0] * 384
                    return self.vectorizer.transform([text]).toarray()[0].tolist()
            
            embeddings = TFIDFEmbeddings()
            all_texts = [doc.page_content for doc in documents]
            embeddings.embed_documents(all_texts)
            print("✅ TF-IDF embeddings initialized and fitted successfully!")

        # 3. Create and Persist the Vector Store
        print("🔧 Creating new vector store...")
        vector_store = Chroma.from_documents(
            documents=documents, # Use the perfectly chunked documents
            embedding=embeddings,
            persist_directory=VECTOR_STORE_PATH
        )

        # 4. Create a Retriever
        retriever = vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 5}
        )
        _rag_initialized = True
        print("✅ RAG pipeline initialized successfully!")

    except Exception as e:
        print(f"❌ Critical Error during RAG pipeline initialization: {e}")

def get_chatbot_response(query: str) -> str:
    """
    Gets a response from the RAG pipeline using Gemini for generation.
    """
    global retriever
    if not _rag_initialized or retriever is None:
        return "Error: Chatbot is not initialized. Please run the initialization first."

    # 1. Retrieve Context
    retrieved_docs = retriever.get_relevant_documents(query)
    context_text = "\n\n".join([doc.page_content for doc in retrieved_docs])

    # 2. Configure the Gemini API
    # api_key = GEMINI_API_KEY
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        return "Error: GEMINI_API_KEY not found. Please set it in your .env file."
    try:
        genai.configure(api_key=api_key)
    except Exception as e:
        return f"Error configuring Gemini API: {e}"

    # 3. Define the Strict Prompt Template
    template = """You are an e-commerce assistant for a store named 'Sample E-Store'.
    Answer the user's question using ONLY the information provided in the context below.
    If any context is not provided try to search the query in internet and answer to it.

    STRICT RULES:
    - Answer ONLY from the context. If the information is not there, say "I don't have information about that."
    - All prices MUST be in Indian Rupees (₹), like this: ₹5,000 or ₹65,250.
    - Be direct and factual. Do not add any extra information, promotions, or apologies.

    Context:
    ---
    {context}
    ---

    Question: {question}

    Response:"""
    
    # 4. Generate Content with Gemini
    try:
        model = genai.GenerativeModel(GEMINI_MODEL)
        prompt = template.format(context=context_text, question=query)
        response = model.generate_content(prompt)
        
        # 5. Clean and return the response
        cleaned_response = response.text.strip()
        return cleaned_response
        
    except Exception as e:
        print(f"❌ Error during Gemini content generation: {e}")
        return "I'm sorry, I'm having trouble connecting to my brain right now. Please try again in a moment."


def run_test_suite():
    """
    Runs a predefined set of questions against the chatbot and saves the
    results to a JSON file to evaluate performance.
    """
    test_questions = [
        'What is the price of the "Macbook First Edition"?',
        'Tell me about the "Saucony Men\'s Kinvara 13 Running Shoe".',
        'What is the "Trucker Bluetooth Headset" known for?',
        'How much does the "Asus Laptop" cost?',
        'Is the "Bio-Oil Skincare Body Oil" suitable for all skin types?',
        'How many days do I have to return an item?',
        'What is the warranty period for electronics?',
        'How can I get free shipping?',
        'What are your customer support hours?',
        'Can I pay using Cash on Delivery?',
        'How do I track my order?',
        'What should I do if I receive a damaged product?',
        'How can I cancel my order?',
        'Do you ship products internationally?',
        'Do you sell the iPhone 15?',
        'What is the discount on the Macbook?',
        'Can you tell me about your gift wrapping services?',
        'What is the weather like today?',
        'Tell me about your laptops.',
        'Which running shoes do you have?',
        'What\'s cheaper, the Macbook or the Asus Laptop?',
        'What products do you have for home and kitchen?',
    ]
    
    results = []
    print("\n--- 🧪 Starting Test Suite ---")
    
    for i, question in enumerate(test_questions):
        print(f"\n({i+1}/{len(test_questions)}) Testing Question: '{question}'")
        start_time = time.time()
        answer = get_chatbot_response(question)
        end_time = time.time()
        
        print(f"  -> Answer: {answer}")
        print(f"  -> Time Taken: {end_time - start_time:.2f}s")
        
        results.append({"question": question, "answer": answer})
        
    with open(RESULTS_FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
        
    print(f"\n--- ✅ Test Suite Finished ---")
    print(f"Results saved to '{RESULTS_FILE_PATH}'")


if __name__ == "__main__":
    # Initialize the RAG pipeline on startup
    initialize_rag_pipeline()
    
    #test queries
    run_test_suite()

    # Optional: uncomment the block below for interactive chat
    # print("\nChatbot is ready! Type 'exit' to quit.")
    # while True:
    #     user_query = input("You: ")
    #     if user_query.lower() == 'exit':
    #         break
    #     bot_response = get_chatbot_response(user_query)
    #     print(f"Bot: {bot_response}")