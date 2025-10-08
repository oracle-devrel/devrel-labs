#!/usr/bin/env python3
"""
Simple A2A Test Script

This script performs a simple test of the A2A protocol to verify all fixes.
"""

import requests
import json
import time

def test_a2a_simple():
    """Simple A2A test"""
    print("🔍 Simple A2A Test")
    print("=" * 40)
    
    # Test health check
    print("1. Testing Health Check...")
    try:
        response = requests.get("http://localhost:8000/a2a/health", timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            if "result" in health_data and health_data["result"].get("status") == "healthy":
                print("✅ Health Check: PASSED")
            else:
                print(f"❌ Health Check: FAILED - {health_data}")
                return False
        else:
            print(f"❌ Health Check: FAILED - HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health Check: ERROR - {str(e)}")
        return False
    
    # Test agent discovery
    print("\n2. Testing Agent Discovery...")
    try:
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
            if "error" in discover_data:
                print(f"❌ Agent Discovery: FAILED - {discover_data['error']}")
                return False
            else:
                result = discover_data.get("result", {})
                agents = result.get("agents", [])
                if agents:
                    print(f"✅ Agent Discovery: PASSED - Found {len(agents)} agents")
                    for i, agent in enumerate(agents, 1):
                        agent_id = agent.get('agent_id', 'unknown')
                        agent_name = agent.get('name', 'unknown')
                        print(f"  Agent {i}: {agent_id} - {agent_name}")
                else:
                    print("❌ Agent Discovery: FAILED - No agents found")
                    print(f"  Result: {result}")
                    return False
        else:
            print(f"❌ Agent Discovery: FAILED - HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Agent Discovery: ERROR - {str(e)}")
        return False
    
    # Test document query
    print("\n3. Testing Document Query...")
    try:
        query_payload = {
            "jsonrpc": "2.0",
            "method": "document.query",
            "params": {
                "query": "What is artificial intelligence?",
                "collection": "General",
                "use_cot": False,
                "max_results": 3
            },
            "id": "test-query"
        }
        
        response = requests.post(
            "http://localhost:8000/a2a",
            json=query_payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            query_data = response.json()
            if "error" in query_data:
                print(f"❌ Document Query: FAILED - {query_data['error']}")
                return False
            else:
                result = query_data.get("result", {})
                answer = result.get("answer", "")
                if answer and answer != "No answer provided" and answer.strip():
                    print(f"✅ Document Query: PASSED")
                    print(f"   Answer: {answer[:100]}...")
                else:
                    print(f"❌ Document Query: FAILED - No valid answer")
                    print(f"   Result: {result}")
                    return False
        else:
            print(f"❌ Document Query: FAILED - HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Document Query: ERROR - {str(e)}")
        return False
    
    # Test task creation
    print("\n4. Testing Task Creation...")
    try:
        task_payload = {
            "jsonrpc": "2.0",
            "method": "task.create",
            "params": {
                "task_type": "document_processing",
                "params": {
                    "command": "test_command",
                    "description": "Test task for A2A testing",
                    "priority": "high"
                }
            },
            "id": "test-task"
        }
        
        response = requests.post(
            "http://localhost:8000/a2a",
            json=task_payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            task_data = response.json()
            if "error" in task_data:
                print(f"❌ Task Creation: FAILED - {task_data['error']}")
                return False
            else:
                result = task_data.get("result", {})
                task_id = result.get("task_id")
                if task_id:
                    print(f"✅ Task Creation: PASSED - Created task {task_id}")
                    
                    # Test task status
                    time.sleep(1)
                    status_payload = {
                        "jsonrpc": "2.0",
                        "method": "task.status",
                        "params": {"task_id": task_id},
                        "id": "test-status"
                    }
                    
                    status_response = requests.post(
                        "http://localhost:8000/a2a",
                        json=status_payload,
                        headers={"Content-Type": "application/json"},
                        timeout=10
                    )
                    
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        if "error" not in status_data:
                            status_result = status_data.get("result", {})
                            task_status = status_result.get("status", "unknown")
                            print(f"✅ Task Status: PASSED - Status: {task_status}")
                        else:
                            print(f"❌ Task Status: FAILED - {status_data['error']}")
                            return False
                    else:
                        print(f"❌ Task Status: FAILED - HTTP {status_response.status_code}")
                        return False
                else:
                    print(f"❌ Task Creation: FAILED - No task ID returned")
                    return False
        else:
            print(f"❌ Task Creation: FAILED - HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Task Operations: ERROR - {str(e)}")
        return False
    
    return True

def main():
    """Main function"""
    print("🤖 Simple A2A Test")
    print("Make sure A2A server is running: python main.py")
    print()
    
    success = test_a2a_simple()
    
    if success:
        print("\n🎉 All A2A tests passed!")
        print("✅ OK")
    else:
        print("\n❌ Some A2A tests failed.")
        print("❌ NOT OK")

if __name__ == "__main__":
    main()
