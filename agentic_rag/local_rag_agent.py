from typing import List, Dict, Any, Optional
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
import torch
from store import VectorStore
from agents.agent_factory import create_agents
import argparse
import yaml
import os
import logging
import time
import json
from pathlib import Path
try:
    from OraDBVectorStore import OraDBVectorStore
    ORACLE_DB_AVAILABLE = True
except ImportError:
    ORACLE_DB_AVAILABLE = False
    print("Oracle DB support not available. Install with: pip install oracledb sentence-transformers")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

class LocalLLM:
    """Wrapper for local LLM to match LangChain's ChatOpenAI interface"""
    def __init__(self, pipeline):
        self.pipeline = pipeline
    
    def invoke(self, messages):
        # Convert messages to a single prompt
        prompt = "\n".join([msg.content for msg in messages])
        result = self.pipeline(
            prompt,
            max_new_tokens=512,
            do_sample=True,
            temperature=0.1,
            top_p=0.95,
            return_full_text=False
        )[0]["generated_text"]
        
        # Create a response object with content attribute
        class Response:
            def __init__(self, content):
                self.content = content
        
        return Response(result.strip())

class OllamaModelHandler:
    """Handler for Ollama models"""
    def __init__(self, model_name: str):
        """Initialize Ollama model handler
        
        Args:
            model_name: Name of the Ollama model to use
        """
        # Remove the 'ollama:' prefix if present
        self.model_name = model_name.replace("ollama:", "") if model_name.startswith("ollama:") else model_name
        self._check_ollama_running()
    
    def _check_ollama_running(self):
        """Check if Ollama is running and the model is available"""
        try:
            import ollama
            
            # Check if Ollama is running
            try:
                models = ollama.list().models
                available_models = [model.model for model in models]
                print(f"Available Ollama models: {', '.join(available_models)}")
                
                # Check if the requested model is available
                if self.model_name not in available_models:
                    # Try with :latest suffix
                    if f"{self.model_name}:latest" in available_models:
                        self.model_name = f"{self.model_name}:latest"
                        print(f"Using model with :latest suffix: {self.model_name}")
                    else:
                        print(f"Model '{self.model_name}' not found in Ollama. Available models: {', '.join(available_models)}")
                        print(f"You can pull it with: ollama pull {self.model_name}")
            except Exception as e:
                raise ConnectionError(f"Failed to connect to Ollama. Please make sure Ollama is running. Error: {str(e)}")
                
        except ImportError:
            raise ImportError("Failed to import ollama. Please install with: pip install ollama")
    
    def __call__(self, prompt, max_new_tokens=512, temperature=0.1, top_p=0.95, **kwargs):
        """Generate text using the Ollama model"""
        try:
            import ollama
            
            # Generate text
            response = ollama.generate(
                model=self.model_name,
                prompt=prompt,
                options={
                    "num_predict": max_new_tokens,
                    "temperature": temperature,
                    "top_p": top_p
                }
            )
            
            # Format result to match transformers pipeline output
            formatted_result = [{
                "generated_text": response["response"]
            }]
            
            return formatted_result
            
        except Exception as e:
            raise Exception(f"Failed to generate text with Ollama: {str(e)}")

