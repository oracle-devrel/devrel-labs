import os
from typing import List, Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import uuid
import time

from pdf_processor import PDFProcessor
from store import VectorStore
from local_rag_agent import LocalRAGAgent
from rag_agent import RAGAgent

# A2A Protocol imports
from a2a_models import A2ARequest, A2AResponse
from a2a_handler import A2AHandler
from agent_card import get_agent_card

# Event Logger import
try:
    from OraDBEventLogger import OraDBEventLogger
    event_logger = OraDBEventLogger()
    EVENT_LOGGING_ENABLED = True
    print("✅ Event logging enabled with Oracle DB")
except Exception as e:
    print(f"⚠️ Event logging disabled: {str(e)}")
    event_logger = None
    EVENT_LOGGING_ENABLED = False

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Agentic RAG API with A2A Protocol",
    description="API for processing PDFs and answering queries using an agentic RAG system with Agent2Agent (A2A) protocol support",
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

# Check for Ollama availability
try:
    import ollama
    ollama_available = True
    print("\nOllama is available. You can use Ollama models for RAG.")
except ImportError:
    ollama_available = False
    print("\nOllama not installed. You can install it with: pip install ollama")

# Initialize RAG agent - use OpenAI if API key is available, otherwise use local model or Ollama
openai_api_key = os.getenv("OPENAI_API_KEY")
if openai_api_key:
    print("\nUsing OpenAI GPT-4 for RAG...")
    rag_agent = RAGAgent(vector_store=vector_store, openai_api_key=openai_api_key)
else:
    # Try to use local Mistral model first
    try:
        print("\nTrying to use local Mistral model...")
        rag_agent = LocalRAGAgent(vector_store=vector_store)
        print("Successfully initialized local Mistral model.")
    except Exception as e:
        print(f"\nFailed to initialize local Mistral model: {str(e)}")
        
        # Fall back to Ollama if Mistral fails and Ollama is available
        if ollama_available:
            try:
                print("\nFalling back to Ollama with llama3 model...")
                rag_agent = LocalRAGAgent(vector_store=vector_store, model_name="ollama:llama3")
                print("Successfully initialized Ollama with llama3 model.")
            except Exception as e:
                print(f"\nFailed to initialize Ollama: {str(e)}")
                print("No available models. Please check your configuration.")
                raise e
        else:
            print("\nNo available models. Please check your configuration.")
            raise e

# Initialize A2A handler
print("\nInitializing A2A Protocol handler...")
a2a_handler = A2AHandler(rag_agent, vector_store, event_logger=event_logger if EVENT_LOGGING_ENABLED else None)
print("A2A Protocol handler initialized successfully.")

class QueryRequest(BaseModel):
    query: str
    use_cot: bool = False
    model: Optional[str] = None  # Allow specifying model in the request

class QueryResponse(BaseModel):
    answer: str
    reasoning: Optional[str] = None
    context: List[dict]

@app.post("/upload/pdf")
async def upload_pdf(file: UploadFile = File(...), request: Request = None):
    """Upload and process a PDF file"""
    start_time = time.time()
    
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    temp_path = None
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
        
        processing_time = (time.time() - start_time) * 1000  # Convert to ms
        
        # Log the event
        if EVENT_LOGGING_ENABLED:
            event_logger.log_document_event(
                document_type="pdf",
                document_id=document_id,
                source=file.filename,
                chunks_processed=len(chunks),
                processing_time_ms=processing_time,
                status="success"
            )
            
            event_logger.log_api_event(
                endpoint="/upload/pdf",
                method="POST",
                request_data={"filename": file.filename},
                response_data={"document_id": document_id, "chunks_processed": len(chunks)},
                status_code=200,
                duration_ms=processing_time
            )
        
        return {
            "message": "PDF processed successfully",
            "document_id": document_id,
            "chunks_processed": len(chunks)
        }
        
    except Exception as e:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        
        processing_time = (time.time() - start_time) * 1000
        
        # Log the error
        if EVENT_LOGGING_ENABLED:
            event_logger.log_document_event(
                document_type="pdf",
                document_id="error",
                source=file.filename if file else "unknown",
                chunks_processed=0,
                processing_time_ms=processing_time,
                status="error",
                error_message=str(e)
            )
        
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """Process a query using the RAG agent"""
    start_time = time.time()
    model_name = request.model if request.model else "default"
    
    try:
        # Determine which model to use
        if request.model:
            if request.model.startswith("ollama:") and ollama_available:
                # Use specified Ollama model
                rag_agent = LocalRAGAgent(vector_store=vector_store, model_name=request.model, use_cot=request.use_cot)
                model_type = "ollama"
            elif request.model == "openai" and openai_api_key:
                # Use OpenAI
                rag_agent = RAGAgent(vector_store=vector_store, openai_api_key=openai_api_key, use_cot=request.use_cot)
                model_type = "openai"
            else:
                # Use default local model
                rag_agent = LocalRAGAgent(vector_store=vector_store, use_cot=request.use_cot)
                model_type = "local"
        else:
            # Reinitialize agent with CoT setting using default model
            if openai_api_key:
                rag_agent = RAGAgent(vector_store=vector_store, openai_api_key=openai_api_key, use_cot=request.use_cot)
                model_type = "openai"
                model_name = "openai-gpt4"
            else:
                # Try local Mistral first
                try:
                    rag_agent = LocalRAGAgent(vector_store=vector_store, use_cot=request.use_cot)
                    model_type = "local"
                    model_name = "mistral-7b"
                except Exception as e:
                    print(f"Failed to initialize local Mistral model: {str(e)}")
                    # Fall back to Ollama if available
                    if ollama_available:
                        try:
                            rag_agent = LocalRAGAgent(vector_store=vector_store, model_name="ollama:llama3", use_cot=request.use_cot)
                            model_type = "ollama"
                            model_name = "llama3"
                        except Exception as e2:
                            raise Exception(f"Failed to initialize any model: {str(e2)}")
                    else:
                        raise e
            
        response = rag_agent.process_query(request.query)
        
        processing_time = (time.time() - start_time) * 1000  # Convert to ms
        
        # Log the event
        if EVENT_LOGGING_ENABLED:
            # Extract context info
            context_count = len(response.get("context", [])) if isinstance(response, dict) else 0
            answer = response.get("answer", "") if isinstance(response, dict) else str(response)
            
            event_logger.log_model_event(
                model_name=model_name,
                model_type=model_type,
                user_prompt=request.query,
                response=answer[:1000],  # Truncate to 1000 chars
                collection_used="default",
                use_cot=request.use_cot,
                duration_ms=processing_time,
                context_chunks=context_count
            )
            
            event_logger.log_api_event(
                endpoint="/query",
                method="POST",
                request_data={"query": request.query, "use_cot": request.use_cot, "model": model_name},
                response_data={"answer_length": len(answer), "context_chunks": context_count},
                status_code=200,
                duration_ms=processing_time
            )
        
        return response
    except Exception as e:
        processing_time = (time.time() - start_time) * 1000
        
        # Log the error
        if EVENT_LOGGING_ENABLED:
            event_logger.log_api_event(
                endpoint="/query",
                method="POST",
                request_data={"query": request.query, "use_cot": request.use_cot, "model": model_name},
                response_data={"error": str(e)},
                status_code=500,
                duration_ms=processing_time
            )
        
        raise HTTPException(status_code=500, detail=str(e))

