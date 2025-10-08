#!/usr/bin/env python3
"""
Test Agent Registration

This script tests the agent registration functionality directly.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from a2a_handler import A2AHandler
from agent_registry import AgentRegistry
from agent_card import get_agent_card
from a2a_models import AgentCard, AgentCapability, AgentEndpoints

def test_agent_registration():
    """Test agent registration directly"""
    print("🔍 Testing Agent Registration...")
    
    # Create a mock RAG agent
    class MockRAGAgent:
        def process_query(self, query):
            return {"answer": "Test answer", "context": []}
    
    # Create A2A handler
    handler = A2AHandler(MockRAGAgent())
    
    # Check registry state
    print(f"Registry has {len(handler.agent_registry.registered_agents)} agents")
    print(f"Available capabilities: {list(handler.agent_registry.capability_index.keys())}")
    
    # Test discovery
    agents = handler.agent_registry.discover_agents("document.query")
    print(f"Found {len(agents)} agents with document.query capability")
    
    for i, agent in enumerate(agents, 1):
        print(f"  Agent {i}: {agent.agent_id} - {agent.name}")
    
    return len(agents) > 0

def test_agent_card_conversion():
    """Test agent card conversion"""
    print("\n🔍 Testing Agent Card Conversion...")
    
    try:
        agent_card_data = get_agent_card()
        print(f"Agent card data type: {type(agent_card_data)}")
        print(f"Agent ID: {agent_card_data.get('agent_id')}")
        print(f"Capabilities count: {len(agent_card_data.get('capabilities', []))}")
        
        # Test conversion to AgentCard object
        capabilities = []
        for cap_data in agent_card_data.get("capabilities", []):
            capability = AgentCapability(
                name=cap_data["name"],
                description=cap_data["description"],
                input_schema=cap_data.get("input_schema", {}),
                output_schema=cap_data.get("output_schema", {})
            )
            capabilities.append(capability)
        
        endpoints_data = agent_card_data.get("endpoints", {})
        endpoints = AgentEndpoints(
            base_url=endpoints_data.get("base_url", "http://localhost:8000"),
            authentication=endpoints_data.get("authentication", {})
        )
        
        agent_card = AgentCard(
            agent_id=agent_card_data["agent_id"],
            name=agent_card_data["name"],
            version=agent_card_data["version"],
            description=agent_card_data["description"],
            capabilities=capabilities,
            endpoints=endpoints,
            metadata=agent_card_data.get("metadata", {})
        )
        
        print(f"Created AgentCard: {agent_card.agent_id}")
        print(f"Capabilities: {[cap.name for cap in agent_card.capabilities]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Agent Card Conversion: ERROR - {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

def main():
    """Main test function"""
    print("🤖 Agent Registration Test")
    print("=" * 40)
    
    # Test agent card conversion
    card_success = test_agent_card_conversion()
    
    # Test agent registration
    reg_success = test_agent_registration()
    
    if card_success and reg_success:
        print("\n🎉 Agent registration is working!")
        print("✅ OK")
    else:
        print("\n❌ Agent registration has issues.")
        print("❌ NOT OK")

if __name__ == "__main__":
    main()
