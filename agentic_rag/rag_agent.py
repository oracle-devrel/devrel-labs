from typing import List, Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from store import VectorStore
from agents.agent_factory import create_agents
import os
import argparse
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RAGAgent:
    def __init__(self, vector_store: VectorStore, openai_api_key: str, use_cot: bool = False, collection: str = None, skip_analysis: bool = False):
        """Initialize RAG agent with vector store and LLM"""
        self.vector_store = vector_store
        self.use_cot = use_cot
        self.collection = collection
        # skip_analysis parameter kept for backward compatibility but no longer used
        self.llm = ChatOpenAI(
            model="gpt-4-turbo-preview",
            temperature=0,
            api_key=openai_api_key
        )
        
        # Initialize specialized agents
        self.agents = create_agents(self.llm, vector_store) if use_cot else None
    
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
            # For PDF or Repository collections, use context-based processing
            if self.use_cot:
                return self._process_query_with_cot(query)
            else:
                return self._process_query_standard(query)
    
    def _process_query_with_cot(self, query: str) -> Dict[str, Any]:
        """Process query using Chain of Thought reasoning with multiple agents"""
        logger.info("Processing query with Chain of Thought reasoning")
        
        # Get initial context based on selected collection
        initial_context = []
        if self.collection == "PDF Collection":
            logger.info(f"Retrieving context from PDF Collection for query: '{query}'")
            pdf_context = self.vector_store.query_pdf_collection(query)
            initial_context.extend(pdf_context)
            logger.info(f"Retrieved {len(pdf_context)} chunks from PDF Collection")
            # Log each chunk with citation number but not full content
            for i, chunk in enumerate(pdf_context):
                source = chunk["metadata"].get("source", "Unknown")
                pages = chunk["metadata"].get("page_numbers", [])
                logger.info(f"Source [{i+1}]: {source} (pages: {pages})")
                # Only log content preview at debug level
                content_preview = chunk["content"][:150] + "..." if len(chunk["content"]) > 150 else chunk["content"]
                logger.debug(f"Content preview for source [{i+1}]: {content_preview}")
        elif self.collection == "Repository Collection":
            logger.info(f"Retrieving context from Repository Collection for query: '{query}'")
            repo_context = self.vector_store.query_repo_collection(query)
            initial_context.extend(repo_context)
            logger.info(f"Retrieved {len(repo_context)} chunks from Repository Collection")
            # Log each chunk with citation number but not full content
            for i, chunk in enumerate(repo_context):
                source = chunk["metadata"].get("source", "Unknown")
                file_path = chunk["metadata"].get("file_path", "Unknown")
                logger.info(f"Source [{i+1}]: {source} (file: {file_path})")
                # Only log content preview at debug level
                content_preview = chunk["content"][:150] + "..." if len(chunk["content"]) > 150 else chunk["content"]
                logger.debug(f"Content preview for source [{i+1}]: {content_preview}")
        elif self.collection == "Web Knowledge Base":
            logger.info(f"Retrieving context from Web Knowledge Base for query: '{query}'")
            web_context = self.vector_store.query_web_collection(query)
            initial_context.extend(web_context)
            logger.info(f"Retrieved {len(web_context)} chunks from Web Knowledge Base")
            # Log each chunk with citation number but not full content
            for i, chunk in enumerate(web_context):
                source = chunk["metadata"].get("source", "Unknown")
                title = chunk["metadata"].get("title", "Unknown")
                logger.info(f"Source [{i+1}]: {source} (title: {title})")
                # Only log content preview at debug level
                content_preview = chunk["content"][:150] + "..." if len(chunk["content"]) > 150 else chunk["content"]
                logger.debug(f"Content preview for source [{i+1}]: {content_preview}")
        # For General Knowledge, no context is needed
        else:
            logger.info("Using General Knowledge collection, no context retrieval needed")
        
        try:
            # Step 1: Planning
            logger.info("Step 1: Planning")
            if not self.agents or "planner" not in self.agents:
                logger.warning("No planner agent available, using direct response")
                return self._generate_general_response(query)
            
            try:
                plan = self.agents["planner"].plan(query, initial_context)
                logger.info(f"Generated plan:\n{plan}")
            except Exception as e:
                logger.error(f"Error in planning step: {str(e)}")
                logger.info("Falling back to general response")
                return self._generate_general_response(query)
            
            # Step 2: Research each step (if researcher is available)
            logger.info("Step 2: Research")
            research_results = []
            if self.agents.get("researcher") is not None and initial_context:
                for step in plan.split("\n"):
                    if not step.strip():
                        continue
                    try:
                        step_research = self.agents["researcher"].research(query, step)
                        # Extract findings from research result
                        findings = step_research.get("findings", []) if isinstance(step_research, dict) else []
                        research_results.append({"step": step, "findings": findings})
                        
                        # Log which sources were used for this step
                        try:
                            source_indices = [initial_context.index(finding) + 1 for finding in findings if finding in initial_context]
                            logger.info(f"Research for step: {step}\nUsing sources: {source_indices}")
                        except ValueError as ve:
                            logger.warning(f"Could not find some findings in initial context: {str(ve)}")
                    except Exception as e:
                        logger.error(f"Error during research for step '{step}': {str(e)}")
                        research_results.append({"step": step, "findings": []})
            else:
                # If no researcher or no context, use the steps directly
                research_results = [{"step": step, "findings": []} for step in plan.split("\n") if step.strip()]
                logger.info("No research performed (no researcher agent or no context available)")
            
            # Step 3: Reasoning about each step
            logger.info("Step 3: Reasoning")
            if not self.agents.get("reasoner"):
                logger.warning("No reasoner agent available, using direct response")
                return self._generate_general_response(query)
            
            reasoning_steps = []
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
            
            # Step 4: Synthesize final answer
            logger.info("Step 4: Synthesis")
            if not self.agents.get("synthesizer"):
                logger.warning("No synthesizer agent available, using direct response")
                return self._generate_general_response(query)
            
            try:
                final_answer = self.agents["synthesizer"].synthesize(query, reasoning_steps)
                logger.info(f"Final synthesized answer:\n{final_answer}")
            except Exception as e:
                logger.error(f"Error in synthesis step: {str(e)}")
                logger.info("Falling back to general response")
                return self._generate_general_response(query)
            
            return {
                "answer": final_answer,
                "context": initial_context,
                "reasoning_steps": reasoning_steps
            }
        except Exception as e:
            logger.error(f"Error in CoT processing: {str(e)}", exc_info=True)
            logger.info("Falling back to general response")
            return self._generate_general_response(query)
    
    def _process_query_standard(self, query: str) -> Dict[str, Any]:
        """Process query using standard approach without Chain of Thought"""
        # Initialize context variables
        context = []
        
        # Get context based on selected collection
        if self.collection == "PDF Collection":
            logger.info(f"Retrieving context from PDF Collection for query: '{query}'")
            context = self.vector_store.query_pdf_collection(query)
            logger.info(f"Retrieved {len(context)} chunks from PDF Collection")
            # Log each chunk with citation number but not full content
            for i, chunk in enumerate(context):
                source = chunk["metadata"].get("source", "Unknown")
                pages = chunk["metadata"].get("page_numbers", [])
                logger.info(f"Source [{i+1}]: {source} (pages: {pages})")
                # Only log content preview at debug level
                content_preview = chunk["content"][:150] + "..." if len(chunk["content"]) > 150 else chunk["content"]
                logger.debug(f"Content preview for source [{i+1}]: {content_preview}")
        elif self.collection == "Repository Collection":
            logger.info(f"Retrieving context from Repository Collection for query: '{query}'")
            context = self.vector_store.query_repo_collection(query)
            logger.info(f"Retrieved {len(context)} chunks from Repository Collection")
            # Log each chunk with citation number but not full content
            for i, chunk in enumerate(context):
                source = chunk["metadata"].get("source", "Unknown")
                file_path = chunk["metadata"].get("file_path", "Unknown")
                logger.info(f"Source [{i+1}]: {source} (file: {file_path})")
                # Only log content preview at debug level
                content_preview = chunk["content"][:150] + "..." if len(chunk["content"]) > 150 else chunk["content"]
                logger.debug(f"Content preview for source [{i+1}]: {content_preview}")
        elif self.collection == "Web Knowledge Base":
            logger.info(f"Retrieving context from Web Knowledge Base for query: '{query}'")
            context = self.vector_store.query_web_collection(query)
            logger.info(f"Retrieved {len(context)} chunks from Web Knowledge Base")
            # Log each chunk with citation number but not full content
            for i, chunk in enumerate(context):
                source = chunk["metadata"].get("source", "Unknown")
                title = chunk["metadata"].get("title", "Unknown")
                logger.info(f"Source [{i+1}]: {source} (title: {title})")
                # Only log content preview at debug level
                content_preview = chunk["content"][:150] + "..." if len(chunk["content"]) > 150 else chunk["content"]
                logger.debug(f"Content preview for source [{i+1}]: {content_preview}")
        
        # Generate response using context if available, otherwise use general knowledge
        if context:
            logger.info(f"Generating response using {len(context)} context chunks")
            response = self._generate_response(query, context)
        else:
            logger.info("No context found, using general knowledge")
            response = self._generate_general_response(query)
        
        return response
    
    def _generate_response(self, query: str, context: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a response based on the query and context"""
        # Format context for the prompt
        formatted_context = "\n\n".join([f"Context {i+1}:\n{item['content']}" 
                                       for i, item in enumerate(context)])
        
        # Create the prompt
        system_prompt = """You are an AI assistant answering questions based on the provided context.
Answer the question based on the context provided. If the answer is not in the context, say "I don't have enough information to answer this question." Be concise and accurate."""
        
        # Create messages for the chat model
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context:\n{formatted_context}\n\nQuestion: {query}"}
        ]
        
        # Generate response
        response = self.llm.invoke(messages)
        
        # Add sources to response if available
        if context:
            # Group sources by document
            sources = {}
            for item in context:
                source = item['metadata'].get('source', 'Unknown')
                if source not in sources:
                    sources[source] = set()
                
                # Add page number if available
                if 'page' in item['metadata']:
                    sources[source].add(str(item['metadata']['page']))
                # Add file path if available for code
                if 'file_path' in item['metadata']:
                    sources[source] = item['metadata']['file_path']
            
            # Print concise source information
            print("\nSources detected:")
            for source, details in sources.items():
                if isinstance(details, set):  # PDF with pages
                    pages = ", ".join(sorted(details))
                    print(f"Document: {source} (pages: {pages})")
                else:  # Code with file path
                    print(f"Code file: {source}")
            
            response['sources'] = sources
        
        return {
            "answer": response.content,
            "context": context
        }

    def _generate_general_response(self, query: str) -> Dict[str, Any]:
        """Generate a response using general knowledge when no context is available"""
        template = """You are a helpful AI assistant. Answer the following query using your general knowledge.

Query: {query}

Answer:"""
        
        prompt = ChatPromptTemplate.from_template(template)
        messages = prompt.format_messages(query=query)
        response = self.llm.invoke(messages)
        
        return {
            "answer": response.content,
            "context": []
        }

def main():
    parser = argparse.ArgumentParser(description="Query documents using OpenAI GPT-4")
    parser.add_argument("--query", required=True, help="Query to process")
    parser.add_argument("--store-path", default="chroma_db", help="Path to the vector store")
    parser.add_argument("--use-cot", action="store_true", help="Enable Chain of Thought reasoning")
    parser.add_argument("--collection", choices=["PDF Collection", "Repository Collection", "General Knowledge"], 
                        help="Specify which collection to query")
    parser.add_argument("--skip-analysis", action="store_true", help="Skip query analysis step")
    parser.add_argument("--verbose", action="store_true", help="Show full content of sources")
    
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    if not os.getenv("OPENAI_API_KEY"):
        print("✗ Error: OPENAI_API_KEY not found in environment variables")
        print("Please create a .env file with your OpenAI API key")
        exit(1)
    
    print("\nInitializing RAG agent...")
    print("=" * 50)
    
    try:
        store = VectorStore(persist_directory=args.store_path)
        agent = RAGAgent(
            store, 
            openai_api_key=os.getenv("OPENAI_API_KEY"), 
            use_cot=args.use_cot, 
            collection=args.collection,
            skip_analysis=args.skip_analysis
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
        print(f"\n✗ Error: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main() 