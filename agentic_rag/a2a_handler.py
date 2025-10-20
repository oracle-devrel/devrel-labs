"""
A2A Protocol Handler

This module implements the core A2A (Agent2Agent) protocol handler that processes
JSON-RPC 2.0 requests and routes them to appropriate methods.
"""

import asyncio
import logging
import yaml
from typing import Dict, Any, Optional
from a2a_models import (
    A2ARequest, A2AResponse, A2AError, TaskInfo, TaskStatus,
    DocumentQueryParams, DocumentUploadParams, TaskCreateParams,
    TaskStatusParams, AgentDiscoverParams, AgentCard, AgentCapability, AgentEndpoint
)
from task_manager import TaskManager
from agent_registry import AgentRegistry
from specialized_agent_cards import get_all_specialized_agent_cards, get_agent_card_by_id

logger = logging.getLogger(__name__)


class A2AHandler:
    """Handler for A2A protocol requests"""
    
    def __init__(self, rag_agent, vector_store=None):
        """Initialize A2A handler with RAG agent and dependencies"""
        self.rag_agent = rag_agent
        self.vector_store = vector_store
        self.task_manager = TaskManager()
        self.agent_registry = AgentRegistry()
        
        # Load agent endpoint configuration
        self.agent_endpoints = self._load_agent_endpoints()
        
        # Initialize specialized agents (lazy loading)
        self._specialized_agents = {}
        
        # Register available methods
        self.methods = {
            "document.query": self.handle_document_query,
            "document.upload": self.handle_document_upload,
            "agent.discover": self.handle_agent_discover,
            "agent.register": self.handle_agent_register,
            "agent.card": self.handle_agent_card,
            "agent.query": self.handle_agent_query,
            "task.create": self.handle_task_create,
            "task.status": self.handle_task_status,
            "task.cancel": self.handle_task_cancel,
            "health.check": self.handle_health_check,
        }
        
        # Initialize registration flag
        self._self_registered = False
        self._specialized_agents_registered = False
    
    def _load_agent_endpoints(self) -> Dict[str, str]:
        """Load agent endpoint URLs from config"""
        try:
            with open('config.yaml', 'r') as f:
                config = yaml.safe_load(f)
                endpoints = config.get('AGENT_ENDPOINTS', {})
                logger.info(f"Loaded agent endpoints: {endpoints}")
                return endpoints
        except Exception as e:
            logger.warning(f"Could not load agent endpoints from config: {str(e)}")
            # Return default localhost endpoints
            return {
                "planner_url": "http://localhost:8000",
                "researcher_url": "http://localhost:8000",
                "reasoner_url": "http://localhost:8000",
                "synthesizer_url": "http://localhost:8000"
            }
    
    def _load_specialized_agent_model(self) -> str:
        """Load specialized agent model from config"""
        try:
            with open('config.yaml', 'r') as f:
                config = yaml.safe_load(f)
                model = config.get('SPECIALIZED_AGENT_MODEL', 'deepseek-r1')
                logger.info(f"Loaded specialized agent model: {model}")
                return model
        except Exception as e:
            logger.warning(f"Could not load model from config: {str(e)}")
            return "deepseek-r1"  # Default model
    
    def _register_self(self):
        """Register this agent in the agent registry"""
        try:
            logger.info("Starting agent self-registration...")
            from agent_card import get_agent_card
            agent_card_data = get_agent_card()
            logger.info(f"Retrieved agent card data: {agent_card_data.get('agent_id', 'unknown')}")
            
            # Convert the agent card data to AgentCard object
            from a2a_models import AgentCard, AgentCapability, AgentEndpoint
            
            # Extract capabilities
            capabilities = []
            for cap_data in agent_card_data.get("capabilities", []):
                capability = AgentCapability(
                    name=cap_data["name"],
                    description=cap_data["description"],
                    input_schema=cap_data.get("input_schema", {}),
                    output_schema=cap_data.get("output_schema", {})
                )
                capabilities.append(capability)
            
            logger.info(f"Created {len(capabilities)} capabilities")
            
            # Create endpoints
            endpoints_data = agent_card_data.get("endpoints", {})
            endpoints = AgentEndpoint(
                base_url=endpoints_data.get("base_url", "http://localhost:8000"),
                authentication=endpoints_data.get("authentication", {})
            )
            
            logger.info(f"Created endpoints: {endpoints.base_url}")
            
            # Create agent card
            agent_card = AgentCard(
                agent_id=agent_card_data["agent_id"],
                name=agent_card_data["name"],
                version=agent_card_data["version"],
                description=agent_card_data["description"],
                capabilities=capabilities,
                endpoints=endpoints,
                metadata=agent_card_data.get("metadata", {})
            )
            
            logger.info(f"Created agent card for: {agent_card.agent_id}")
            
            # Register the agent
            success = self.agent_registry.register_agent(agent_card)
            if success:
                logger.info(f"Successfully registered self as agent: {agent_card.agent_id}")
                logger.info(f"Registry now has {len(self.agent_registry.registered_agents)} agents")
                logger.info(f"Available capabilities: {list(self.agent_registry.capability_index.keys())}")
            else:
                logger.error("Failed to register agent in registry")
            
        except Exception as e:
            logger.error(f"Failed to register self as agent: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    def _register_specialized_agents(self):
        """Register all specialized Chain of Thought agents"""
        try:
            logger.info("Starting specialized agents registration...")
            
            # Get all specialized agent cards with configured URLs
            specialized_cards = get_all_specialized_agent_cards(self.agent_endpoints)
            
            # Register each specialized agent
            for agent_id, card_data in specialized_cards.items():
                try:
                    # Convert to AgentCard object
                    capabilities = []
                    for cap_data in card_data.get("capabilities", []):
                        capability = AgentCapability(
                            name=cap_data["name"],
                            description=cap_data["description"],
                            input_schema=cap_data.get("input_schema", {}),
                            output_schema=cap_data.get("output_schema", {})
                        )
                        capabilities.append(capability)
                    
                    endpoints_data = card_data.get("endpoints", {})
                    endpoints = AgentEndpoint(
                        base_url=endpoints_data.get("base_url", "http://localhost:8000"),
                        authentication=endpoints_data.get("authentication", {})
                    )
                    
                    agent_card = AgentCard(
                        agent_id=card_data["agent_id"],
                        name=card_data["name"],
                        version=card_data["version"],
                        description=card_data["description"],
                        capabilities=capabilities,
                        endpoints=endpoints,
                        metadata=card_data.get("metadata", {})
                    )
                    
                    success = self.agent_registry.register_agent(agent_card)
                    if success:
                        logger.info(f"Successfully registered specialized agent: {agent_id}")
                    else:
                        logger.error(f"Failed to register specialized agent: {agent_id}")
                        
                except Exception as e:
                    logger.error(f"Error registering specialized agent {agent_id}: {str(e)}")
            
            logger.info(f"Specialized agent registration complete. Registry has {len(self.agent_registry.registered_agents)} total agents")
            logger.info(f"Available capabilities: {list(self.agent_registry.capability_index.keys())}")
            
        except Exception as e:
            logger.error(f"Failed to register specialized agents: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    async def handle_request(self, request: A2ARequest) -> A2AResponse:
        """Handle incoming A2A request"""
        logger.info(f"Handling A2A request: {request.method}")
        
        if request.method not in self.methods:
            return A2AResponse(
                error=A2AError(
                    code=-32601,
                    message="Method not found"
                ).model_dump(),
                id=request.id
            )
        
        try:
            result = await self.methods[request.method](request.params)
            return A2AResponse(result=result, id=request.id)
        except Exception as e:
            logger.error(f"Error handling request {request.method}: {str(e)}")
            return A2AResponse(
                error=A2AError(
                    code=-32603,
                    message=f"Internal error: {str(e)}"
                ).model_dump(),
                id=request.id
            )
    
    async def handle_document_query(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle document query requests"""
        query_params = DocumentQueryParams(**params)
        
        # Map A2A collection names to RAG agent collection names
        collection_mapping = {
            "PDF": "PDF Collection",
            "Repository": "Repository Collection", 
            "Web": "Web Knowledge Base",
            "General": "General Knowledge"
        }
        rag_collection = collection_mapping.get(query_params.collection, "General Knowledge")
        
        # Set collection on RAG agent if it supports it
        if hasattr(self.rag_agent, 'collection'):
            self.rag_agent.collection = rag_collection
        
        # Process query using RAG agent
        response = self.rag_agent.process_query(query_params.query)
        
        return {
            "answer": response.get("answer", ""),
            "context": response.get("context", []),
            "sources": response.get("sources", {}),
            "reasoning_steps": response.get("reasoning_steps", []),
            "collection_used": query_params.collection or "General"
        }
    
    async def handle_document_upload(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle document upload requests"""
        upload_params = DocumentUploadParams(**params)
        
        # Process document based on type
        if upload_params.document_type == "pdf":
            # For PDF, we would need to implement PDF processing
            # This is a placeholder for now
            return {
                "status": "success",
                "message": "PDF processing not implemented in A2A handler",
                "document_type": upload_params.document_type
            }
        elif upload_params.document_type == "web":
            # For web content, we would process the content
            return {
                "status": "success",
                "message": "Web content processing not implemented in A2A handler",
                "document_type": upload_params.document_type
            }
        else:
            return {
                "status": "error",
                "message": f"Unsupported document type: {upload_params.document_type}"
            }
    
    def _call_ollama_api(self, model: str, prompt: str, system_prompt: str = None) -> str:
        """Call Ollama API directly for inference"""
        import requests
        
        url = "http://127.0.0.1:11434/api/generate"
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_predict": 512
            }
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        try:
            response = requests.post(url, json=payload, timeout=120)
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
        except Exception as e:
            logger.error(f"Error calling Ollama API: {str(e)}")
            raise
    
    def _get_specialized_agent_card(self, agent_id: str) -> dict:
        """Get the agent card for a specialized agent"""
        from specialized_agent_cards import get_agent_card_by_id
        return get_agent_card_by_id(agent_id, self.agent_endpoints)
    
    async def handle_agent_query(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agent query requests - routes to specialized agents using Ollama API"""
        try:
            # Extract agent_id from params
            agent_id = params.get("agent_id")
            if not agent_id:
                return {
                    "error": "agent_id is required",
                    "message": "Must specify which agent to query"
                }
            
            # Get the agent card to extract personality and role
            agent_card = self._get_specialized_agent_card(agent_id)
            if not agent_card:
                return {
                    "error": f"Agent card not found for {agent_id}",
                    "message": "Agent not registered"
                }
            
            # Extract agent metadata
            metadata = agent_card.get("metadata", {})
            personality = metadata.get("personality", "")
            role = metadata.get("role", "")
            expertise = metadata.get("expertise", [])
            
            # Extract query parameters
            query = params.get("query")
            step = params.get("step")
            context = params.get("context", [])
            reasoning_steps = params.get("reasoning_steps", [])
            
            # Get model from config
            model = self._load_specialized_agent_model()
            
            # Route to appropriate agent method based on agent_id
            if agent_id == "planner_agent_v1":
                # Planner: Break down the query into steps
                system_prompt = f"""You are a {role} with expertise in {', '.join(expertise)}.
Your personality: {personality}

Your task is to break down complex problems into 3-4 clear, manageable steps for systematic problem-solving.
Be strategic, analytical, and methodical in your planning."""
                
                user_prompt = f"""Query: {query}

Break down this query into 3-4 clear, actionable steps. Format your response as:

Step 1: [First step description]
Step 2: [Second step description]
Step 3: [Third step description]
Step 4: [Fourth step description] (if needed)

Steps:"""
                
                logger.info(f"Calling Planner with model: {model}")
                plan = self._call_ollama_api(model, user_prompt, system_prompt)
                logger.info(f"Planner response: {plan[:200]}...")
                
                # Extract steps from plan
                steps = []
                for line in plan.split("\n"):
                    line = line.strip()
                    if line and (line.startswith("Step") or line.startswith("-") or (len(line) > 10 and not line.startswith("Your"))):
                        # Clean up the step
                        clean_step = line.replace("Step 1:", "").replace("Step 2:", "").replace("Step 3:", "").replace("Step 4:", "").replace("-", "").strip()
                        if clean_step and len(clean_step) > 10:
                            steps.append(clean_step)
                
                return {
                    "plan": plan,
                    "steps": steps[:4],  # Limit to 4 steps
                    "agent_id": agent_id
                }
            
            elif agent_id == "researcher_agent_v1":
                # Researcher: Gather information for a specific step
                if not step:
                    return {"error": "step is required for researcher agent"}
                
                system_prompt = f"""You are a {role} with expertise in {', '.join(expertise)}.
Your personality: {personality}

Your task is to gather and analyze relevant information from the provided context, extracting key findings for each research step."""
                
                # Query vector store for relevant information
                logger.info(f"Researching for step: {step}")
                pdf_results = self.vector_store.query_pdf_collection(query) if self.vector_store else []
                repo_results = self.vector_store.query_repo_collection(query) if self.vector_store else []
                all_results = pdf_results + repo_results
                
                context_str = "\n\n".join([f"Source {i+1}:\n{item['content']}" for i, item in enumerate(all_results[:3])])
                
                user_prompt = f"""Original Query: {query}
Research Step: {step}

Context from knowledge base:
{context_str if context_str else "No specific context found in knowledge base."}

Based on this context, extract and summarize key findings relevant to this research step. Be thorough and detail-oriented.

Key Findings:"""
                
                logger.info(f"Calling Researcher with model: {model}")
                summary = self._call_ollama_api(model, user_prompt, system_prompt)
                logger.info(f"Researcher response: {summary[:200]}...")
                
                findings = [{"content": summary, "metadata": {"source": "Research Summary"}}]
                findings.extend(all_results[:3])
                
                return {
                    "findings": findings,
                    "summary": summary,
                    "agent_id": agent_id
                }
            
            elif agent_id == "reasoner_agent_v1":
                # Reasoner: Apply logical reasoning to the step
                if not step:
                    return {"error": "step is required for reasoner agent"}
                
                system_prompt = f"""You are a {role} with expertise in {', '.join(expertise)}.
Your personality: {personality}

Your task is to apply logical reasoning and analysis to information, drawing clear conclusions for each step."""
                
                context_str = "\n\n".join([f"Context {i+1}:\n{item.get('content', str(item))}" for i, item in enumerate(context)])
                
                user_prompt = f"""Original Query: {query}
Reasoning Step: {step}

Research Findings:
{context_str}

Analyze this information and draw a clear, logical conclusion for this step. Be critical and analytical in your reasoning.

Conclusion:"""
                
                logger.info(f"Calling Reasoner with model: {model}")
                conclusion = self._call_ollama_api(model, user_prompt, system_prompt)
                logger.info(f"Reasoner response: {conclusion[:200]}...")
                
                return {
                    "conclusion": conclusion,
                    "reasoning": conclusion,
                    "agent_id": agent_id
                }
            
            elif agent_id == "synthesizer_agent_v1":
                # Synthesizer: Combine all reasoning steps into final answer
                if not reasoning_steps:
                    return {"error": "reasoning_steps is required for synthesizer agent"}
                
                system_prompt = f"""You are a {role} with expertise in {', '.join(expertise)}.
Your personality: {personality}

Your task is to combine multiple reasoning steps into a clear, comprehensive final answer."""
                
                steps_str = "\n\n".join([f"Step {i+1}:\n{step}" for i, step in enumerate(reasoning_steps)])
                
                user_prompt = f"""Original Query: {query}

Reasoning Steps:
{steps_str}

Combine these reasoning steps into a clear, comprehensive final answer. Be integrative and ensure the answer is coherent.

Final Answer:"""
                
                logger.info(f"Calling Synthesizer with model: {model}")
                answer = self._call_ollama_api(model, user_prompt, system_prompt)
                logger.info(f"Synthesizer response: {answer[:200]}...")
                
                return {
                    "answer": answer,
                    "summary": answer,
                    "agent_id": agent_id
                }
            
            else:
                return {
                    "error": f"Unknown agent ID: {agent_id}",
                    "message": "Agent not found or not supported"
                }
                
        except Exception as e:
            logger.error(f"Error in agent query: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "error": str(e),
                "message": "Failed to process agent query"
            }
    
    async def handle_agent_discover(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agent discovery requests"""
        try:
            # Ensure self is registered
            if not self._self_registered:
                logger.info("Self not registered yet, registering now...")
                self._register_self()
                self._self_registered = True
            
            # Ensure specialized agents are registered
            if not self._specialized_agents_registered:
                logger.info("Specialized agents not registered yet, registering now...")
                self._register_specialized_agents()
                self._specialized_agents_registered = True
            
            discover_params = AgentDiscoverParams(**params)
            logger.info(f"Agent discovery request: capability={discover_params.capability}, agent_id={discover_params.agent_id}")
            
            # Debug registry state
            logger.info(f"Registry has {len(self.agent_registry.registered_agents)} agents")
            logger.info(f"Available capabilities: {list(self.agent_registry.capability_index.keys())}")
            
            if discover_params.agent_id:
                # Return specific agent
                agent = self.agent_registry.get_agent(discover_params.agent_id)
                if agent:
                    logger.info(f"Found specific agent: {discover_params.agent_id}")
                    return {"agents": [agent.model_dump()]}
                else:
                    logger.info(f"Agent not found: {discover_params.agent_id}")
                    return {"agents": []}
            else:
                # Return agents with specific capability
                agents = self.agent_registry.discover_agents(discover_params.capability)
                logger.info(f"Found {len(agents)} agents with capability: {discover_params.capability}")
                
                # Convert AgentCard objects to dictionaries
                agents_data = []
                for agent in agents:
                    try:
                        agents_data.append(agent.model_dump())
                    except Exception as e:
                        logger.error(f"Error converting agent to dict: {str(e)}")
                        # Fallback to basic info
                        agents_data.append({
                            "agent_id": getattr(agent, 'agent_id', 'unknown'),
                            "name": getattr(agent, 'name', 'unknown'),
                            "version": getattr(agent, 'version', 'unknown'),
                            "description": getattr(agent, 'description', 'unknown')
                        })
                
                logger.info(f"Returning {len(agents_data)} agents")
                return {"agents": agents_data}
        except Exception as e:
            logger.error(f"Error in agent discovery: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {"agents": []}
    
    async def handle_agent_register(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agent registration requests"""
        try:
            logger.info("Handling agent registration request")
            
            # Extract agent card data from params
            agent_card_data = params.get("agent_card", {})
            if not agent_card_data:
                logger.error("No agent_card provided in registration request")
                return {
                    "success": False,
                    "message": "No agent_card provided",
                    "agent_id": None
                }
            
            # Convert to AgentCard object
            from a2a_models import AgentCard, AgentCapability, AgentEndpoint
            
            # Extract capabilities
            capabilities = []
            for cap_data in agent_card_data.get("capabilities", []):
                capability = AgentCapability(
                    name=cap_data["name"],
                    description=cap_data["description"],
                    input_schema=cap_data.get("input_schema", {}),
                    output_schema=cap_data.get("output_schema", {})
                )
                capabilities.append(capability)
            
            # Create endpoints
            endpoints_data = agent_card_data.get("endpoints", {})
            endpoints = AgentEndpoint(
                base_url=endpoints_data.get("base_url", "http://localhost:8000"),
                authentication=endpoints_data.get("authentication", {})
            )
            
            # Create agent card
            agent_card = AgentCard(
                agent_id=agent_card_data["agent_id"],
                name=agent_card_data["name"],
                version=agent_card_data["version"],
                description=agent_card_data["description"],
                capabilities=capabilities,
                endpoints=endpoints,
                metadata=agent_card_data.get("metadata", {})
            )
            
            # Register the agent
            success = self.agent_registry.register_agent(agent_card)
            
            if success:
                logger.info(f"Successfully registered agent: {agent_card.agent_id}")
                logger.info(f"Registry now has {len(self.agent_registry.registered_agents)} agents")
                logger.info(f"Available capabilities: {list(self.agent_registry.capability_index.keys())}")
                
                return {
                    "success": True,
                    "message": "Agent registered successfully",
                    "agent_id": agent_card.agent_id,
                    "capabilities": len(capabilities),
                    "registry_size": len(self.agent_registry.registered_agents)
                }
            else:
                logger.error(f"Failed to register agent: {agent_card.agent_id}")
                return {
                    "success": False,
                    "message": "Failed to register agent",
                    "agent_id": agent_card.agent_id
                }
                
        except Exception as e:
            logger.error(f"Error in agent registration: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "message": f"Registration error: {str(e)}",
                "agent_id": None
            }
    
    async def handle_agent_card(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agent card requests"""
        # Return the agent card for this agent
        from agent_card import get_agent_card
        return get_agent_card()
    
    async def handle_task_create(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle task creation requests"""
        task_params = TaskCreateParams(**params)
        
        task_id = await self.task_manager.create_task(
            task_type=task_params.task_type,
            params=task_params.params
        )
        
        return {
            "task_id": task_id,
            "status": "created",
            "message": "Task created successfully"
        }
    
    async def handle_task_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle task status requests"""
        status_params = TaskStatusParams(**params)
        
        task_info = self.task_manager.get_task_status(status_params.task_id)
        if not task_info:
            return {
                "error": "Task not found",
                "task_id": status_params.task_id
            }
        
        return task_info.model_dump()
    
    async def handle_task_cancel(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle task cancellation requests"""
        status_params = TaskStatusParams(**params)
        
        success = self.task_manager.cancel_task(status_params.task_id)
        return {
            "task_id": status_params.task_id,
            "cancelled": success,
            "message": "Task cancelled" if success else "Task not found or already completed"
        }
    
    async def handle_health_check(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle health check requests"""
        return {
            "status": "healthy",
            "timestamp": asyncio.get_event_loop().time(),
            "version": "1.0.0",
            "capabilities": list(self.methods.keys())
        }
