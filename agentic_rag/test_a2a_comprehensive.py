#!/usr/bin/env python3
"""
Comprehensive A2A Test Script

This script performs comprehensive testing of the A2A protocol functionality:
1. Health check
2. Agent discovery
3. Task creation with a new command
4. Task status verification
5. Document query test
6. Prints "OK" if everything works correctly
"""

import requests
import json
import time
import uuid
from datetime import datetime

class A2ATester:
    """Comprehensive A2A testing class"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.timeout = 30
        self.test_results = []
    
    def make_a2a_request(self, method: str, params: dict, request_id: str = None) -> dict:
        """Make an A2A JSON-RPC request"""
        if request_id is None:
            request_id = str(uuid.uuid4())
        
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": request_id
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/a2a",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": f"Request failed: {str(e)}"
                },
                "id": request_id
            }
    
    def test_health_check(self) -> bool:
        """Test A2A health check"""
        print("🔍 Testing Health Check...")
        
        try:
            response = self.session.get(f"{self.base_url}/a2a/health", timeout=10)
            if response.status_code == 200:
                health_data = response.json()
                if "result" in health_data and health_data["result"].get("status") == "healthy":
                    print("✅ Health Check: PASSED")
                    self.test_results.append(("Health Check", True, "Server is healthy"))
                    return True
                else:
                    print(f"❌ Health Check: FAILED - {health_data}")
                    self.test_results.append(("Health Check", False, str(health_data)))
                    return False
            else:
                print(f"❌ Health Check: FAILED - HTTP {response.status_code}")
                self.test_results.append(("Health Check", False, f"HTTP {response.status_code}"))
                return False
        except Exception as e:
            print(f"❌ Health Check: ERROR - {str(e)}")
            self.test_results.append(("Health Check", False, str(e)))
            return False
    
    def test_agent_discovery(self) -> bool:
        """Test A2A agent discovery"""
        print("🔍 Testing Agent Discovery...")
        
        try:
            response = self.make_a2a_request(
                "agent.discover",
                {"capability": "document.query"}
            )
            
            print(f"Discovery response: {json.dumps(response, indent=2)}")
            
            if "error" in response:
                print(f"❌ Agent Discovery: FAILED - {response['error']}")
                self.test_results.append(("Agent Discovery", False, str(response['error'])))
                return False
            else:
                result = response.get("result", {})
                agents = result.get("agents", [])
                if agents:
                    print(f"✅ Agent Discovery: PASSED - Found {len(agents)} agents")
                    for i, agent in enumerate(agents, 1):
                        agent_id = agent.get('agent_id', 'unknown')
                        agent_name = agent.get('name', 'unknown')
                        print(f"  Agent {i}: {agent_id} - {agent_name}")
                    self.test_results.append(("Agent Discovery", True, f"Found {len(agents)} agents"))
                    return True
                else:
                    print("❌ Agent Discovery: FAILED - No agents found")
                    print(f"  Result: {result}")
                    self.test_results.append(("Agent Discovery", False, "No agents found"))
                    return False
        except Exception as e:
            print(f"❌ Agent Discovery: ERROR - {str(e)}")
            self.test_results.append(("Agent Discovery", False, str(e)))
            return False
    
    def test_document_query(self) -> bool:
        """Test A2A document query"""
        print("🔍 Testing Document Query...")
        
        try:
            response = self.make_a2a_request(
                "document.query",
                {
                    "query": "What is artificial intelligence?",
                    "collection": "General",
                    "use_cot": False,
                    "max_results": 3
                }
            )
            
            if "error" in response:
                print(f"❌ Document Query: FAILED - {response['error']}")
                self.test_results.append(("Document Query", False, str(response['error'])))
                return False
            else:
                result = response.get("result", {})
                answer = result.get("answer", "")
                if answer and answer != "No answer provided":
                    print(f"✅ Document Query: PASSED - Got answer: {answer[:50]}...")
                    self.test_results.append(("Document Query", True, f"Got answer: {answer[:50]}..."))
                    return True
                else:
                    print(f"❌ Document Query: FAILED - No valid answer: {result}")
                    self.test_results.append(("Document Query", False, f"No valid answer: {result}"))
                    return False
        except Exception as e:
            print(f"❌ Document Query: ERROR - {str(e)}")
            self.test_results.append(("Document Query", False, str(e)))
            return False
    
    def test_task_creation_and_status(self) -> bool:
        """Test A2A task creation and status checking"""
        print("🔍 Testing Task Creation and Status...")
        
        # Create a unique task
        task_id = f"test-task-{int(time.time())}"
        task_params = {
            "command": "test_command",
            "description": f"Test task created at {datetime.now().isoformat()}",
            "priority": "high",
            "test_id": task_id
        }
        
        try:
            # Create task
            create_response = self.make_a2a_request(
                "task.create",
                {
                    "task_type": "document_processing",
                    "params": task_params
                },
                f"create-{task_id}"
            )
            
            if "error" in create_response:
                print(f"❌ Task Creation: FAILED - {create_response['error']}")
                self.test_results.append(("Task Creation", False, str(create_response['error'])))
                return False
            
            result = create_response.get("result", {})
            created_task_id = result.get("task_id")
            
            if not created_task_id:
                print(f"❌ Task Creation: FAILED - No task ID returned: {result}")
                self.test_results.append(("Task Creation", False, f"No task ID: {result}"))
                return False
            
            print(f"✅ Task Creation: PASSED - Created task: {created_task_id}")
            self.test_results.append(("Task Creation", True, f"Created task: {created_task_id}"))
            
            # Wait a moment for task to be processed
            time.sleep(2)
            
            # Check task status
            status_response = self.make_a2a_request(
                "task.status",
                {"task_id": created_task_id},
                f"status-{created_task_id}"
            )
            
            if "error" in status_response:
                print(f"❌ Task Status: FAILED - {status_response['error']}")
                self.test_results.append(("Task Status", False, str(status_response['error'])))
                return False
            
            status_result = status_response.get("result", {})
            task_status = status_result.get("status", "unknown")
            
            print(f"✅ Task Status: PASSED - Task status: {task_status}")
            self.test_results.append(("Task Status", True, f"Task status: {task_status}"))
            
            return True
            
        except Exception as e:
            print(f"❌ Task Operations: ERROR - {str(e)}")
            self.test_results.append(("Task Operations", False, str(e)))
            return False
    
    def run_comprehensive_test(self) -> bool:
        """Run all A2A tests comprehensively"""
        print("🤖 A2A Comprehensive Test Suite")
        print("=" * 60)
        print("Testing A2A protocol functionality...")
        print("=" * 60)
        
        all_passed = True
        
        # Test 1: Health Check
        if not self.test_health_check():
            all_passed = False
        
        # Test 2: Agent Discovery
        if not self.test_agent_discovery():
            all_passed = False
        
        # Test 3: Document Query
        if not self.test_document_query():
            all_passed = False
        
        # Test 4: Task Creation and Status
        if not self.test_task_creation_and_status():
            all_passed = False
        
        # Print results summary
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)
        
        for test_name, passed, details in self.test_results:
            status = "✅ PASSED" if passed else "❌ FAILED"
            print(f"{test_name}: {status}")
            if not passed:
                print(f"  Details: {details}")
        
        print("=" * 60)
        
        if all_passed:
            print("🎉 ALL TESTS PASSED - A2A SYSTEM IS WORKING CORRECTLY!")
            print("✅ OK")
            return True
        else:
            print("❌ SOME TESTS FAILED - A2A SYSTEM HAS ISSUES")
            print("❌ NOT OK")
            return False

def main():
    """Main test function"""
    print("Starting A2A Comprehensive Test...")
    print("Make sure the A2A server is running: python main.py")
    print()
    
    tester = A2ATester()
    success = tester.run_comprehensive_test()
    
    if success:
        print("\n🎉 A2A system is fully operational!")
        exit(0)
    else:
        print("\n❌ A2A system has issues that need to be resolved.")
        exit(1)

if __name__ == "__main__":
    main()