class LocalRAGAgent:
    def __init__(self, vector_store: VectorStore = None, model_name: str = "mistralai/Mistral-7B-Instruct-v0.2", 
                 use_cot: bool = False, collection: str = None, skip_analysis: bool = False,
                 quantization: str = None, use_oracle_db: bool = True):
        """Initialize local RAG agent with vector store and local LLM
        
        Args:
            vector_store: Vector store for retrieving context (if None, will create one)
            model_name: HuggingFace model name/path or Ollama model name
            use_cot: Whether to use Chain of Thought reasoning
            collection: Collection to search in (PDF, Repository, or General Knowledge)
            skip_analysis: Whether to skip query analysis (kept for backward compatibility)
            quantization: Quantization method to use (None, '4bit', '8bit')
            use_oracle_db: Whether to use Oracle DB for vector storage (if False, uses ChromaDB)
        """
        # Initialize vector store if not provided
        self.use_oracle_db = use_oracle_db and ORACLE_DB_AVAILABLE
        
        if vector_store is None:
            if self.use_oracle_db:
                try:
                    self.vector_store = OraDBVectorStore()
                    print("Using Oracle DB for vector storage")
                except ValueError as ve:
                    if "credentials not found" in str(ve):
                        print(f"Oracle DB credentials not found in config.yaml: {str(ve)}")
                        print("Falling back to ChromaDB")
                    else:
                        print(f"Oracle DB initialization error: {str(ve)}")
                        print("Falling back to ChromaDB")
                    self.vector_store = VectorStore(persist_directory="embeddings")
                    self.use_oracle_db = False
                except Exception as e:
                    print(f"Error initializing Oracle DB: {str(e)}")
                    print("Falling back to ChromaDB")
                    self.vector_store = VectorStore(persist_directory="embeddings")
                    self.use_oracle_db = False
            else:
                self.vector_store = VectorStore(persist_directory="embeddings")
                print("Using ChromaDB for vector storage")
        else:
            self.vector_store = vector_store
            # Determine type of vector store
            self.use_oracle_db = hasattr(vector_store, 'connection') and hasattr(vector_store, 'cursor')
        
        self.use_cot = use_cot
        self.collection = collection
        self.quantization = quantization
        self.model_name = model_name
        # skip_analysis parameter kept for backward compatibility but no longer used
        
        # Check if this is an Ollama model
        self.is_ollama = model_name.startswith("ollama:")
        
        if self.is_ollama:
            # Extract the actual model name from the prefix
            ollama_model_name = model_name.replace("ollama:", "")
            
            # Load Ollama model
            print("\nLoading Ollama model...")
            print(f"Model: {ollama_model_name}")
            print("Note: Make sure Ollama is running on your system.")
            
            # Initialize Ollama model handler
            self.ollama_handler = OllamaModelHandler(ollama_model_name)
            
            # Create pipeline-like interface
            self.pipeline = self.ollama_handler
            
        else:
            # Load HuggingFace token from config
            try:
                with open('config.yaml', 'r') as f:
                    config = yaml.safe_load(f)
                token = config.get('HUGGING_FACE_HUB_TOKEN')
                if not token:
                    raise ValueError("HUGGING_FACE_HUB_TOKEN not found in config.yaml")
            except Exception as e:
                raise Exception(f"Failed to load HuggingFace token from config.yaml: {str(e)}")
            
            # Load model and tokenizer
            print("\nLoading model and tokenizer...")
            print(f"Model: {model_name}")
            if quantization:
                print(f"Quantization: {quantization}")
            print("Note: Initial loading and inference can take 1-5 minutes depending on your hardware.")
            print("Subsequent queries will be faster but may still take 30-60 seconds per response.")
            
            # Check if CUDA is available and set appropriate dtype
            if torch.cuda.is_available():
                print("CUDA is available. Using GPU acceleration.")
                dtype = torch.float16
            else:
                print("CUDA is not available. Using CPU only (this will be slow).")
                dtype = torch.float32
            
            # Set up model loading parameters
            model_kwargs = {
                "torch_dtype": dtype,
                "device_map": "auto",
                "token": token,
                "low_cpu_mem_usage": True,
                "offload_folder": "offload"
            }
            
            # Apply quantization if specified
            if quantization == '4bit':
                try:
                    from transformers import BitsAndBytesConfig
                    quantization_config = BitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_compute_dtype=torch.float16,
                        bnb_4bit_use_double_quant=True,
                        bnb_4bit_quant_type="nf4"
                    )
                    model_kwargs["quantization_config"] = quantization_config
                    print("Using 4-bit quantization with bitsandbytes")
                except ImportError:
                    print("Warning: bitsandbytes not installed. Falling back to standard loading.")
                    print("To use 4-bit quantization, install bitsandbytes: pip install bitsandbytes")
            elif quantization == '8bit':
                try:
                    from transformers import BitsAndBytesConfig
                    quantization_config = BitsAndBytesConfig(load_in_8bit=True)
                    model_kwargs["quantization_config"] = quantization_config
                    print("Using 8-bit quantization with bitsandbytes")
                except ImportError:
                    print("Warning: bitsandbytes not installed. Falling back to standard loading.")
                    print("To use 8-bit quantization, install bitsandbytes: pip install bitsandbytes")
            
            # Load model with appropriate settings
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                **model_kwargs
            )
            self.tokenizer = AutoTokenizer.from_pretrained(model_name, token=token)
            
            # Create text generation pipeline with optimized settings
            self.pipeline = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                max_new_tokens=512,
                do_sample=True,
                temperature=0.1,
                top_p=0.95,
                device_map="auto"
            )
            print("✓ Model loaded successfully")
        
        # Create LLM wrapper
        self.llm = LocalLLM(self.pipeline)
        
        # Initialize specialized agents if CoT is enabled
        self.agents = create_agents(self.llm, self.vector_store) if use_cot else None
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """Process a user query using the agentic RAG pipeline"""
        logger.info(f"Processing query with collection: {self.collection}")
        
        # Process based on collection type and CoT setting
        if self.collection == "General Knowledge":
            # For General Knowledge, directly use general response
            if self.use_cot:
                return self._process_query_with_cot(query)
            else:
                return self._generate_general_response(query)
        else:
            # For PDF, Repository, or Web collections, use context-based processing
            if self.use_cot:
                return self._process_query_with_cot(query)
            else:
                return self._process_query_standard(query)
    
    def _process_query_with_cot(self, query: str) -> Dict[str, Any]:
        """Process query using Chain of Thought reasoning"""
        try:
            # Get context based on collection type
            if self.collection == "PDF Collection":
                db_type = "Oracle DB" if self.use_oracle_db else "ChromaDB"
                print(f"🔄 Using {db_type} for retrieving PDF Collection context")
                context = self.vector_store.query_pdf_collection(query)
            elif self.collection == "Repository Collection":
                db_type = "Oracle DB" if self.use_oracle_db else "ChromaDB"
                print(f"🔄 Using {db_type} for retrieving Repository Collection context")
                context = self.vector_store.query_repo_collection(query)
            elif self.collection == "Web Knowledge Base":
                db_type = "Oracle DB" if self.use_oracle_db else "ChromaDB"
                print(f"🔄 Using {db_type} for retrieving Web Knowledge Base context")
                context = self.vector_store.query_web_collection(query)
            else:
                context = []
            
            # Log number of chunks retrieved
            logger.info(f"Retrieved {len(context)} chunks from {self.collection}")
            
            # Create agents if not already created
            if not self.agents:
                self.agents = create_agents(self.llm, self.vector_store)
            
            # Get planning step
            try:
                planning_result = self.agents["planner"].plan(query, context)
                logger.info("Planning step completed")
            except Exception as e:
                logger.error(f"Error in planning step: {str(e)}")
                logger.info("Falling back to general response")
                return self._generate_general_response(query)
            
            # Get research step
            research_results = []
            if self.agents.get("researcher") is not None and context:
                for step in planning_result.split("\n"):
                    if not step.strip():
                        continue
                    try:
                        step_research = self.agents["researcher"].research(query, step)
                        # Extract findings from research result
                        findings = step_research.get("findings", []) if isinstance(step_research, dict) else []
                        research_results.append({"step": step, "findings": findings})
                        
                        # Log which sources were used for this step
                        try:
                            source_indices = [context.index(finding) + 1 for finding in findings if finding in context]
                            logger.info(f"Research for step: {step}\nUsing sources: {source_indices}")
                        except ValueError as ve:
                            logger.warning(f"Could not find some findings in initial context: {str(ve)}")
                    except Exception as e:
                        logger.error(f"Error during research for step '{step}': {str(e)}")
                        research_results.append({"step": step, "findings": []})
            else:
                # If no researcher or no context, use the steps directly
                research_results = [{"step": step, "findings": []} for step in planning_result.split("\n") if step.strip()]
                logger.info("No research performed (no researcher agent or no context available)")
            
            # Get reasoning step
            reasoning_steps = []
            if not self.agents.get("reasoner"):
                logger.warning("No reasoner agent available, using direct response")
                return self._generate_general_response(query)
            
            for result in research_results:
                try:
                    step_reasoning = self.agents["reasoner"].reason(
                        query,
                        result["step"],
                        result["findings"] if result["findings"] else [{"content": "Using general knowledge", "metadata": {"source": "General Knowledge"}}]
                    )
                    reasoning_steps.append(step_reasoning)
                    logger.info(f"Reasoning for step: {result['step']}\n{step_reasoning}")
                except Exception as e:
                    logger.error(f"Error in reasoning for step '{result['step']}': {str(e)}")
                    reasoning_steps.append(f"Error in reasoning for this step: {str(e)}")
            
            # Get synthesis step
            if not self.agents.get("synthesizer"):
                logger.warning("No synthesizer agent available, using direct response")
                return self._generate_general_response(query)
            
            try:
                synthesis_result = self.agents["synthesizer"].synthesize(query, reasoning_steps)
                logger.info("Synthesis step completed")
            except Exception as e:
                logger.error(f"Error in synthesis step: {str(e)}")
                logger.info("Falling back to general response")
                return self._generate_general_response(query)
            
            return {
                "answer": synthesis_result["answer"],
                "reasoning_steps": reasoning_steps,
                "context": context
            }
            
        except Exception as e:
            logger.error(f"Error in CoT processing: {str(e)}")
            raise
    
    def _process_query_standard(self, query: str) -> Dict[str, Any]:
        """Process query using standard RAG approach"""
        try:
            # Get context based on collection type
            if self.collection == "PDF Collection":
                db_type = "Oracle DB" if self.use_oracle_db else "ChromaDB"
                print(f"🔄 Using {db_type} for retrieving PDF Collection context")
                context = self.vector_store.query_pdf_collection(query)
            elif self.collection == "Repository Collection":
                db_type = "Oracle DB" if self.use_oracle_db else "ChromaDB"
                print(f"🔄 Using {db_type} for retrieving Repository Collection context")
                context = self.vector_store.query_repo_collection(query)
            elif self.collection == "Web Knowledge Base":
                db_type = "Oracle DB" if self.use_oracle_db else "ChromaDB"
                print(f"🔄 Using {db_type} for retrieving Web Knowledge Base context")
                context = self.vector_store.query_web_collection(query)
            else:
                context = []
            
            # Log number of chunks retrieved
            logger.info(f"Retrieved {len(context)} chunks from {self.collection}")
            
            # Generate response using context
            response = self._generate_response(query, context)
            return response
            
        except Exception as e:
            logger.error(f"Error in standard processing: {str(e)}")
            raise
    
    def _generate_text(self, prompt: str, max_length: int = 512) -> str:
        """Generate text using the local model"""
        # Log start time for performance monitoring
        start_time = time.time()
        
        result = self.pipeline(
            prompt,
            max_new_tokens=max_length,
            do_sample=True,
            temperature=0.1,
            top_p=0.95,
            return_full_text=False
        )[0]["generated_text"]
        
        # Log completion time
        elapsed_time = time.time() - start_time
        logger.info(f"Text generation completed in {elapsed_time:.2f} seconds")
        
        return result.strip()
    
    def _generate_response(self, query: str, context: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a response using the retrieved context"""
        context_str = "\n\n".join([f"Context {i+1}:\n{item['content']}" 
                                  for i, item in enumerate(context)])
        
        template = """Answer the following query using the provided context. 
Respond as if you are knowledgeable about the topic and incorporate the context naturally.
Do not mention limitations in the context or that you couldn't find specific information.

Context:
{context}

Query: {query}

Answer:"""
        
        prompt = template.format(context=context_str, query=query)
        response_text = self._generate_text(prompt)
        
        # Add sources to response if available
        sources = {}
        if context:
            # Group sources by document
            for item in context:
                # Handle metadata which could be a string (from Oracle DB) or a dict (from ChromaDB)
                metadata = item['metadata']
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except json.JSONDecodeError:
                        metadata = {"source": "Unknown"}
                
                source = metadata.get('source', 'Unknown')
                if source not in sources:
                    sources[source] = set()
                
                # Add page number if available
                if 'page' in metadata:
                    sources[source].add(str(metadata['page']))
                # Add file path if available for code
                if 'file_path' in metadata:
                    sources[source] = metadata['file_path']
            
            # Print concise source information
            print("\nSources detected:")
            # Print a single line for each source without additional details
            for source in sources:
                print(f"- {source}")
        
        return {
            "answer": response_text,
            "context": context,
            "sources": sources
        }

    def _generate_general_response(self, query: str) -> Dict[str, Any]:
        """Generate a response using general knowledge when no context is available"""
        template = """You are a helpful AI assistant. Answer the following query using your general knowledge.

Query: {query}

Answer:"""
        
        prompt = template.format(query=query)
        response = self._generate_text(prompt)
        
        return {
            "answer": response,
            "context": []
        }

def main():
    parser = argparse.ArgumentParser(description="Query documents using local LLM")
    parser.add_argument("--query", required=True, help="Query to search for")
    parser.add_argument("--embeddings", default="oracle", choices=["oracle", "chromadb"], help="Embeddings backend to use")
    parser.add_argument("--model", default="ollama:qwen2", help="Model to use (default: ollama:qwen2)")
    parser.add_argument("--collection", help="Collection to search (PDF, Repository, General Knowledge)")
    parser.add_argument("--use-cot", action="store_true", help="Use Chain of Thought reasoning")
    parser.add_argument("--store-path", default="embeddings", help="Path to ChromaDB store")
    parser.add_argument("--skip-analysis", action="store_true", help="Skip query analysis (not recommended)")
    parser.add_argument("--verbose", action="store_true", help="Show full content of sources")
    parser.add_argument("--quiet", action="store_true", help="Disable verbose logging")
    parser.add_argument("--quantization", choices=["4bit", "8bit"], help="Quantization method (4bit or 8bit)")
        
    args = parser.parse_args()
    
    # Set logging level based on quiet flag
    if args.quiet:
        logger.setLevel(logging.WARNING)
    else:
        logger.setLevel(logging.INFO)
    
    print("\nInitializing RAG agent...")
    print("=" * 50)
    
    try:
        # Determine which vector store to use based on args.embeddings
        if args.embeddings == "oracle" and ORACLE_DB_AVAILABLE:
            try:
                logger.info("Initializing Oracle DB vector store")
                store = OraDBVectorStore()
                print("✓ Using Oracle DB for vector storage")
            except Exception as e:
                logger.warning(f"Failed to initialize Oracle DB: {str(e)}")
                logger.info(f"Falling back to ChromaDB from: {args.store_path}")
                store = VectorStore(persist_directory=args.store_path)
                print("⚠ Oracle DB initialization failed, using ChromaDB instead")
        else:
            if args.embeddings == "oracle" and not ORACLE_DB_AVAILABLE:
                logger.warning("Oracle DB support not available")
                print("⚠ Oracle DB support not available (missing dependencies)")
                
            logger.info(f"Initializing ChromaDB vector store from: {args.store_path}")
            store = VectorStore(persist_directory=args.store_path)
            print("✓ Using ChromaDB for vector storage")
        
        logger.info("Initializing local RAG agent...")
        # Set use_oracle_db based on the actual store type
        use_oracle_db = args.embeddings == "oracle" and isinstance(store, OraDBVectorStore)
        
        agent = LocalRAGAgent(
            store, 
            model_name=args.model, 
            use_cot=args.use_cot, 
            collection=args.collection,
            skip_analysis=args.skip_analysis,
            use_oracle_db=use_oracle_db
        )
        
        print(f"\nProcessing query: {args.query}")
        print("=" * 50)
        
        response = agent.process_query(args.query)
        
        print("\nResponse:")
        print("-" * 50)
        print(response["answer"])
        
        if response.get("reasoning_steps"):
            print("\nReasoning Steps:")
            print("-" * 50)
            for i, step in enumerate(response["reasoning_steps"]):
                print(f"\nStep {i+1}:")
                print(step)
        
        if response.get("context"):
            print("\nSources used:")
            print("-" * 50)
            
            # Print concise list of sources
            for i, ctx in enumerate(response["context"]):
                source = ctx["metadata"].get("source", "Unknown")
                if "page_numbers" in ctx["metadata"]:
                    pages = ctx["metadata"].get("page_numbers", [])
                    print(f"[{i+1}] {source} (pages: {pages})")
                else:
                    file_path = ctx["metadata"].get("file_path", "Unknown")
                    print(f"[{i+1}] {source} (file: {file_path})")
                
                # Only print content if verbose flag is set
                if args.verbose:
                    content_preview = ctx["content"][:300] + "..." if len(ctx["content"]) > 300 else ctx["content"]
                    print(f"    Content: {content_preview}\n")
    
    except Exception as e:
        logger.error(f"Error during execution: {str(e)}", exc_info=True)
        print(f"\n✗ Error: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main() 