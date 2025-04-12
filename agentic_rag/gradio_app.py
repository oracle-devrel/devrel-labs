import gradio as gr
import os
from typing import List, Dict, Any
from pathlib import Path
import tempfile
from dotenv import load_dotenv
import yaml
import torch
import time

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
        print("Using Oracle DB 23ai for vector storage")
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
        
        # Format response with reasoning steps if CoT is enabled
        if use_cot and "reasoning_steps" in response:
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
            final_answer = "\n🎯 Final Answer:\n" + response["answer"]
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
            formatted_response = response["answer"]
            print("\nStandard Response:")
            print("-" * 50)
            print(formatted_response)
            
            # Add sources if available
            if response.get("context"):
                print("\nSources Used:")
                print("-" * 50)
                sources_text = "\n\n📚 Sources used:\n"
                formatted_response += sources_text
                print(sources_text)
                
                for ctx in response["context"]:
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
            ✅ <strong>Oracle DB 23ai</strong> is active and being used for vector storage.
            </div>
            """)
        else:
            gr.Markdown("""
            <div style="padding: 10px; background-color: #f8d7da; color: #721c24; border-radius: 5px; margin-bottom: 15px;">
            ⚠️ <strong>ChromaDB</strong> is being used for vector storage. Oracle DB 23ai is not available.
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
        
        4. **Performance Expectations**:
           - **Ollama models**: Typically faster inference, default is qwen2
           - **Local (Mistral) model**: Initial loading takes 1-5 minutes, each query takes 30-60 seconds
           - **OpenAI model**: Fast responses, typically a few seconds per query
           - Chain of Thought reasoning takes longer for all models
        
        Note: The interface will automatically detect available models based on your configuration:
        - Ollama models are the default option (requires Ollama to be installed and running)
        - Local Mistral model requires HuggingFace token in `config.yaml` (fallback option)
        - OpenAI model requires API key in `.env` file
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