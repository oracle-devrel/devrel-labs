"""
Test suite for A2A Protocol implementation

This module contains comprehensive tests for the A2A protocol functionality,
including unit tests for individual components and integration tests.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

# Import A2A components
from a2a_models import (
    A2ARequest, A2AResponse, A2AError, TaskStatus, TaskInfo,
    DocumentQueryParams, DocumentUploadParams, TaskCreateParams,
    TaskStatusParams, AgentDiscoverParams, AgentCard, AgentCapability
)
from a2a_handler import A2AHandler
from task_manager import TaskManager
from agent_registry import AgentRegistry
from agent_card import get_agent_card


class TestA2AModels:
    """Test A2A data models"""
    
    def test_a2a_request_creation(self):
        """Test A2A request model creation"""
        request = A2ARequest(
            method="document.query",
            params={"query": "test query"}
        )
        
        assert request.jsonrpc == "2.0"
        assert request.method == "document.query"
        assert request.params == {"query": "test query"}
        assert request.id is not None
    
    def test_a2a_response_creation(self):
        """Test A2A response model creation"""
        response = A2AResponse(
            result={"answer": "test answer"},
            id="test-id"
        )
        
        assert response.jsonrpc == "2.0"
        assert response.result == {"answer": "test answer"}
        assert response.error is None
        assert response.id == "test-id"
    
    def test_a2a_error_creation(self):
        """Test A2A error model creation"""
        error = A2AError(
            code=-32601,
            message="Method not found"
        )
        
        assert error.code == -32601
        assert error.message == "Method not found"
        assert error.data is None
    
    def test_document_query_params(self):
        """Test document query parameters"""
        params = DocumentQueryParams(
            query="test query",
            collection="PDF",
            use_cot=True,
            max_results=5
        )
        
        assert params.query == "test query"
        assert params.collection == "PDF"
        assert params.use_cot is True
        assert params.max_results == 5
    
    def test_task_info_creation(self):
        """Test task info model creation"""
        task_info = TaskInfo(
            task_id="test-task-id",
            task_type="document_processing",
            status=TaskStatus.PENDING,
            params={"document": "test.pdf"}
        )
        
        assert task_info.task_id == "test-task-id"
        assert task_info.task_type == "document_processing"
        assert task_info.status == TaskStatus.PENDING
        assert task_info.params == {"document": "test.pdf"}
        assert task_info.result is None
        assert task_info.error is None


class TestTaskManager:
    """Test task manager functionality"""
    
    @pytest.fixture
    def task_manager(self):
        """Create task manager instance for testing"""
        return TaskManager()
    
    @pytest.mark.asyncio
    async def test_create_task(self, task_manager):
        """Test task creation"""
        task_id = await task_manager.create_task(
            task_type="document_processing",
            params={"document": "test.pdf"}
        )
        
        assert task_id is not None
        assert task_id in task_manager.tasks
        
        task_info = task_manager.tasks[task_id]
        assert task_info.task_type == "document_processing"
        assert task_info.status == TaskStatus.PENDING
    
    @pytest.mark.asyncio
    async def test_task_execution(self, task_manager):
        """Test task execution"""
        task_id = await task_manager.create_task(
            task_type="document_processing",
            params={"chunk_count": 5}
        )
        
        # Wait for task to complete
        await asyncio.sleep(3)
        
        task_info = task_manager.get_task_status(task_id)
        assert task_info.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]
    
    def test_get_task_status(self, task_manager):
        """Test getting task status"""
        # Test with non-existent task
        task_info = task_manager.get_task_status("non-existent")
        assert task_info is None
    
    def test_cancel_task(self, task_manager):
        """Test task cancellation"""
        # Create a task
        task_id = "test-task-id"
        task_info = TaskInfo(
            task_id=task_id,
            task_type="test",
            status=TaskStatus.PENDING,
            params={}
        )
        task_manager.tasks[task_id] = task_info
        
        # Cancel the task
        success = task_manager.cancel_task(task_id)
        assert success is True
        
        # Check task status
        updated_task = task_manager.get_task_status(task_id)
        assert updated_task.status == TaskStatus.CANCELLED
    
    def test_list_tasks(self, task_manager):
        """Test listing tasks"""
        # Add some test tasks
        task1 = TaskInfo(
            task_id="task1",
            task_type="test1",
            status=TaskStatus.PENDING,
            params={}
        )
        task2 = TaskInfo(
            task_id="task2",
            task_type="test2",
            status=TaskStatus.COMPLETED,
            params={}
        )
        
        task_manager.tasks["task1"] = task1
        task_manager.tasks["task2"] = task2
        
        # Test listing all tasks
        all_tasks = task_manager.list_tasks()
        assert len(all_tasks) == 2
        
        # Test filtering by status
        pending_tasks = task_manager.list_tasks(TaskStatus.PENDING)
        assert len(pending_tasks) == 1
        assert "task1" in pending_tasks
        
        completed_tasks = task_manager.list_tasks(TaskStatus.COMPLETED)
        assert len(completed_tasks) == 1
        assert "task2" in completed_tasks


class TestAgentRegistry:
    """Test agent registry functionality"""
    
    @pytest.fixture
    def agent_registry(self):
        """Create agent registry instance for testing"""
        return AgentRegistry()
    
    @pytest.fixture
    def sample_agent_card(self):
        """Create sample agent card for testing"""
        capability = AgentCapability(
            name="test.capability",
            description="Test capability",
            input_schema={"type": "object"},
            output_schema={"type": "object"}
        )
        
        return AgentCard(
            agent_id="test-agent",
            name="Test Agent",
            version="1.0.0",
            description="Test agent for testing",
            capabilities=[capability],
            endpoints={"base_url": "http://test.example.com"}
        )
    
    def test_register_agent(self, agent_registry, sample_agent_card):
        """Test agent registration"""
        success = agent_registry.register_agent(sample_agent_card)
        assert success is True
        assert "test-agent" in agent_registry.registered_agents
    
    def test_unregister_agent(self, agent_registry, sample_agent_card):
        """Test agent unregistration"""
        # Register agent first
        agent_registry.register_agent(sample_agent_card)
        
        # Unregister agent
        success = agent_registry.unregister_agent("test-agent")
        assert success is True
        assert "test-agent" not in agent_registry.registered_agents
    
    def test_get_agent(self, agent_registry, sample_agent_card):
        """Test getting agent by ID"""
        # Register agent
        agent_registry.register_agent(sample_agent_card)
        
        # Get agent
        agent = agent_registry.get_agent("test-agent")
        assert agent is not None
        assert agent.agent_id == "test-agent"
    
    def test_discover_agents(self, agent_registry, sample_agent_card):
        """Test agent discovery"""
        # Register agent
        agent_registry.register_agent(sample_agent_card)
        
        # Discover agents by capability
        agents = agent_registry.discover_agents("test.capability")
        assert len(agents) == 1
        assert agents[0].agent_id == "test-agent"
        
        # Discover all agents
        all_agents = agent_registry.discover_agents()
        assert len(all_agents) == 1
    
    def test_search_agents(self, agent_registry, sample_agent_card):
        """Test agent search"""
        # Register agent
        agent_registry.register_agent(sample_agent_card)
        
        # Search by name
        agents = agent_registry.search_agents("Test")
        assert len(agents) == 1
        
        # Search by description
        agents = agent_registry.search_agents("testing")
        assert len(agents) == 1
    
    def test_get_capabilities(self, agent_registry, sample_agent_card):
        """Test getting capabilities"""
        # Register agent
        agent_registry.register_agent(sample_agent_card)
        
        capabilities = agent_registry.get_capabilities()
        assert "test.capability" in capabilities
    
    def test_get_registry_stats(self, agent_registry, sample_agent_card):
        """Test getting registry statistics"""
        # Register agent
        agent_registry.register_agent(sample_agent_card)
        
        stats = agent_registry.get_registry_stats()
        assert stats["total_agents"] == 1
        assert stats["total_capabilities"] == 1
        assert "test-agent" in stats["agents"]


class TestA2AHandler:
    """Test A2A handler functionality"""
    
    @pytest.fixture
    def mock_rag_agent(self):
        """Create mock RAG agent"""
        mock_agent = Mock()
        mock_agent.process_query.return_value = {
            "answer": "Test answer",
            "context": [],
            "sources": {}
        }
        return mock_agent
    
    @pytest.fixture
    def mock_vector_store(self):
        """Create mock vector store"""
        return Mock()
    
    @pytest.fixture
    def a2a_handler(self, mock_rag_agent, mock_vector_store):
        """Create A2A handler instance for testing"""
        return A2AHandler(mock_rag_agent, mock_vector_store)
    
    @pytest.mark.asyncio
    async def test_handle_document_query(self, a2a_handler):
        """Test document query handling"""
        request = A2ARequest(
            method="document.query",
            params={"query": "test query"}
        )
        
        response = await a2a_handler.handle_request(request)
        
        assert response.jsonrpc == "2.0"
        assert response.error is None
        assert response.result is not None
        assert "answer" in response.result
    
    @pytest.mark.asyncio
    async def test_handle_unknown_method(self, a2a_handler):
        """Test handling unknown method"""
        request = A2ARequest(
            method="unknown.method",
            params={}
        )
        
        response = await a2a_handler.handle_request(request)
        
        assert response.jsonrpc == "2.0"
        assert response.error is not None
        assert response.error["code"] == -32601
        assert response.result is None
    
    @pytest.mark.asyncio
    async def test_handle_agent_card(self, a2a_handler):
        """Test agent card handling"""
        request = A2ARequest(
            method="agent.card",
            params={}
        )
        
        response = await a2a_handler.handle_request(request)
        
        assert response.jsonrpc == "2.0"
        assert response.error is None
        assert response.result is not None
        assert "agent_id" in response.result
    
    @pytest.mark.asyncio
    async def test_handle_health_check(self, a2a_handler):
        """Test health check handling"""
        request = A2ARequest(
            method="health.check",
            params={}
        )
        
        response = await a2a_handler.handle_request(request)
        
        assert response.jsonrpc == "2.0"
        assert response.error is None
        assert response.result is not None
        assert response.result["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_handle_task_create(self, a2a_handler):
        """Test task creation handling"""
        request = A2ARequest(
            method="task.create",
            params={
                "task_type": "document_processing",
                "params": {"document": "test.pdf"}
            }
        )
        
        response = await a2a_handler.handle_request(request)
        
        assert response.jsonrpc == "2.0"
        assert response.error is None
        assert response.result is not None
        assert "task_id" in response.result
    
    @pytest.mark.asyncio
    async def test_handle_task_status(self, a2a_handler):
        """Test task status handling"""
        # First create a task
        create_request = A2ARequest(
            method="task.create",
            params={
                "task_type": "document_processing",
                "params": {"document": "test.pdf"}
            }
        )
        create_response = await a2a_handler.handle_request(create_request)
        task_id = create_response.result["task_id"]
        
        # Then check status
        status_request = A2ARequest(
            method="task.status",
            params={"task_id": task_id}
        )
        
        response = await a2a_handler.handle_request(status_request)
        
        assert response.jsonrpc == "2.0"
        assert response.error is None
        assert response.result is not None
        assert "task_id" in response.result


class TestAgentCard:
    """Test agent card functionality"""
    
    def test_get_agent_card(self):
        """Test getting agent card"""
        card = get_agent_card()
        
        assert "agent_id" in card
        assert "name" in card
        assert "version" in card
        assert "capabilities" in card
        assert "endpoints" in card
        
        assert card["agent_id"] == "agentic_rag_v1"
        assert card["name"] == "Agentic RAG System"
        assert len(card["capabilities"]) > 0
    
    def test_agent_card_capabilities(self):
        """Test agent card capabilities"""
        card = get_agent_card()
        capabilities = card["capabilities"]
        
        capability_names = [cap["name"] for cap in capabilities]
        
        assert "document.query" in capability_names
        assert "document.upload" in capability_names
        assert "task.create" in capability_names
        assert "task.status" in capability_names
        assert "agent.discover" in capability_names
        assert "health.check" in capability_names


class TestIntegration:
    """Integration tests for A2A protocol"""
    
    @pytest.fixture
    def mock_rag_agent(self):
        """Create mock RAG agent for integration tests"""
        mock_agent = Mock()
        mock_agent.process_query.return_value = {
            "answer": "Integration test answer",
            "context": [{"content": "test context", "metadata": {"source": "test.pdf"}}],
            "sources": {"test.pdf": ["1", "2"]}
        }
        return mock_agent
    
    @pytest.fixture
    def mock_vector_store(self):
        """Create mock vector store for integration tests"""
        return Mock()
    
    @pytest.fixture
    def a2a_handler(self, mock_rag_agent, mock_vector_store):
        """Create A2A handler for integration tests"""
        return A2AHandler(mock_rag_agent, mock_vector_store)
    
    @pytest.mark.asyncio
    async def test_full_document_query_workflow(self, a2a_handler):
        """Test complete document query workflow"""
        # Create request
        request = A2ARequest(
            method="document.query",
            params={
                "query": "What is machine learning?",
                "collection": "PDF",
                "use_cot": True,
                "max_results": 5
            }
        )
        
        # Process request
        response = await a2a_handler.handle_request(request)
        
        # Verify response
        assert response.jsonrpc == "2.0"
        assert response.error is None
        assert response.result is not None
        
        result = response.result
        assert "answer" in result
        assert "context" in result
        assert "sources" in result
        assert "collection_used" in result
    
    @pytest.mark.asyncio
    async def test_task_lifecycle(self, a2a_handler):
        """Test complete task lifecycle"""
        # Create task
        create_request = A2ARequest(
            method="task.create",
            params={
                "task_type": "complex_query",
                "params": {"query": "complex question", "expected_results": 10}
            }
        )
        
        create_response = await a2a_handler.handle_request(create_request)
        assert create_response.error is None
        task_id = create_response.result["task_id"]
        
        # Check task status
        status_request = A2ARequest(
            method="task.status",
            params={"task_id": task_id}
        )
        
        status_response = await a2a_handler.handle_request(status_request)
        assert status_response.error is None
        assert "task_id" in status_response.result
    
    @pytest.mark.asyncio
    async def test_agent_discovery_workflow(self, a2a_handler):
        """Test agent discovery workflow"""
        # Discover agents
        discover_request = A2ARequest(
            method="agent.discover",
            params={"capability": "document.query"}
        )
        
        discover_response = await a2a_handler.handle_request(discover_request)
        assert discover_response.error is None
        assert "agents" in discover_response.result
        
        # Get agent card
        card_request = A2ARequest(
            method="agent.card",
            params={}
        )
        
        card_response = await a2a_handler.handle_request(card_request)
        assert card_response.error is None
        assert "agent_id" in card_response.result


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
