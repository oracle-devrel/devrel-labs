import gradio as gr
import os
from typing import List, Dict, Any
from pathlib import Path
import tempfile
from dotenv import load_dotenv
import yaml
import torch
import time
import requests
import json
import asyncio
import threading
from datetime import datetime

from pdf_processor import PDFProcessor
from web_processor import WebProcessor
from repo_processor import RepoProcessor
from store import VectorStore

# Try to import OraDBVectorStore
try:
    from OraDBVectorStore import OraDBVectorStore
    ORACLE_DB_AVAILABLE = True
except ImportError:
    ORACLE_DB_AVAILABLE = False

from local_rag_agent import LocalRAGAgent
from rag_agent import RAGAgent

# Load environment variables and config
load_dotenv()

def load_config():
    """Load configuration from config.yaml"""
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        return config.get('HUGGING_FACE_HUB_TOKEN')
    except Exception as e:
        print(f"Error loading config: {str(e)}")
        return None

# Initialize components
pdf_processor = PDFProcessor()
web_processor = WebProcessor()
repo_processor = RepoProcessor()

# Initialize vector store (prefer Oracle DB if available)
if ORACLE_DB_AVAILABLE:
    try:
        vector_store = OraDBVectorStore()
        print("Using Oracle AI Database 26ai for vector storage")
    except Exception as e:
        print(f"Error initializing Oracle DB: {str(e)}")
        print("Falling back to ChromaDB")
        vector_store = VectorStore()
else:
    vector_store = VectorStore()
    print("Using ChromaDB for vector storage (Oracle DB not available)")

# Initialize agents
hf_token = load_config()
openai_key = os.getenv("OPENAI_API_KEY")

# Initialize agents with use_cot=True to ensure CoT is available
# Default to Ollama qwen2, fall back to Mistral if available
try:
    local_agent = LocalRAGAgent(vector_store, model_name="ollama:qwen2", use_cot=True)
    print("Using Ollama qwen2 as default model")
except Exception as e:
    print(f"Could not initialize Ollama qwen2: {str(e)}")
    local_agent = LocalRAGAgent(vector_store, use_cot=True) if hf_token else None
    print("Falling back to Local Mistral model" if hf_token else "No local model available")
    
openai_agent = RAGAgent(vector_store, openai_api_key=openai_key, use_cot=True) if openai_key else None

