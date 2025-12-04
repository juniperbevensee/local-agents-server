#!/usr/bin/env python3
"""
Test script to send requests to the Flask agent
"""

import requests
import json
import sys

AGENT_URL = "http://localhost:5000/v1/chat/completions"

def test_with_url(url):
    """Test the agent with a direct URL."""
    payload = {
        "model": "local-model",
        "messages": [
            {
                "role": "user",
                "content": f"Please summarize this article: {url}"
            }
        ],
        "stream": False
    }

    print(f"Sending request to agent...")
    print(f"URL to summarize: {url}\n")

    try:
        response = requests.post(AGENT_URL, json=payload)
        response.raise_for_status()

        result = response.json()
        print("Response:")
        print(json.dumps(result, indent=2))

        if 'choices' in result and len(result['choices']) > 0:
            print("\n" + "="*50)
            print("Summary:")
            print("="*50)
            print(result['choices'][0]['message']['content'])

    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the agent. Make sure it's running on port 5000.")
    except Exception as e:
        print(f"Error: {e}")

def test_with_search_query(query, platform):
    """Test the agent with a search query."""
    payload = {
        "model": "local-model",
        "messages": [
            {
                "role": "user",
                "content": f"Search {query} on {platform} 10 posts."
            }
        ],
        "stream": False
    }

    print(f"Sending search request to agent...")
    print(f"Query: {query} on {platform}\n")

    try:
        response = requests.post(AGENT_URL, json=payload)
        response.raise_for_status()

        result = response.json()
        print("Response:")
        print(json.dumps(result, indent=2))

        if 'choices' in result and len(result['choices']) > 0:
            print("\n" + "="*50)
            print("Agent Response:")
            print("="*50)
            print(result['choices'][0]['message']['content'])

    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the agent. Make sure it's running on port 5000.")
    except Exception as e:
        print(f"Error: {e}")

def test_health():
    """Test the health endpoint."""
    try:
        response = requests.get("http://localhost:5000/health")
        response.raise_for_status()
        print("Health check:")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Health check failed: {e}")

if __name__ == "__main__":
    print("Flask Agent Test Script")
    print("="*50)

    # Test health endpoint
    test_health()
    print("\n" + "="*50 + "\n")

    if len(sys.argv) > 1:
        # Use URL from command line
        url = sys.argv[1]
        test_with_url(url)
    else:
        # Example tests
        print("Test 1: URL Summarization")
        print("="*50)
        test_with_url("https://example.com")

        print("\n\n" + "="*50)
        print("Test 2: Search Query (should prompt for URL)")
        print("="*50)
        test_with_search_query("Trump", "Telegram")
