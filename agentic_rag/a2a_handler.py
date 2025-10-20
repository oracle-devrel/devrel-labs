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
    
    def _get_specialized_agent(self, agent_id: str):
        """Get or create a specialized agent instance"""
        if agent_id in self._specialized_agents:
            return self._specialized_agents[agent_id]
        
        # Import agent factory
        from agents.agent_factory import create_agents
        from langchain_openai import ChatOpenAI
        import os
        
        # Create LLM (using OpenAI for now, can be configured)
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            # Try Ollama as fallback
            try:
                from langchain_community.llms import Ollama
                llm = Ollama(model="qwq")
                logger.info("Using Ollama qwq for specialized agents")
            except Exception as e:
                logger.error(f"Could not initialize LLM for specialized agents: {str(e)}")
                raise ValueError("No LLM available for specialized agents")
        else:
            llm = ChatOpenAI(model="gpt-4", temperature=0.7, api_key=openai_key)
            logger.info("Using OpenAI GPT-4 for specialized agents")
        
        # Create all agents
        agents = create_agents(llm, self.vector_store)
        
        # Map agent_id to agent type
        agent_map = {
            "planner_agent_v1": agents["planner"],
            "researcher_agent_v1": agents["researcher"],
            "reasoner_agent_v1": agents["reasoner"],
            "synthesizer_agent_v1": agents["synthesizer"]
        }
        
        if agent_id not in agent_map:
            raise ValueError(f"Unknown agent ID: {agent_id}")
        
        # Cache the agent
        self._specialized_agents[agent_id] = agent_map[agent_id]
        logger.info(f"Created and cached specialized agent: {agent_id}")
        
        return agent_map[agent_id]
    
    async def handle_agent_query(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agent query requests - routes to specialized agents"""
        try:
            # Extract agent_id from params
            agent_id = params.get("agent_id")
            if not agent_id:
                return {
                    "error": "agent_id is required",
                    "message": "Must specify which agent to query"
                }
            
            # Get the specialized agent
            agent = self._get_specialized_agent(agent_id)
            
            # Extract query parameters
            query = params.get("query")
            step = params.get("step")
            context = params.get("context", [])
            reasoning_steps = params.get("reasoning_steps", [])
            
            # Route to appropriate agent method based on agent_id
            if agent_id == "planner_agent_v1":
                # Planner: Break down the query into steps
                plan = agent.plan(query, context)
                return {
                    "plan": plan,
                    "steps": plan.split("\n") if plan else [],
                    "agent_id": agent_id
                }
            
            elif agent_id == "researcher_agent_v1":
                # Researcher: Gather information for a specific step
                if not step:
                    return {"error": "step is required for researcher agent"}
                findings = agent.research(query, step)
                return {
                    "findings": findings,
                    "summary": findings[0]["content"] if findings else "",
                    "agent_id": agent_id
                }
            
            elif agent_id == "reasoner_agent_v1":
                # Reasoner: Apply logical reasoning to the step
                if not step:
                    return {"error": "step is required for reasoner agent"}
                conclusion = agent.reason(query, step, context)
                return {
                    "conclusion": conclusion,
                    "reasoning": conclusion,
                    "agent_id": agent_id
                }
            
            elif agent_id == "synthesizer_agent_v1":
                # Synthesizer: Combine all reasoning steps into final answer
                if not reasoning_steps:
                    return {"error": "reasoning_steps is required for synthesizer agent"}
                answer = agent.synthesize(query, reasoning_steps)
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