# A2A Client for testing
class A2AClient:
    """A2A client for testing A2A protocol functionality"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.timeout = 30
    
    def make_request(self, method: str, params: Dict[str, Any], request_id: str = "1") -> Dict[str, Any]:
        """Make an A2A request"""
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": request_id
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/a2a",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": f"Request failed: {str(e)}"
                },
                "id": request_id
            }
    
    def get_agent_card(self) -> Dict[str, Any]:
        """Get the agent card"""
        try:
            response = self.session.get(f"{self.base_url}/agent_card")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"Failed to get agent card: {str(e)}"}
    
    def health_check(self) -> Dict[str, Any]:
        """Check system health"""
        try:
            response = self.session.get(f"{self.base_url}/a2a/health")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"Health check failed: {str(e)}"}

# Initialize A2A client
a2a_client = A2AClient()

# Global task tracking for A2A testing
a2a_tasks = {}
a2a_task_counter = 0

def process_pdf(file: tempfile._TemporaryFileWrapper) -> str:
    """Process uploaded PDF file"""
    try:
        chunks, document_id = pdf_processor.process_pdf(file.name)
        vector_store.add_pdf_chunks(chunks, document_id=document_id)
        return f"✓ Successfully processed PDF and added {len(chunks)} chunks to knowledge base (ID: {document_id})"
    except Exception as e:
        return f"✗ Error processing PDF: {str(e)}"

def process_url(url: str) -> str:
    """Process web content from URL"""
    try:
        # Process URL and get chunks
        chunks = web_processor.process_url(url)
        if not chunks:
            return "✗ No content extracted from URL"
            
        # Add chunks to vector store with URL as source ID
        vector_store.add_web_chunks(chunks, source_id=url)
        return f"✓ Successfully processed URL and added {len(chunks)} chunks to knowledge base"
    except Exception as e:
        return f"✗ Error processing URL: {str(e)}"

def process_repo(repo_path: str) -> str:
    """Process repository content"""
    try:
        # Process repository and get chunks
        chunks, document_id = repo_processor.process_repo(repo_path)
        if not chunks:
            return "✗ No content extracted from repository"
            
        # Add chunks to vector store
        vector_store.add_repo_chunks(chunks, document_id=document_id)
        return f"✓ Successfully processed repository and added {len(chunks)} chunks to knowledge base (ID: {document_id})"
    except Exception as e:
        return f"✗ Error processing repository: {str(e)}"

def chat(message: str, history: List[List[str]], agent_type: str, use_cot: bool, collection: str) -> List[List[str]]:
    """Process chat message using selected agent and collection"""
    try:
        print("\n" + "="*50)
        print(f"New message received: {message}")
        print(f"Agent: {agent_type}, CoT: {use_cot}, Collection: {collection}")
        print("="*50 + "\n")
        
        # Determine if we should skip analysis based on collection and interface type
        # Skip analysis for General Knowledge or when using standard chat interface (not CoT)
        skip_analysis = collection == "General Knowledge" or not use_cot
        
        # Map collection names to actual collection names in vector store
        collection_mapping = {
            "PDF Collection": "pdf_documents",
            "Repository Collection": "repository_documents",
            "Web Knowledge Base": "web_documents",
            "General Knowledge": "general_knowledge"
        }
        
        # Get the actual collection name
        actual_collection = collection_mapping.get(collection, "pdf_documents")
        
        # Parse agent type to determine model and quantization
        quantization = None
        model_name = None
        
        if "4-bit" in agent_type:
            quantization = "4bit"
            model_type = "Local (Mistral)"
        elif "8-bit" in agent_type:
            quantization = "8bit"
            model_type = "Local (Mistral)"
        elif agent_type == "openai":
            model_type = "OpenAI"
        else:
            # All other models are treated as Ollama models
            model_type = "Ollama"
            model_name = agent_type
        
        # Select appropriate agent and reinitialize with correct settings
        if model_type == "OpenAI":
            if not openai_key:
                response_text = "OpenAI key not found. Please check your config."
                print(f"Error: {response_text}")
                return history + [[message, response_text]]
            agent = RAGAgent(vector_store, openai_api_key=openai_key, use_cot=use_cot, 
                            collection=collection, skip_analysis=skip_analysis)
        elif model_type == "Local (Mistral)":
            # For HF models, we need the token
            if not hf_token:
                response_text = "Local agent not available. Please check your HuggingFace token configuration."
                print(f"Error: {response_text}")
                return history + [[message, response_text]]
            agent = LocalRAGAgent(vector_store, use_cot=use_cot, collection=collection, 
                                 skip_analysis=skip_analysis, quantization=quantization)
        else:  # Ollama models
            try:
                agent = LocalRAGAgent(vector_store, model_name=model_name, use_cot=use_cot, 
                                     collection=collection, skip_analysis=skip_analysis)
            except Exception as e:
                response_text = f"Error initializing Ollama model: {str(e)}"
                print(f"Error: {response_text}")
                return history + [[message, response_text]]
        
        # Process query and get response
        print("Processing query...")
        response = agent.process_query(message)
        print("Query processed successfully")
        
        # Handle string responses from Ollama models
        if isinstance(response, str):
            response = {
                "answer": response,
                "reasoning_steps": [response] if use_cot else [],
                "context": []
            }
        
        # Format response with reasoning steps if CoT is enabled
        if use_cot and isinstance(response, dict) and "reasoning_steps" in response:
            formatted_response = "🤔 Let me think about this step by step:\n\n"
            print("\nChain of Thought Reasoning Steps:")
            print("-" * 50)
            
            # Add each reasoning step with conclusion
            for i, step in enumerate(response["reasoning_steps"], 1):
                step_text = f"Step {i}:\n{step}\n"
                formatted_response += step_text
                print(step_text)
                
                # Add intermediate response to chat history to show progress
                history.append([None, f"🔄 Step {i} Conclusion:\n{step}"])
            
            # Add final answer
            print("\nFinal Answer:")
            print("-" * 50)
            final_answer = "\n🎯 Final Answer:\n" + response.get("answer", "No answer provided")
            formatted_response += final_answer
            print(final_answer)
            
            # Add sources if available
            if response.get("context"):
                print("\nSources Used:")
                print("-" * 50)
                sources_text = "\n📚 Sources used:\n"
                formatted_response += sources_text
                print(sources_text)
                
                for ctx in response["context"]:
                    if isinstance(ctx, dict) and "metadata" in ctx:
                        source = ctx["metadata"].get("source", "Unknown")
                        if "page_numbers" in ctx["metadata"]:
                            pages = ctx["metadata"].get("page_numbers", [])
                            source_line = f"- {source} (pages: {pages})\n"
                        else:
                            file_path = ctx["metadata"].get("file_path", "Unknown")
                            source_line = f"- {source} (file: {file_path})\n"
                        formatted_response += source_line
                        print(source_line)
            
            # Add final formatted response to history
            history.append([message, formatted_response])
        else:
            # For standard response (no CoT)
            formatted_response = response.get("answer", "No answer provided") if isinstance(response, dict) else str(response)
            print("\nStandard Response:")
            print("-" * 50)
            print(formatted_response)
            
            # Add sources if available
            if isinstance(response, dict) and response.get("context"):
                print("\nSources Used:")
                print("-" * 50)
                sources_text = "\n\n📚 Sources used:\n"
                formatted_response += sources_text
                print(sources_text)
                
                for ctx in response["context"]:
                    if isinstance(ctx, dict) and "metadata" in ctx:
                        source = ctx["metadata"].get("source", "Unknown")
                        if "page_numbers" in ctx["metadata"]:
                            pages = ctx["metadata"].get("page_numbers", [])
                            source_line = f"- {source} (pages: {pages})\n"
                        else:
                            file_path = ctx["metadata"].get("file_path", "Unknown")
                            source_line = f"- {source} (file: {file_path})\n"
                        formatted_response += source_line
                        print(source_line)
            
            history.append([message, formatted_response])
        
        print("\n" + "="*50)
        print("Response complete")
        print("="*50 + "\n")
        
        return history
    except Exception as e:
        error_msg = f"Error processing query: {str(e)}"
        print(f"\nError occurred:")
        print("-" * 50)
        print(error_msg)
        print("="*50 + "\n")
        history.append([message, error_msg])
        return history

# A2A Testing Functions
def test_a2a_health() -> str:
    """Test A2A health check"""
    try:
        response = a2a_client.health_check()
        if response.get("error"):
            return f"❌ Health Check Failed: {response['error']}"
        else:
            return f"✅ Health Check Passed: {json.dumps(response, indent=2)}"
    except Exception as e:
        return f"❌ Health Check Error: {str(e)}"

def test_a2a_agent_card() -> str:
    """Test A2A agent card retrieval"""
    try:
        response = a2a_client.get_agent_card()
        if response.get("error"):
            return f"❌ Agent Card Failed: {response['error']}"
        else:
            return f"✅ Agent Card Retrieved: {json.dumps(response, indent=2)}"
    except Exception as e:
        return f"❌ Agent Card Error: {str(e)}"

def test_a2a_document_query(query: str, collection: str, use_cot: bool) -> str:
    """Test A2A document query"""
    try:
        # Map collection names to A2A collection format
        collection_mapping = {
            "PDF Collection": "PDF",
            "Repository Collection": "Repository", 
            "Web Knowledge Base": "Web",
            "General Knowledge": "General"
        }
        a2a_collection = collection_mapping.get(collection, "General")
        
        response = a2a_client.make_request(
            "document.query",
            {
                "query": query,
                "collection": a2a_collection,
                "use_cot": use_cot,
                "max_results": 3
            },
            f"query-{int(time.time())}"
        )
        
        if response.get("error"):
            return f"❌ Document Query Failed: {json.dumps(response['error'], indent=2)}"
        else:
            result = response.get("result", {})
            answer = result.get("answer", "No answer provided")
            sources = result.get("sources", {})
            reasoning = result.get("reasoning_steps", [])
            
            response_text = f"✅ Document Query Success:\n\n"
            response_text += f"Answer: {answer}\n\n"
            
            if reasoning:
                response_text += f"Reasoning Steps:\n"
                for i, step in enumerate(reasoning, 1):
                    response_text += f"{i}. {step}\n"
                response_text += "\n"
            
            if sources:
                response_text += f"Sources: {json.dumps(sources, indent=2)}\n"
            
            return response_text
    except Exception as e:
        return f"❌ Document Query Error: {str(e)}"

def test_a2a_task_create(task_type: str, task_params: str) -> str:
    """Test A2A task creation"""
    global a2a_task_counter
    try:
        # Parse task parameters
        try:
            params = json.loads(task_params) if task_params.strip() else {}
        except json.JSONDecodeError:
            params = {"description": task_params}
        
        a2a_task_counter += 1
        task_id = f"gradio-task-{a2a_task_counter}"
        
        response = a2a_client.make_request(
            "task.create",
            {
                "task_type": task_type,
                "params": params
            },
            task_id
        )
        
        if response.get("error"):
            return f"❌ Task Creation Failed: {json.dumps(response['error'], indent=2)}"
        else:
            result = response.get("result", {})
            created_task_id = result.get("task_id", "unknown")
            
            # Store task for tracking
            a2a_tasks[created_task_id] = {
                "id": created_task_id,
                "type": task_type,
                "params": params,
                "created_at": datetime.now().isoformat(),
                "status": "created"
            }
            
            return f"✅ Task Created Successfully:\n\nTask ID: {created_task_id}\nType: {task_type}\nParams: {json.dumps(params, indent=2)}\nStatus: {result.get('status', 'unknown')}"
    except Exception as e:
        return f"❌ Task Creation Error: {str(e)}"

def test_a2a_task_status(task_id: str) -> str:
    """Test A2A task status check"""
    try:
        response = a2a_client.make_request(
            "task.status",
            {"task_id": task_id},
            f"status-{int(time.time())}"
        )
        
        if response.get("error"):
            return f"❌ Task Status Failed: {json.dumps(response['error'], indent=2)}"
        else:
            result = response.get("result", {})
            return f"✅ Task Status Retrieved:\n\n{json.dumps(result, indent=2)}"
    except Exception as e:
        return f"❌ Task Status Error: {str(e)}"

def test_a2a_agent_discover(capability: str) -> str:
    """Test A2A agent discovery"""
    try:
        response = a2a_client.make_request(
            "agent.discover",
            {"capability": capability},
            f"discover-{int(time.time())}"
        )
        
        if response.get("error"):
            return f"❌ Agent Discovery Failed: {json.dumps(response['error'], indent=2)}"
        else:
            result = response.get("result", {})
            agents = result.get("agents", [])
            
            response_text = f"✅ Agent Discovery Success:\n\n"
            response_text += f"Capability: {capability}\n"
            response_text += f"Found {len(agents)} agents:\n\n"
            
            for i, agent in enumerate(agents, 1):
                response_text += f"{i}. {json.dumps(agent, indent=2)}\n\n"
            
            return response_text
    except Exception as e:
        return f"❌ Agent Discovery Error: {str(e)}"

def get_a2a_task_list() -> str:
    """Get list of tracked A2A tasks"""
    if not a2a_tasks:
        return "No tasks tracked yet. Create a task first."
    
    response_text = "📋 Tracked A2A Tasks:\n\n"
    for task_id, task_info in a2a_tasks.items():
        response_text += f"Task ID: {task_id}\n"
        response_text += f"Type: {task_info['type']}\n"
        response_text += f"Created: {task_info['created_at']}\n"
        response_text += f"Status: {task_info['status']}\n"
        response_text += f"Params: {json.dumps(task_info['params'], indent=2)}\n"
        response_text += "-" * 50 + "\n"
    
    return response_text

def refresh_a2a_tasks() -> str:
    """Refresh status of all tracked tasks"""
    if not a2a_tasks:
        return "No tasks to refresh."
    
    response_text = "🔄 Refreshing Task Statuses:\n\n"
    for task_id in list(a2a_tasks.keys()):
        try:
            status_response = a2a_client.make_request(
                "task.status",
                {"task_id": task_id},
                f"refresh-{int(time.time())}"
            )
            
            if not status_response.get("error"):
                result = status_response.get("result", {})
                a2a_tasks[task_id]["status"] = result.get("status", "unknown")
                response_text += f"✅ {task_id}: {result.get('status', 'unknown')}\n"
            else:
                response_text += f"❌ {task_id}: Error checking status\n"
        except Exception as e:
            response_text += f"❌ {task_id}: {str(e)}\n"
    
    return response_text

# Individual test functions for quick test suite
def test_individual_health() -> str:
    """Individual health test"""
    return test_a2a_health()

def test_individual_card() -> str:
    """Individual agent card test"""
    return test_a2a_agent_card()

def test_individual_discover() -> str:
    """Individual agent discovery test"""
    return test_a2a_agent_discover("document.query")

def test_individual_query() -> str:
    """Individual document query test"""
    return test_a2a_document_query("What is machine learning?", "General Knowledge", False)

def test_individual_task() -> str:
    """Individual task creation test"""
    return test_a2a_task_create("individual_test", '{"description": "Individual test task", "test_type": "quick"}')

# A2A Chat Interface Functions
def a2a_chat(message: str, history: List[List[str]], agent_type: str, use_cot: bool, collection: str) -> List[List[str]]:
    """Process chat message using A2A protocol with distributed specialized agents for CoT"""
    try:
        print("\n" + "="*50)
        print(f"A2A Chat - New message: {message}")
        print(f"Agent: {agent_type}, CoT: {use_cot}, Collection: {collection}")
        print("="*50 + "\n")
        
        # Map collection names to A2A collection format
        collection_mapping = {
            "PDF Collection": "PDF",
            "Repository Collection": "Repository", 
            "Web Knowledge Base": "Web",
            "General Knowledge": "General"
        }
        a2a_collection = collection_mapping.get(collection, "General")
        
        if use_cot:
            # Use distributed specialized agents via A2A protocol
            print("🔄 Using distributed CoT agents via A2A protocol...")
            
            # Step 1: Call Planner Agent via A2A
            print("\n1️⃣ Calling Planner Agent...")
            planner_response = a2a_client.make_request(
                "agent.query",
                {
                    "agent_id": "planner_agent_v1",
                    "query": message,
                    "context": []
                },
                f"planner-{int(time.time())}"
            )
            
            if planner_response.get("error"):
                error_msg = f"Planner Error: {json.dumps(planner_response['error'], indent=2)}"
                print(f"❌ {error_msg}")
                history.append([message, error_msg])
                return history
            
            planner_result = planner_response.get("result", {})
            plan = planner_result.get("plan", "")
            steps = planner_result.get("steps", [])
            
            # Extract clean steps from plan (filter out empty lines)
            if not steps or len(steps) == 0:
                steps = [s.strip() for s in plan.split("\n") if s.strip() and not s.strip().startswith("Step")]
            
            print(f"✅ Planner created {len(steps)} steps")
            history.append([None, f"🎯 Planning:\n{plan}"])
            
            # Collect reasoning steps
            reasoning_steps = []
            all_context = []
            
            # Process each step: Research → Reason
            for i, step in enumerate(steps[:4], 1):  # Limit to 4 steps
                if not step.strip():
                    continue
                    
                print(f"\n{i+1}️⃣ Processing Step {i}: {step[:50]}...")
                
                # Step 2: Call Researcher Agent via A2A
                print(f"   🔍 Researching...")
                researcher_response = a2a_client.make_request(
                    "agent.query",
                    {
                        "agent_id": "researcher_agent_v1",
                        "query": message,
                        "step": step,
                        "context": []
                    },
                    f"researcher-{i}-{int(time.time())}"
                )
                
                if researcher_response.get("error"):
                    print(f"   ⚠️ Research skipped: {researcher_response.get('error')}")
                    findings = []
                else:
                    researcher_result = researcher_response.get("result", {})
                    findings = researcher_result.get("findings", [])
                    print(f"   ✅ Found {len(findings)} research items")
                
                all_context.extend(findings)
                
                # Step 3: Call Reasoner Agent via A2A
                print(f"   🤔 Reasoning...")
                reasoner_response = a2a_client.make_request(
                    "agent.query",
                    {
                        "agent_id": "reasoner_agent_v1",
                        "query": message,
                        "step": step,
                        "context": findings
                    },
                    f"reasoner-{i}-{int(time.time())}"
                )
                
                if reasoner_response.get("error"):
                    print(f"   ⚠️ Reasoning skipped: {reasoner_response.get('error')}")
                    conclusion = f"Unable to reason about: {step}"
                else:
                    reasoner_result = reasoner_response.get("result", {})
                    conclusion = reasoner_result.get("conclusion", "")
                    print(f"   ✅ Conclusion reached")
                
                reasoning_steps.append(conclusion)
                history.append([None, f"🔄 Step {i} - {step[:50]}...\n{conclusion}"])
            
            # Step 4: Call Synthesizer Agent via A2A
            print(f"\n5️⃣ Synthesizing final answer...")
            synthesizer_response = a2a_client.make_request(
                "agent.query",
                {
                    "agent_id": "synthesizer_agent_v1",
                    "query": message,
                    "reasoning_steps": reasoning_steps,
                    "context": all_context
                },
                f"synthesizer-{int(time.time())}"
            )
            
            if synthesizer_response.get("error"):
                error_msg = f"Synthesizer Error: {json.dumps(synthesizer_response['error'], indent=2)}"
                print(f"❌ {error_msg}")
                history.append([message, error_msg])
                return history
            
            synthesizer_result = synthesizer_response.get("result", {})
            final_answer = synthesizer_result.get("answer", "No answer provided")
            print(f"✅ Final answer synthesized")
            
            # Format final response
            formatted_response = f"🎯 Final Answer:\n{final_answer}"
            
            # Add sources if available from context
            if all_context:
                sources_text = "\n\n📚 Sources used:\n"
                seen_sources = set()
                for ctx in all_context:
                    if isinstance(ctx, dict) and "metadata" in ctx:
                        source = ctx["metadata"].get("source", "Unknown")
                        if source not in seen_sources:
                            sources_text += f"- {source}\n"
                            seen_sources.add(source)
                formatted_response += sources_text
            
            history.append([message, formatted_response])
            
            print("\n" + "="*50)
            print("✅ A2A CoT Response complete")
            print("="*50 + "\n")
            
        else:
            # Standard mode - use document.query without CoT
            print("📝 Using standard A2A document query...")
            response = a2a_client.make_request(
                "document.query",
                {
                    "query": message,
                    "collection": a2a_collection,
                    "use_cot": False,
                    "max_results": 5
                },
                f"chat-{int(time.time())}"
            )
            
            if response.get("error"):
                error_msg = f"A2A Error: {json.dumps(response['error'], indent=2)}"
                print(f"❌ A2A Error detected: {error_msg}")
                history.append([message, error_msg])
                return history
            
            result = response.get("result", {})
            answer = result.get("answer", "No answer provided")
            sources = result.get("sources", {})
            
            formatted_response = answer
            
            # Add sources if available
            if sources:
                sources_text = "\n\n📚 Sources used:\n"
                for source, details in sources.items():
                    if isinstance(details, str):
                        sources_text += f"- {source}: {details}\n"
                    else:
                        sources_text += f"- {source}\n"
                formatted_response += sources_text
            
            history.append([message, formatted_response])
            
            print("\n" + "="*50)
            print("✅ A2A Standard Response complete")
            print("="*50 + "\n")
        
        return history
        
    except Exception as e:
        error_msg = f"A2A Chat Error: {str(e)}"
        print(f"\nA2A Chat Error:")
        print("-" * 50)
        print(error_msg)
        import traceback
        print(traceback.format_exc())
        print("="*50 + "\n")
        history.append([message, error_msg])
        return history

def create_interface():
    """Create Gradio interface"""
    with gr.Blocks(title="Agentic RAG System", theme=gr.themes.Soft()) as interface:
        gr.Markdown("""
        # 🤖 Agentic RAG System
        
        Upload PDFs, process web content, repositories, and chat with your documents using local or OpenAI models.
        
        > **Note on Performance**: When using the Local (Mistral) model, initial loading can take 1-5 minutes, and each query may take 30-60 seconds to process depending on your hardware. OpenAI queries are typically much faster.
        """)
        
        # Show Oracle DB status
        if ORACLE_DB_AVAILABLE and hasattr(vector_store, 'connection'):
            gr.Markdown("""
            <div style="padding: 10px; background-color: #d4edda; color: #155724; border-radius: 5px; margin-bottom: 15px;">
            ✅ <strong>Oracle AI Database 26ai</strong> is active and being used for vector storage.
            </div>
            """)
        else:
            gr.Markdown("""
            <div style="padding: 10px; background-color: #f8d7da; color: #721c24; border-radius: 5px; margin-bottom: 15px;">
            ⚠️ <strong>ChromaDB</strong> is being used for vector storage. Oracle AI Database 26ai is not available.
            </div>
            """)
        
        # Create model choices list for reuse
        model_choices = []
        # Only Ollama models (no more local Mistral deployments)
        model_choices.extend([
            "qwq",
            "gemma3",
            "llama3.3",
            "phi4",
            "mistral",
            "llava",
            "phi3",
            "deepseek-r1"
        ])
        if openai_key:
            model_choices.append("openai")
        
        # Set default model to qwq
        default_model = "qwq"
        
        # Model Management Tab (First Tab)
        with gr.Tab("Model Management"):
            gr.Markdown("""
            ## Model Selection
            Choose your preferred model for the conversation.
            """)
            
            with gr.Row():
                with gr.Column():
                    model_dropdown = gr.Dropdown(
                        choices=model_choices,
                        value=default_model,
                        label="Select Model",
                        info="Choose the model to use for the conversation"
                    )
                    download_button = gr.Button("Download Selected Model")
                    model_status = gr.Textbox(
                        label="Download Status",
                        placeholder="Select a model and click Download to begin...",
                        interactive=False
                    )
            
            # Add model FAQ section
            gr.Markdown("""
            ## Model FAQ
            
            | Model | Parameters | Size | Download Command |
            |-------|------------|------|------------------|
            | qwq | 32B | 20GB | qwq:latest |
            | gemma3 | 4B | 3.3GB | gemma3:latest |
            | llama3.3 | 70B | 43GB | llama3.3:latest |
            | phi4 | 14B | 9.1GB | phi4:latest |
            | mistral | 7B | 4.1GB | mistral:latest |
            | llava | 7B | 4.5GB | llava:latest |
            | phi3 | 4B | 4.0GB | phi3:latest |
            | deepseek-r1 | 7B | 4.7GB | deepseek-r1:latest |
            
            Note: All models are available through Ollama. Make sure Ollama is running on your system.
            """)
        
        # Document Processing Tab
        with gr.Tab("Document Processing"):
            with gr.Row():
                with gr.Column():
                    pdf_file = gr.File(label="Upload PDF")
                    pdf_button = gr.Button("Process PDF")
                    pdf_output = gr.Textbox(label="PDF Processing Output")
                    
                with gr.Column():
                    url_input = gr.Textbox(label="Enter URL")
                    url_button = gr.Button("Process URL")
                    url_output = gr.Textbox(label="URL Processing Output")
                    
                with gr.Column():
                    repo_input = gr.Textbox(label="Enter Repository Path or URL")
                    repo_button = gr.Button("Process Repository")
                    repo_output = gr.Textbox(label="Repository Processing Output")
        
        # Define collection choices once to ensure consistency
        collection_choices = [
            "PDF Collection",
            "Repository Collection", 
            "Web Knowledge Base",
            "General Knowledge"
        ]
        
        with gr.Tab("Standard Chat Interface"):
            with gr.Row():
                with gr.Column(scale=1):
                    standard_agent_dropdown = gr.Dropdown(
                        choices=model_choices,
                        value=default_model if default_model in model_choices else model_choices[0] if model_choices else None,
                        label="Select Agent"
                    )
                with gr.Column(scale=1):
                    standard_collection_dropdown = gr.Dropdown(
                        choices=collection_choices,
                        value=collection_choices[0],
                        label="Select Knowledge Base",
                        info="Choose which knowledge base to use for answering questions"
                    )
            gr.Markdown("""
            > **Collection Selection**: 
            > - This interface ALWAYS uses the selected collection without performing query analysis.
            > - "PDF Collection": Will ALWAYS search the PDF documents regardless of query type.
            > - "Repository Collection": Will ALWAYS search the repository code regardless of query type.
            > - "Web Knowledge Base": Will ALWAYS search web content regardless of query type.
            > - "General Knowledge": Will ALWAYS use the model's built-in knowledge without searching collections.
            """)
            standard_chatbot = gr.Chatbot(height=400)
            with gr.Row():
                standard_msg = gr.Textbox(label="Your Message", scale=9)
                standard_send = gr.Button("Send", scale=1)
            standard_clear = gr.Button("Clear Chat")

        with gr.Tab("Chain of Thought Chat Interface"):
            with gr.Row():
                with gr.Column(scale=1):
                    cot_agent_dropdown = gr.Dropdown(
                        choices=model_choices,
                        value=default_model if default_model in model_choices else model_choices[0] if model_choices else None,
                        label="Select Agent"
                    )
                with gr.Column(scale=1):
                    cot_collection_dropdown = gr.Dropdown(
                        choices=collection_choices,
                        value=collection_choices[0],
                        label="Select Knowledge Base",
                        info="Choose which knowledge base to use for answering questions"
                    )
            gr.Markdown("""
            > **Collection Selection**: 
            > - When a specific collection is selected, the system will ALWAYS use that collection without analysis:
            >   - "PDF Collection": Will ALWAYS search the PDF documents.
            >   - "Repository Collection": Will ALWAYS search the repository code.
            >   - "Web Knowledge Base": Will ALWAYS search web content.
            >   - "General Knowledge": Will ALWAYS use the model's built-in knowledge.
            > - This interface shows step-by-step reasoning and may perform query analysis when needed.
            """)
            cot_chatbot = gr.Chatbot(height=400)
            with gr.Row():
                cot_msg = gr.Textbox(label="Your Message", scale=9)
                cot_send = gr.Button("Send", scale=1)
            cot_clear = gr.Button("Clear Chat")
        
        # A2A Chat Interface Tab
        with gr.Tab("A2A Chat Interface"):
            gr.Markdown("""
            # 🤖 A2A Chat Interface
            
            Chat with your documents using the A2A (Agent2Agent) protocol. This interface provides the same 
            experience as the standard chat interfaces but communicates through the A2A server.
            
            > **Prerequisites**: A2A server must be running (`python main.py` on port 8000)
            > **Note**: This interface uses A2A protocol for all communication, providing agent-to-agent 
            > interaction capabilities while maintaining the familiar chat experience.
            """)
            
            with gr.Row():
                with gr.Column(scale=1):
                    a2a_agent_dropdown = gr.Dropdown(
                        choices=model_choices,
                        value=default_model if default_model in model_choices else model_choices[0] if model_choices else None,
                        label="Select Agent",
                        info="Agent selection (for display purposes - A2A server handles the actual model)"
                    )
                with gr.Column(scale=1):
                    a2a_collection_dropdown = gr.Dropdown(
                        choices=collection_choices,
                        value=collection_choices[0],
                        label="Select Knowledge Base",
                        info="Choose which knowledge base to use for answering questions"
                    )
            
            gr.Markdown("""
            > **Collection Selection**: 
            > - When a specific collection is selected, the A2A server will use that collection:
            >   - "PDF Collection": Will search the PDF documents via A2A
            >   - "Repository Collection": Will search the repository code via A2A
            >   - "Web Knowledge Base": Will search web content via A2A
            >   - "General Knowledge": Will use the model's built-in knowledge via A2A
            > - All communication goes through the A2A protocol for agent-to-agent interaction
            """)
            
            with gr.Row():
                with gr.Column(scale=1):
                    a2a_use_cot_checkbox = gr.Checkbox(
                        label="Use Chain of Thought", 
                        value=False,
                        info="Enable step-by-step reasoning through A2A"
                    )
                with gr.Column(scale=1):
                    a2a_clear_button = gr.Button("Clear Chat", variant="secondary")
            
            a2a_chatbot = gr.Chatbot(height=400, label="A2A Chat")
            with gr.Row():
                a2a_msg = gr.Textbox(label="Your Message", scale=9, placeholder="Ask a question...")
                a2a_send = gr.Button("Send", scale=1, variant="primary")
            
            # A2A Status indicator
            with gr.Row():
                a2a_status_button = gr.Button("🔍 Check A2A Status", variant="secondary", size="sm")
                a2a_status_output = gr.Textbox(label="A2A Status", lines=2, interactive=False, visible=False)
        
        # A2A Testing Tab
        with gr.Tab("A2A Protocol Testing"):
            gr.Markdown("""
            # 🤖 A2A Protocol Testing Interface
            
            Test the Agent2Agent (A2A) protocol functionality. Make sure the A2A server is running on `localhost:8000`.
            
            > **Note**: This interface tests the A2A protocol by making HTTP requests to the A2A server. 
            > The server must be running separately using `python main.py`.
            """)
            
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 🔍 Basic A2A Tests")
                    
                    # Health Check
                    health_button = gr.Button("🏥 Health Check", variant="secondary")
                    health_output = gr.Textbox(label="Health Check Result", lines=5, interactive=False)
                    
                    # Agent Card
                    agent_card_button = gr.Button("🃏 Get Agent Card", variant="secondary")
                    agent_card_output = gr.Textbox(label="Agent Card Result", lines=8, interactive=False)
                    
                    # Agent Discovery
                    with gr.Row():
                        discover_capability = gr.Textbox(
                            label="Capability to Discover", 
                            value="document.query",
                            placeholder="e.g., document.query, task.create"
                        )
                        discover_button = gr.Button("🔍 Discover Agents", variant="secondary")
                    discover_output = gr.Textbox(label="Agent Discovery Result", lines=6, interactive=False)
                
                with gr.Column(scale=1):
                    gr.Markdown("### 📄 Document Query Testing")
                    
                    with gr.Row():
                        a2a_query = gr.Textbox(
                            label="Query", 
                            value="What is artificial intelligence?",
                            placeholder="Enter your question"
                        )
                        a2a_collection = gr.Dropdown(
                            choices=["PDF Collection", "Repository Collection", "Web Knowledge Base", "General Knowledge"],
                            value="General Knowledge",
                            label="Collection"
                        )
                    
                    a2a_use_cot = gr.Checkbox(label="Use Chain of Thought", value=False)
                    a2a_query_button = gr.Button("🔍 Query Documents", variant="primary")
                    a2a_query_output = gr.Textbox(label="Document Query Result", lines=10, interactive=False)
            
            gr.Markdown("---")
            
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 📋 Task Management")
                    
                    with gr.Row():
                        task_type = gr.Textbox(
                            label="Task Type", 
                            value="document_processing",
                            placeholder="e.g., document_processing, analysis_task"
                        )
                        task_params = gr.Textbox(
                            label="Task Parameters (JSON)", 
                            value='{"document": "test.pdf", "chunk_count": 10}',
                            placeholder='{"key": "value"}'
                        )
                    
                    task_create_button = gr.Button("➕ Create Task", variant="primary")
                    task_create_output = gr.Textbox(label="Task Creation Result", lines=6, interactive=False)
                    
                    with gr.Row():
                        task_id_input = gr.Textbox(
                            label="Task ID to Check", 
                            placeholder="Enter task ID from creation result"
                        )
                        task_status_button = gr.Button("📊 Check Task Status", variant="secondary")
                    task_status_output = gr.Textbox(label="Task Status Result", lines=6, interactive=False)
                
                with gr.Column(scale=1):
                    gr.Markdown("### 📊 Task Management Dashboard")
                    
                    task_list_button = gr.Button("📋 Show All Tasks", variant="secondary")
                    task_refresh_button = gr.Button("🔄 Refresh Task Statuses", variant="secondary")
                    task_dashboard_output = gr.Textbox(label="Task Dashboard", lines=12, interactive=False)
            
            gr.Markdown("---")
            
            with gr.Row():
                gr.Markdown("""
                ### 🚀 Quick Test Suite
                
                Run individual A2A tests or all tests in sequence to verify the complete functionality.
                """)
                
                with gr.Column(scale=1):
                    gr.Markdown("**Individual Tests:**")
                    individual_health_button = gr.Button("🏥 Test Health", variant="secondary", size="sm")
                    individual_card_button = gr.Button("🃏 Test Agent Card", variant="secondary", size="sm")
                    individual_discover_button = gr.Button("🔍 Test Discovery", variant="secondary", size="sm")
                    individual_query_button = gr.Button("📄 Test Query", variant="secondary", size="sm")
                    individual_task_button = gr.Button("📋 Test Task", variant="secondary", size="sm")
                
                with gr.Column(scale=1):
                    gr.Markdown("**Complete Test Suite:**")
                    run_all_tests_button = gr.Button("🧪 Run All A2A Tests", variant="primary", size="lg")
                
                all_tests_output = gr.Textbox(label="Test Results", lines=15, interactive=False)
        
        # Event handlers
        pdf_button.click(process_pdf, inputs=[pdf_file], outputs=[pdf_output])
        url_button.click(process_url, inputs=[url_input], outputs=[url_output])
        repo_button.click(process_repo, inputs=[repo_input], outputs=[repo_output])
        
        # Model download event handler
        download_button.click(download_model, inputs=[model_dropdown], outputs=[model_status])
        
        # Standard chat handlers
        standard_msg.submit(
            chat,
            inputs=[
                standard_msg,
                standard_chatbot,
                standard_agent_dropdown,
                gr.State(False),  # use_cot=False
                standard_collection_dropdown
            ],
            outputs=[standard_chatbot]
        )
        standard_send.click(
            chat,
            inputs=[
                standard_msg,
                standard_chatbot,
                standard_agent_dropdown,
                gr.State(False),  # use_cot=False
                standard_collection_dropdown
            ],
            outputs=[standard_chatbot]
        )
        standard_clear.click(lambda: None, None, standard_chatbot, queue=False)
        
        # CoT chat handlers
        cot_msg.submit(
            chat,
            inputs=[
                cot_msg,
                cot_chatbot,
                cot_agent_dropdown,
                gr.State(True),  # use_cot=True
                cot_collection_dropdown
            ],
            outputs=[cot_chatbot]
        )
        cot_send.click(
            chat,
            inputs=[
                cot_msg,
                cot_chatbot,
                cot_agent_dropdown,
                gr.State(True),  # use_cot=True
                cot_collection_dropdown
            ],
            outputs=[cot_chatbot]
        )
        cot_clear.click(lambda: None, None, cot_chatbot, queue=False)
        
        # A2A Testing Event Handlers
        health_button.click(test_a2a_health, outputs=[health_output])
        agent_card_button.click(test_a2a_agent_card, outputs=[agent_card_output])
        discover_button.click(test_a2a_agent_discover, inputs=[discover_capability], outputs=[discover_output])
        a2a_query_button.click(test_a2a_document_query, inputs=[a2a_query, a2a_collection, a2a_use_cot], outputs=[a2a_query_output])
        task_create_button.click(test_a2a_task_create, inputs=[task_type, task_params], outputs=[task_create_output])
        task_status_button.click(test_a2a_task_status, inputs=[task_id_input], outputs=[task_status_output])
        task_list_button.click(get_a2a_task_list, outputs=[task_dashboard_output])
        task_refresh_button.click(refresh_a2a_tasks, outputs=[task_dashboard_output])
        
        # Run all tests function
        def run_all_a2a_tests():
            """Run all A2A tests in sequence"""
            results = []
            results.append("🧪 Running Complete A2A Test Suite")
            results.append("=" * 60)
            
            # Test 1: Health Check
            results.append("\n1. 🏥 Health Check")
            results.append("-" * 30)
            health_result = test_a2a_health()
            results.append(health_result)
            
            # Test 2: Agent Card
            results.append("\n2. 🃏 Agent Card")
            results.append("-" * 30)
            card_result = test_a2a_agent_card()
            results.append(card_result)
            
            # Test 3: Agent Discovery
            results.append("\n3. 🔍 Agent Discovery")
            results.append("-" * 30)
            discover_result = test_a2a_agent_discover("document.query")
            results.append(discover_result)
            
            # Test 4: Document Query
            results.append("\n4. 📄 Document Query")
            results.append("-" * 30)
            query_result = test_a2a_document_query("What is machine learning?", "General Knowledge", False)
            results.append(query_result)
            
            # Test 5: Task Creation
            results.append("\n5. 📋 Task Creation")
            results.append("-" * 30)
            task_result = test_a2a_task_create("test_task", '{"description": "A2A test task", "priority": "high"}')
            results.append(task_result)
            
            # Test 6: Task Status (if task was created)
            if "Task ID:" in task_result and "gradio-task-" in task_result:
                # Extract task ID from result
                task_id = None
                for line in task_result.split('\n'):
                    if "Task ID:" in line:
                        task_id = line.split("Task ID:")[1].strip()
                        break
                
                if task_id:
                    results.append("\n6. 📊 Task Status Check")
                    results.append("-" * 30)
                    status_result = test_a2a_task_status(task_id)
                    results.append(status_result)
            
            results.append("\n" + "=" * 60)
            results.append("🎉 A2A Test Suite Complete!")
            
            return "\n".join(results)
        
        run_all_tests_button.click(run_all_a2a_tests, outputs=[all_tests_output])
        
        # Individual test event handlers
        individual_health_button.click(test_individual_health, outputs=[all_tests_output])
        individual_card_button.click(test_individual_card, outputs=[all_tests_output])
        individual_discover_button.click(test_individual_discover, outputs=[all_tests_output])
        individual_query_button.click(test_individual_query, outputs=[all_tests_output])
        individual_task_button.click(test_individual_task, outputs=[all_tests_output])
        
        # A2A Chat Interface Event Handlers
        a2a_msg.submit(
            a2a_chat,
            inputs=[
                a2a_msg,
                a2a_chatbot,
                a2a_agent_dropdown,
                a2a_use_cot_checkbox,
                a2a_collection_dropdown
            ],
            outputs=[a2a_chatbot]
        )
        a2a_send.click(
            a2a_chat,
            inputs=[
                a2a_msg,
                a2a_chatbot,
                a2a_agent_dropdown,
                a2a_use_cot_checkbox,
                a2a_collection_dropdown
            ],
            outputs=[a2a_chatbot]
        )
        a2a_clear_button.click(lambda: None, None, a2a_chatbot, queue=False)
        a2a_status_button.click(test_a2a_health, outputs=[a2a_status_output])
        
        # Instructions
        gr.Markdown("""
        ## Instructions
        
        1. **Document Processing**:
           - Upload PDFs using the file uploader
           - Process web content by entering URLs
           - Process repositories by entering paths or GitHub URLs
           - All processed content is added to the knowledge base
        
        2. **Standard Chat Interface**:
           - Quick responses without detailed reasoning steps
           - Select your preferred agent (Ollama qwen2 by default)
           - Select which knowledge collection to query:
             - **PDF Collection**: Always searches PDF documents
             - **Repository Collection**: Always searches code repositories
             - **Web Knowledge Base**: Always searches web content
             - **General Knowledge**: Uses the model's built-in knowledge without searching collections
        
        3. **Chain of Thought Chat Interface**:
           - Detailed responses with step-by-step reasoning
           - See the planning, research, reasoning, and synthesis steps
           - Great for complex queries or when you want to understand the reasoning process
           - May take longer but provides more detailed and thorough answers
           - Same collection selection options as the Standard Chat Interface
        
        4. **A2A Chat Interface**:
           - Same chat experience as standard interfaces but uses A2A protocol
           - **Prerequisites**: A2A server must be running (`python main.py` on port 8000)
           - **Agent-to-Agent Communication**: All queries go through A2A protocol
           - **Collection Support**: PDF, Repository, Web, and General Knowledge collections
           - **Chain of Thought**: Step-by-step reasoning through A2A
           - **Status Monitoring**: Check A2A server connectivity
           - **Same UI**: Familiar chat interface with A2A backend
        
        5. **A2A Protocol Testing**:
           - Test the Agent2Agent (A2A) protocol functionality
           - **Prerequisites**: A2A server must be running (`python main.py` on port 8000)
           - **Health Check**: Verify A2A server connectivity
           - **Agent Card**: Get agent capability information
           - **Agent Discovery**: Find agents with specific capabilities
           - **Document Query**: Test A2A document querying with different collections
           - **Task Management**: Create, monitor, and track long-running tasks
           - **Task Dashboard**: View all tracked tasks and their statuses
           - **Complete Test Suite**: Run all A2A tests in sequence
        
        6. **Performance Expectations**:
           - **Ollama models**: Typically faster inference, default is qwen2
           - **Local (Mistral) model**: Initial loading takes 1-5 minutes, each query takes 30-60 seconds
           - **OpenAI model**: Fast responses, typically a few seconds per query
           - Chain of Thought reasoning takes longer for all models
           - **A2A requests**: Depends on A2A server performance and network latency
           - **A2A Chat Interface**: Same performance as A2A server + network overhead
        
        Note: The interface will automatically detect available models based on your configuration:
        - Ollama models are the default option (requires Ollama to be installed and running)
        - Local Mistral model requires HuggingFace token in `config.yaml` (fallback option)
        - OpenAI model requires API key in `.env` file
        - A2A testing requires the A2A server to be running separately
        """)
    
    return interface

def main():
    # Check configuration
    try:
        import ollama
        try:
            # Check if Ollama is running and list available models
            models = ollama.list().models
            available_models = [model.model for model in models]
            
            # Check if any default models are available
            if "qwen2" not in available_models and "qwen2:latest" not in available_models and \
               "llama3" not in available_models and "llama3:latest" not in available_models and \
               "phi3" not in available_models and "phi3:latest" not in available_models:
                print("⚠️ Warning: Ollama is running but no default models (qwen2, llama3, phi3) are available.")
                print("Please download a model through the Model Management tab or run:")
                print("    ollama pull qwen2")
                print("    ollama pull llama3")
                print("    ollama pull phi3")
            else:
                available_default_models = []
                for model in ["qwen2", "llama3", "phi3"]:
                    if model in available_models or f"{model}:latest" in available_models:
                        available_default_models.append(model)
                
                print(f"✅ Ollama is running with available default models: {', '.join(available_default_models)}")
                print(f"All available models: {', '.join(available_models)}")
        except Exception as e:
            print(f"⚠️ Warning: Ollama is installed but not running or encountered an error: {str(e)}")
            print("Please start Ollama before using the interface.")
    except ImportError:
        print("⚠️ Warning: Ollama package not installed. Please install with: pip install ollama")
        
    if not hf_token and not openai_key:
        print("⚠️ Warning: Neither HuggingFace token nor OpenAI key found. Using Ollama only.")
    
    # Launch interface
    interface = create_interface()
    interface.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=True,
        inbrowser=True
    )

def download_model(model_type: str) -> str:
    """Download a model and return status message"""
    try:
        print(f"Downloading model: {model_type}")
        
        # Parse model type to determine model and quantization
        quantization = None
        model_name = None
        
        if "4-bit" in model_type or "8-bit" in model_type:
            # For HF models, we need the token
            if not hf_token:
                return "❌ Error: HuggingFace token not found in config.yaml. Please add your token first."
            
            model_name = "mistralai/Mistral-7B-Instruct-v0.2"  # Default model
            if "4-bit" in model_type:
                quantization = "4bit"
            elif "8-bit" in model_type:
                quantization = "8bit"
                
            # Start download timer
            start_time = time.time()
            
            try:
                from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
                
                # Download tokenizer first (smaller download to check access)
                try:
                    tokenizer = AutoTokenizer.from_pretrained(model_name, token=hf_token)
                except Exception as e:
                    if "401" in str(e):
                        return f"❌ Error: This model is gated. Please accept the terms on the Hugging Face website: https://huggingface.co/{model_name}"
                    else:
                        return f"❌ Error downloading tokenizer: {str(e)}"
                
                # Set up model loading parameters
                model_kwargs = {
                    "token": hf_token,
                    "device_map": None,  # Don't load on GPU for download only
                }
                
                # Apply quantization if specified
                if quantization == '4bit':
                    try:
                        quantization_config = BitsAndBytesConfig(
                            load_in_4bit=True,
                            bnb_4bit_compute_dtype=torch.float16,
                            bnb_4bit_use_double_quant=True,
                            bnb_4bit_quant_type="nf4"
                        )
                        model_kwargs["quantization_config"] = quantization_config
                    except ImportError:
                        return "❌ Error: bitsandbytes not installed. Please install with: pip install bitsandbytes>=0.41.0"
                elif quantization == '8bit':
                    try:
                        quantization_config = BitsAndBytesConfig(load_in_8bit=True)
                        model_kwargs["quantization_config"] = quantization_config
                    except ImportError:
                        return "❌ Error: bitsandbytes not installed. Please install with: pip install bitsandbytes>=0.41.0"
                
                # Download model (but don't load it fully to save memory)
                AutoModelForCausalLM.from_pretrained(
                    model_name,
                    **model_kwargs
                )
                
                # Calculate download time
                download_time = time.time() - start_time
                return f"✅ Successfully downloaded {model_type} in {download_time:.1f} seconds."
                
            except Exception as e:
                return f"❌ Error downloading model: {str(e)}"
        # all ollama models
        else:
            # Extract model name from model_type
            # Remove the 'Ollama - ' prefix and any leading/trailing whitespace
            model_name = model_type.replace("Ollama - ", "").strip()
            
            # Use Ollama to pull the model
            try:
                import ollama
                
                print(f"Pulling Ollama model: {model_name}")
                start_time = time.time()
                
                # Check if model already exists
                try:
                    models = ollama.list().models
                    available_models = [model.model for model in models]
                    
                    # Check for model with or without :latest suffix
                    if model_name in available_models or f"{model_name}:latest" in available_models:
                        return f"✅ Model {model_name} is already available in Ollama."
                except Exception:
                    # If we can't check, proceed with pull anyway
                    pass
                
                # Pull the model with progress tracking
                progress_text = ""
                for progress in ollama.pull(model_name, stream=True):
                    status = progress.get('status')
                    if status:
                        progress_text = f"Status: {status}"
                        print(progress_text)
                    
                    # Show download progress
                    if 'completed' in progress and 'total' in progress:
                        completed = progress['completed']
                        total = progress['total']
                        if total > 0:
                            percent = (completed / total) * 100
                            progress_text = f"Downloading: {percent:.1f}% ({completed}/{total})"
                            print(progress_text)
                
                # Calculate download time
                download_time = time.time() - start_time
                return f"✅ Successfully pulled Ollama model {model_name} in {download_time:.1f} seconds."
                
            except ImportError:
                return "❌ Error: ollama not installed. Please install with: pip install ollama"
            except ConnectionError:
                return "❌ Error: Could not connect to Ollama. Please make sure Ollama is installed and running."
            except Exception as e:
                return f"❌ Error pulling Ollama model: {str(e)}"
    
    except Exception as e:
        return f"❌ Error: {str(e)}"

if __name__ == "__main__":
    main() 