#!/usr/bin/env python3
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Test the LLM configuration
api_key = os.getenv("GROK_API_KEY")
api_url = os.getenv("GROK_API_URL")
model = os.getenv("GROK_MODEL")

print("=" * 50)
print("LLM Configuration Test")
print("=" * 50)
print(f"API Key: {'Set' if api_key else 'Not set'}")
print(f"API URL: {api_url}")
print(f"Model: {model}")
print("=" * 50)

if api_key and api_url and model:
    try:
        import requests
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are an expert log analysis assistant."},
                {"role": "user", "content": "Hello, can you help me analyze logs?"},
            ],
            "temperature": 0.2,
        }
        print("Testing API connection...")
        response = requests.post(api_url, json=payload, headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("SUCCESS: LLM is working!")
            print(f"Response: {data['choices'][0]['message']['content'][:200]}...")
        else:
            print("ERROR: API call failed")
            print(f"Response: {response.text[:500]}")
            
    except Exception as e:
        print(f"ERROR: {e}")
else:
    print("ERROR: Missing configuration")
    
print("=" * 50)
input("Press Enter to exit...")
