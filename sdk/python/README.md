# TSM Python SDK

Official Python client library for The Sovereign Mechanica AI Control Plane.

## Installation

```bash
pip install tsm-sdk
```

## Quick Start

### Async Usage

```python
from tsm_sdk import TSMClient, ExecuteOptions, ModelProvider

async def main():
    # Create client
    client = TSMClient(api_key="your-api-key")

    # Execute a simple request
    response = await client.execute("What is artificial intelligence?")
    print(response.output)

    # Execute with options
    options = ExecuteOptions(
        model="gpt-4",
        provider=ModelProvider.OPENAI,
        temperature=0.7,
        max_tokens=1000
    )
    response = await client.execute("Explain quantum computing", options=options)
    print(f"Cost: ${response.cost:.4f}")
    print(f"Tokens: {response.tokens}")

    # Clean up
    await client.close()

# Run
import asyncio
asyncio.run(main())
```

### Synchronous Usage

```python
from tsm_sdk import TSMClientSync

# Create synchronous client
client = TSMClientSync(api_key="your-api-key")

# Execute request
response = client.execute("What is AI?")
print(response.output)

# Clean up
client.close()
```

### Streaming Responses

```python
async def stream_example():
    async with TSMClient(api_key="your-api-key") as client:
        async for chunk in client.execute_stream("Write a story about AI"):
            print(chunk.content, end="", flush=True)

            if chunk.is_final:
                print("\n[Stream complete]")

asyncio.run(stream_example())
```

## Features

### Model Execution

Execute AI models with flexible options:

```python
from tsm_sdk import TSMClient, ExecuteOptions, ModelProvider

async with TSMClient(api_key="your-api-key") as client:
    # Use specific model
    response = await client.execute(
        "Analyze this code for security issues",
        options=ExecuteOptions(
            model="gpt-4",
            provider=ModelProvider.OPENAI,
            temperature=0.2
        )
    )

    # Local-first (privacy mode)
    response = await client.execute(
        "Sensitive data analysis",
        options=ExecuteOptions(provider=ModelProvider.LOCAL)
    )
```

### Document Management

Add and search documents in TSM's memory store:

```python
async with TSMClient(api_key="your-api-key") as client:
    # Add document
    doc = await client.add_document(
        content="Python is a programming language",
        metadata={"type": "definition", "language": "python"}
    )

    # Search documents
    results = await client.search_documents("programming language", top_k=5)
    for doc in results:
        print(f"- {doc.content}")

    # Delete document
    await client.delete_document(doc.document_id)
```

### Analytics

Get usage analytics:

```python
from datetime import datetime, timedelta

async with TSMClient(api_key="your-api-key") as client:
    # Get last 7 days analytics
    analytics = await client.get_analytics(
        start_date=datetime.now() - timedelta(days=7),
        end_date=datetime.now()
    )

    print(f"Total requests: {analytics.total_requests}")
    print(f"Total tokens: {analytics.total_tokens:,}")
    print(f"Total cost: ${analytics.total_cost:.2f}")
    print(f"Avg latency: {analytics.avg_latency_ms:.0f}ms")
    print(f"Success rate: {analytics.success_rate * 100:.1f}%")
```

### Model Discovery

List available models:

```python
async with TSMClient(api_key="your-api-key") as client:
    models = await client.list_models()

    for model in models:
        print(f"{model.name} ({model.provider})")
        print(f"  Context: {model.context_window:,} tokens")
        print(f"  Cost: ${model.cost_per_token * 1_000_000:.2f} per 1M tokens")
```

### Cache Management

Clear cache when needed:

```python
async with TSMClient(api_key="your-api-key") as client:
    await client.clear_cache()
```

## Error Handling

The SDK provides specific exception types:

```python
from tsm_sdk import (
    TSMError,
    AuthenticationError,
    RateLimitError,
    QuotaExceededError
)

async with TSMClient(api_key="your-api-key") as client:
    try:
        response = await client.execute("Hello")
    except AuthenticationError:
        print("Invalid API key")
    except RateLimitError as e:
        print(f"Rate limited: {e}")
    except QuotaExceededError as e:
        print(f"Quota exceeded: {e}")
    except TSMError as e:
        print(f"API error: {e}")
```

## Configuration

### Base URL

For self-hosted or enterprise deployments:

```python
client = TSMClient(
    api_key="your-api-key",
    base_url="https://your-tsm-instance.com"
)
```

### Timeout

Customize request timeout:

```python
client = TSMClient(
    api_key="your-api-key",
    timeout=60  # 60 seconds
)
```

## Response Objects

### Response

```python
@dataclass
class Response:
    request_id: str        # Unique request ID
    output: str           # Model output
    model: str            # Model used
    provider: str         # Provider used
    tokens: int           # Tokens consumed
    cost: float           # Cost in USD
    latency_ms: float     # Latency in milliseconds
    metadata: Dict        # Additional metadata
```

### Document

```python
@dataclass
class Document:
    document_id: str      # Unique document ID
    content: str          # Document content
    metadata: Dict        # Document metadata
    created_at: datetime  # Creation timestamp
```

### Analytics

```python
@dataclass
class Analytics:
    total_requests: int       # Total number of requests
    total_tokens: int         # Total tokens consumed
    total_cost: float         # Total cost in USD
    avg_latency_ms: float     # Average latency
    success_rate: float       # Success rate (0.0-1.0)
```

## Best Practices

### Context Manager

Always use context manager for automatic cleanup:

```python
async with TSMClient(api_key="key") as client:
    response = await client.execute("prompt")
    # Client automatically closed
```

### Error Handling

Always handle errors appropriately:

```python
try:
    response = await client.execute("prompt")
except QuotaExceededError:
    # Handle quota exceeded (e.g., upgrade tier)
    pass
except RateLimitError:
    # Handle rate limit (e.g., exponential backoff)
    pass
```

### Streaming for Long Responses

Use streaming for long-form content:

```python
async for chunk in client.execute_stream("Write a long article"):
    # Process chunks as they arrive
    process(chunk.content)
```

## Advanced Usage

### Custom Metadata

Include metadata with requests:

```python
options = ExecuteOptions(
    metadata={
        "user_id": "user123",
        "session_id": "session456",
        "request_type": "analysis"
    }
)
response = await client.execute("prompt", options=options)
```

### Provider Selection

Choose specific providers for different use cases:

```python
# High quality
response = await client.execute(
    "Complex reasoning task",
    options=ExecuteOptions(provider=ModelProvider.ANTHROPIC)
)

# Fast and cheap
response = await client.execute(
    "Simple classification",
    options=ExecuteOptions(provider=ModelProvider.GROQ)
)

# Privacy-first
response = await client.execute(
    "Sensitive data processing",
    options=ExecuteOptions(provider=ModelProvider.LOCAL)
)
```

## Support

- Documentation: https://docs.tsm-platform.com
- Issues: https://github.com/tsm-platform/python-sdk/issues
- Email: support@tsm-platform.com

## License

MIT License - see LICENSE file for details.
