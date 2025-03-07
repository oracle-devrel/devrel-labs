import os
from typing import List, Optional
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import uuid

from pdf_processor import PDFProcessor
from store import VectorStore
from local_rag_agent import LocalRAGAgent
from rag_agent import RAGAgent

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Agentic RAG API",
    description="API for processing PDFs and answering queries using an agentic RAG system",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
pdf_processor = PDFProcessor()
vector_store = VectorStore()

# Initialize RAG agent - use OpenAI if API key is available, otherwise use local model. by default = local model
openai_api_key = os.getenv("OPENAI_API_KEY")
if openai_api_key:
    print("\nUsing OpenAI GPT-4 for RAG...")
    rag_agent = RAGAgent(vector_store=vector_store, openai_api_key=openai_api_key)
else:
    print("\nOpenAI API key not found. Using local Mistral model for RAG...")
    rag_agent = LocalRAGAgent(vector_store=vector_store)

class QueryRequest(BaseModel):
    query: str
    use_cot: bool = False

class QueryResponse(BaseModel):
    answer: str
    reasoning: Optional[str] = None
    context: List[dict]

@app.post("/upload/pdf")
async def upload_pdf(file: UploadFile = File(...)):
    """Upload and process a PDF file"""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    try:
        # Save the uploaded file temporarily
        temp_path = f"temp_{uuid.uuid4()}.pdf"
        with open(temp_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Process the PDF
        chunks, document_id = pdf_processor.process_pdf(temp_path)
        
        # Add chunks to vector store
        vector_store.add_pdf_chunks(chunks, document_id=document_id)
        
        # Clean up
        os.remove(temp_path)
        
        return {
            "message": "PDF processed successfully",
            "document_id": document_id,
            "chunks_processed": len(chunks)
        }
        
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """Process a query using the RAG agent"""
    try:
        # Reinitialize agent with CoT setting
        if openai_api_key:
            rag_agent = RAGAgent(vector_store=vector_store, openai_api_key=openai_api_key, use_cot=request.use_cot)
        else:
            rag_agent = LocalRAGAgent(vector_store=vector_store, use_cot=request.use_cot)
            
        response = rag_agent.process_query(request.query)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 