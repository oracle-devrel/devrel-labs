"""
A2A Protocol Handler

This module implements the core A2A (Agent2Agent) protocol handler that processes
JSON-RPC 2.0 requests and routes them to appropriate methods.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from a2a_models import (
    A2ARequest, A2AResponse, A2AError, TaskInfo, TaskStatus,
    DocumentQueryParams, DocumentUploadParams, TaskCreateParams,
    TaskStatusParams, AgentDiscoverParams
)
from task_manager import TaskManager
from agent_registry import AgentRegistry

logger = logging.getLogger(__name__)


class A2AHandler:
    """Handler for A2A protocol requests"""
    
    def __init__(self, rag_agent, vector_store=None):
        """Initialize A2A handler with RAG agent and dependencies"""
        self.rag_agent = rag_agent
        self.vector_store = vector_store
        self.task_manager = TaskManager()
        self.agent_registry = AgentRegistry()
        
        # Register available methods
        self.methods = {
            "document.query": self.handle_document_query,
            "document.upload": self.handle_document_upload,
            "agent.discover": self.handle_agent_discover,
            "agent.register": self.handle_agent_register,
            "agent.card": self.handle_agent_card,
            "task.create": self.handle_task_create,
            "task.status": self.handle_task_status,
            "task.cancel": self.handle_task_cancel,
            "health.check": self.handle_health_check,
        }
        
        # Initialize registration flag
        self._self_registered = False
    
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
    
    async def handle_agent_discover(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agent discovery requests"""
        try:
            # Ensure self is registered
            if not self._self_registered:
                logger.info("Self not registered yet, registering now...")
                self._register_self()
                self._self_registered = True
            
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
