#!/usr/bin/env python3
"""
Test Agent Discovery Fix

This script tests the agent discovery functionality to verify the fix.
"""

import requests
import json

def test_agent_discovery():
    """Test agent discovery functionality"""
    print("🔍 Testing Agent Discovery...")
    
    try:
        # Test agent discovery
        discover_payload = {
            "jsonrpc": "2.0",
            "method": "agent.discover",
            "params": {"capability": "document.query"},
            "id": "test-discover"
        }
        
        response = requests.post(
            "http://localhost:8000/a2a",
            json=discover_payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            discover_data = response.json()
            print(f"Response: {json.dumps(discover_data, indent=2)}")
            
            if "error" in discover_data:
                print(f"❌ Agent Discovery: FAILED - {discover_data['error']}")
                return False
            else:
                result = discover_data.get("result", {})
                agents = result.get("agents", [])
                print(f"✅ Agent Discovery: Found {len(agents)} agents")
                
                for i, agent in enumerate(agents, 1):
                    print(f"  Agent {i}: {agent.get('agent_id', 'unknown')} - {agent.get('name', 'unknown')}")
                
                return len(agents) > 0
        else:
            print(f"❌ Agent Discovery: FAILED - HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Agent Discovery: ERROR - {str(e)}")
        return False

def test_agent_card():
    """Test agent card functionality"""
    print("\n🔍 Testing Agent Card...")
    
    try:
        response = requests.get("http://localhost:8000/agent_card", timeout=10)
        if response.status_code == 200:
            card_data = response.json()
            print(f"✅ Agent Card: Retrieved successfully")
            print(f"   Agent ID: {card_data.get('agent_id', 'Unknown')}")
            print(f"   Name: {card_data.get('name', 'Unknown')}")
            print(f"   Capabilities: {len(card_data.get('capabilities', []))} found")
            return True
        else:
            print(f"❌ Agent Card: FAILED - HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Agent Card: ERROR - {str(e)}")
        return False

def main():
    """Main test function"""
    print("🤖 Agent Discovery Test")
    print("=" * 40)
    print("Make sure A2A server is running: python main.py")
    print()
    
    # Test agent card first
    card_success = test_agent_card()
    
    # Test agent discovery
    discovery_success = test_agent_discovery()
    
    if card_success and discovery_success:
        print("\n🎉 Agent Discovery is working!")
        print("✅ OK")
    else:
        print("\n❌ Agent Discovery has issues.")
        print("❌ NOT OK")

if __name__ == "__main__":
    main()
