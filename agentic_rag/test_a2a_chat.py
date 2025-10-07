#!/usr/bin/env python3
"""
Test script for A2A Chat Interface

This script demonstrates how to test the A2A Chat Interface functionality
that's now integrated into the Gradio app.
"""

import requests
import json
import time

def test_a2a_chat_interface():
    """Test A2A Chat Interface functionality"""
    print("🤖 A2A Chat Interface Test")
    print("=" * 60)
    print("This script tests the A2A Chat Interface functionality.")
    print("Make sure both servers are running:")
    print("  - A2A Server: python main.py (port 8000)")
    print("  - Gradio App: python gradio_app.py (port 7860)")
    print("=" * 60)
    
    # Test A2A server connectivity
    print("\n1. Testing A2A Server Connectivity...")
    try:
        response = requests.get("http://localhost:8000/a2a/health", timeout=5)
        if response.status_code == 200:
            print("✅ A2A Server is running and accessible")
        else:
            print(f"❌ A2A Server returned status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ A2A Server is not accessible: {str(e)}")
        print("💡 Make sure to start the A2A server with: python main.py")
        return False
    
    # Test Gradio app connectivity
    print("\n2. Testing Gradio App Connectivity...")
    try:
        response = requests.get("http://localhost:7860", timeout=5)
        if response.status_code == 200:
            print("✅ Gradio App is running and accessible")
        else:
            print(f"❌ Gradio App returned status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Gradio App is not accessible: {str(e)}")
        print("💡 Make sure to start the Gradio app with: python gradio_app.py")
        return False
    
    # Test A2A document query (simulating chat interface)
    print("\n3. Testing A2A Document Query (Chat Simulation)...")
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
            "id": "chat-test"
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
                print(f"❌ A2A Document Query failed: {query_data['error']}")
                return False
            else:
                result = query_data.get("result", {})
                answer = result.get("answer", "No answer")
                sources = result.get("sources", {})
                reasoning = result.get("reasoning_steps", [])
                
                print(f"✅ A2A Document Query successful:")
                print(f"   Answer: {answer[:100]}...")
                print(f"   Sources: {len(sources)} found")
                print(f"   Reasoning steps: {len(reasoning)}")
        else:
            print(f"❌ A2A Document Query failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ A2A Document Query error: {str(e)}")
        return False
    
    # Test A2A document query with CoT
    print("\n4. Testing A2A Document Query with Chain of Thought...")
    try:
        query_payload = {
            "jsonrpc": "2.0",
            "method": "document.query",
            "params": {
                "query": "Explain machine learning concepts",
                "collection": "General",
                "use_cot": True,
                "max_results": 3
            },
            "id": "chat-cot-test"
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
                print(f"❌ A2A CoT Query failed: {query_data['error']}")
                return False
            else:
                result = query_data.get("result", {})
                answer = result.get("answer", "No answer")
                reasoning = result.get("reasoning_steps", [])
                
                print(f"✅ A2A CoT Query successful:")
                print(f"   Answer: {answer[:100]}...")
                print(f"   Reasoning steps: {len(reasoning)}")
                if reasoning:
                    print(f"   First reasoning step: {reasoning[0][:100]}...")
        else:
            print(f"❌ A2A CoT Query failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ A2A CoT Query error: {str(e)}")
        return False
    
    print("\n🎉 All A2A Chat Interface tests passed!")
    print("\n💡 You can now:")
    print("   - Open http://localhost:7860 in your browser")
    print("   - Go to the 'A2A Chat Interface' tab")
    print("   - Chat with your documents using A2A protocol")
    print("   - Use the 'A2A Protocol Testing' tab for comprehensive testing")
    
    return True

def main():
    """Main test function"""
    success = test_a2a_chat_interface()
    
    if success:
        print("\n" + "=" * 60)
        print("✅ A2A Chat Interface is working correctly!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ Some tests failed. Please check the server configurations.")
        print("=" * 60)

if __name__ == "__main__":
    main()
