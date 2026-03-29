"""Direct test of TSM Layer without server"""
import sys
sys.path.insert(0, 'C:/Users/mymai/Desktop/TSMv1')

print("Testing TSM Layer components...")

# Test 1: Import firewall
print("\n1. Testing firewall...")
from firewall import sanitizer
result = sanitizer.sanitize("My SSN is 123-45-6789")
print(f"   Original had SSN, sanitized: {result.sanitized_text}")
print(f"   Redactions: {len(result.redactions)}")

# Test 2: Import classifier
print("\n2. Testing risk classifier...")
from firewall import classifier
import asyncio
async def test_classifier():
    risk = await classifier.classify("secret api key", {})
    print(f"   Risk tier: {risk.tier}")
    print(f"   Category: {risk.category}")

asyncio.run(test_classifier())

# Test 3: Gateway import
print("\n3. Testing gateway import...")
try:
    from gateway.api import app
    print("   Gateway API imported successfully!")
    print(f"   App title: {app.title}")
except Exception as e:
    print(f"   Error: {e}")

print("\nTests complete!")
