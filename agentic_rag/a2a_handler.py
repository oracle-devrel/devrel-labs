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
            "agent.card": self.handle_agent_card,
            "task.create": self.handle_task_create,
            "task.status": self.handle_task_status,
            "task.cancel": self.handle_task_cancel,
            "health.check": self.handle_health_check,
        }
    
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
        
        # Process query using RAG agent
        response = self.rag_agent.process_query(query_params.query)
        
        return {
            "answer": response.get("answer", ""),
            "context": response.get("context", []),
            "sources": response.get("sources", {}),
            "reasoning_steps": response.get("reasoning_steps", []),
            "collection_used": query_params.collection or "auto"
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
        discover_params = AgentDiscoverParams(**params)
        
        if discover_params.agent_id:
            # Return specific agent
            agent = self.agent_registry.get_agent(discover_params.agent_id)
            if agent:
                return {"agents": [agent]}
            else:
                return {"agents": []}
        else:
            # Return agents with specific capability
            agents = self.agent_registry.discover_agents(discover_params.capability)
            return {"agents": agents}
    
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
