#!/usr/bin/env python3
"""
Test script for A2A Gradio integration

This script demonstrates how to test the A2A functionality
that's now integrated into the Gradio app.
"""

import requests
import json
import time

def test_a2a_server_connectivity():
    """Test if A2A server is running and accessible"""
    try:
        response = requests.get("http://localhost:8000/a2a/health", timeout=5)
        if response.status_code == 200:
            print("✅ A2A Server is running and accessible")
            return True
        else:
            print(f"❌ A2A Server returned status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ A2A Server is not accessible: {str(e)}")
        print("💡 Make sure to start the A2A server with: python main.py")
        return False

def test_gradio_app_connectivity():
    """Test if Gradio app is running and accessible"""
    try:
        response = requests.get("http://localhost:7860", timeout=5)
        if response.status_code == 200:
            print("✅ Gradio App is running and accessible")
            return True
        else:
            print(f"❌ Gradio App returned status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Gradio App is not accessible: {str(e)}")
        print("💡 Make sure to start the Gradio app with: python gradio_app.py")
        return False

def test_a2a_functionality():
    """Test basic A2A functionality"""
    print("\n🧪 Testing A2A Functionality...")
    print("=" * 50)
    
    # Test health check
    try:
        response = requests.get("http://localhost:8000/a2a/health", timeout=10)
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ Health Check: {health_data}")
        else:
            print(f"❌ Health Check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health Check error: {str(e)}")
        return False
    
    # Test agent card
    try:
        response = requests.get("http://localhost:8000/agent_card", timeout=10)
        if response.status_code == 200:
            card_data = response.json()
            print(f"✅ Agent Card: {json.dumps(card_data, indent=2)}")
        else:
            print(f"❌ Agent Card failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Agent Card error: {str(e)}")
        return False
    
    # Test document query
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
                print(f"❌ Document Query failed: {query_data['error']}")
                return False
            else:
                result = query_data.get("result", {})
                answer = result.get("answer", "No answer")
                print(f"✅ Document Query: {answer[:100]}...")
        else:
            print(f"❌ Document Query failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Document Query error: {str(e)}")
        return False
    
    return True

def main():
    """Main test function"""
    print("🤖 A2A Gradio Integration Test")
    print("=" * 60)
    print("This script tests the A2A functionality integrated into the Gradio app.")
    print("Make sure both servers are running:")
    print("  - A2A Server: python main.py (port 8000)")
    print("  - Gradio App: python gradio_app.py (port 7860)")
    print("=" * 60)
    
    # Test server connectivity
    print("\n1. Testing Server Connectivity...")
    a2a_running = test_a2a_server_connectivity()
    gradio_running = test_gradio_app_connectivity()
    
    if not a2a_running or not gradio_running:
        print("\n❌ One or both servers are not running. Please start them and try again.")
        return
    
    # Test A2A functionality
    print("\n2. Testing A2A Functionality...")
    a2a_working = test_a2a_functionality()
    
    if a2a_working:
        print("\n🎉 All tests passed! A2A Gradio integration is working correctly.")
        print("\n💡 You can now:")
        print("   - Open http://localhost:7860 in your browser")
        print("   - Go to the 'A2A Protocol Testing' tab")
        print("   - Test all A2A functionality through the web interface")
    else:
        print("\n❌ Some tests failed. Please check the A2A server configuration.")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
