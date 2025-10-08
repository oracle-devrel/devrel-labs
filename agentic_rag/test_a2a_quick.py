#!/usr/bin/env python3
"""
Quick A2A Test Script

This script performs a quick test of the A2A protocol to verify the fixes.
"""

import requests
import json
import time

def test_a2a_quick():
    """Quick A2A test"""
    print("🔍 Quick A2A Test")
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
    
    # Test document query
    print("\n2. Testing Document Query...")
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
            "id": "quick-test"
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
                    return True
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

def main():
    """Main function"""
    print("🤖 Quick A2A Test")
    print("Make sure A2A server is running: python main.py")
    print()
    
    success = test_a2a_quick()
    
    if success:
        print("\n🎉 A2A Document Query is working!")
        print("✅ OK")
    else:
        print("\n❌ A2A Document Query has issues.")
        print("❌ NOT OK")

if __name__ == "__main__":
    main()