# A2A Protocol endpoints
@app.post("/a2a", response_model=A2AResponse)
async def a2a_endpoint(request: A2ARequest):
    """A2A Protocol endpoint for agent-to-agent communication"""
    start_time = time.time()
    
    try:
        response = await a2a_handler.handle_request(request)
        
        processing_time = (time.time() - start_time) * 1000
        
        # Log A2A API event
        if EVENT_LOGGING_ENABLED:
            event_logger.log_api_event(
                endpoint="/a2a",
                method="POST",
                request_data={"method": request.method, "params": request.params},
                response_data={"result": str(response.result)[:500] if hasattr(response, 'result') else ""},
                status_code=200,
                duration_ms=processing_time
            )
        
        return response
    except Exception as e:
        processing_time = (time.time() - start_time) * 1000
        
        if EVENT_LOGGING_ENABLED:
            event_logger.log_api_event(
                endpoint="/a2a",
                method="POST",
                request_data={"method": request.method, "params": request.params},
                response_data={"error": str(e)},
                status_code=500,
                duration_ms=processing_time
            )
        raise

@app.get("/agent_card")
async def get_agent_card_endpoint():
    """Get the agent card for this agent"""
    return get_agent_card()

@app.get("/a2a/health")
async def a2a_health_check():
    """A2A health check endpoint"""
    return await a2a_handler.handle_request(A2ARequest(
        method="health.check",
        params={}
    ))

# Event logging endpoints
@app.get("/events/statistics")
async def get_event_statistics():
    """Get event logging statistics"""
    if not EVENT_LOGGING_ENABLED:
        raise HTTPException(status_code=503, detail="Event logging is not enabled")
    
    try:
        stats = event_logger.get_statistics()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/events/{event_type}")
async def get_events(event_type: str, limit: int = 100):
    """Get events by type (all, a2a, api, model, document, query)"""
    if not EVENT_LOGGING_ENABLED:
        raise HTTPException(status_code=503, detail="Event logging is not enabled")
    
    valid_types = ["all", "a2a", "api", "model", "document", "query"]
    if event_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid event type. Must be one of: {', '.join(valid_types)}")
    
    try:
        events = event_logger.get_events(event_type=event_type, limit=limit)
        
        # Convert datetime objects to strings for JSON serialization
        for event in events:
            if 'TIMESTAMP' in event and event['TIMESTAMP']:
                event['TIMESTAMP'] = str(event['TIMESTAMP'])
        
        return {
            "event_type": event_type,
            "count": len(events),
            "events": events
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/events/count/{event_type}")
async def get_event_count(event_type: str):
    """Get count of events by type"""
    if not EVENT_LOGGING_ENABLED:
        raise HTTPException(status_code=503, detail="Event logging is not enabled")
    
    valid_types = ["all", "a2a", "api", "model", "document", "query"]
    if event_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid event type. Must be one of: {', '.join(valid_types)}")
    
    try:
        count = event_logger.get_event_count(event_type=event_type)
        return {
            "event_type": event_type,
            "count": count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 