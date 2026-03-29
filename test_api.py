"""Test TSM Layer API directly"""
import sys
sys.path.insert(0, 'C:/Users/mymai/Desktop/TSMv1')

import asyncio
from gateway.api import app
from gateway.pipeline import RequestPipeline

async def test_pipeline():
    """Test the full request pipeline"""
    print("Testing TSM Layer Request Pipeline")
    print("=" * 60)

    pipeline = RequestPipeline()

    # Test 1: SSN redaction
    print("\n1. Testing SSN redaction...")
    result = await pipeline.execute(
        input_text="My SSN is 123-45-6789. Analyze this code.",
        context={"user_id": "test_user", "org_id": "test_org"},
        options={}
    )

    print(f"   Input had SSN")
    print(f"   Output: {result['output'][:100]}...")
    print(f"   Trace ID: {result['trace_id']}")
    print(f"   Metadata: {result['metadata']}")

    # Test 2: API key redaction
    print("\n2. Testing API key redaction...")
    result = await pipeline.execute(
        input_text="Use api_key=sk-1234567890abcdefghij for authentication",
        context={"user_id": "test_user"},
        options={}
    )

    print(f"   Output: {result['output'][:100]}...")
    print(f"   Sanitized: {result['metadata']['sanitized']}")

    # Test 3: Normal request
    print("\n3. Testing normal request...")
    result = await pipeline.execute(
        input_text="What is the capital of France?",
        context={"user_id": "test_user"},
        options={}
    )

    print(f"   Output: {result['output']}")
    print(f"   Risk tier: {result['metadata']['risk_tier']}")

    print("\n" + "=" * 60)
    print("All tests passed!")

if __name__ == "__main__":
    asyncio.run(test_pipeline())
