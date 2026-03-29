"""
TSM Python SDK
==============

Official Python client library for TSM Platform.

Installation:
    pip install tsm-sdk

Usage:
    from tsm_sdk import TSMClient

    client = TSMClient(api_key="your-api-key")
    response = client.execute("What is AI?")
    print(response.output)
"""

from typing import Dict, List, Optional, Any, AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio
import aiohttp
import json
import logging

logger = logging.getLogger(__name__)


class ModelProvider(str, Enum):
    """Available model providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    LOCAL = "local"
    AZURE = "azure"
    TOGETHER = "together"
    GROQ = "groq"
    DEEPSEEK = "deepseek"


@dataclass
class ExecuteOptions:
    """Options for model execution."""

    model: Optional[str] = None
    provider: Optional[ModelProvider] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    stream: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Response:
    """TSM API response."""

    request_id: str
    output: str
    model: str
    provider: str
    tokens: int
    cost: float
    latency_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Response":
        return cls(
            request_id=data["request_id"],
            output=data["output"],
            model=data["model"],
            provider=data["provider"],
            tokens=data["tokens"],
            cost=data["cost"],
            latency_ms=data["latency_ms"],
            metadata=data.get("metadata", {}),
        )


@dataclass
class StreamChunk:
    """Streaming response chunk."""

    chunk_id: str
    content: str
    is_final: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Document:
    """Document in memory store."""

    document_id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Document":
        return cls(
            document_id=data["document_id"],
            content=data["content"],
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
        )


@dataclass
class Model:
    """Model information."""

    model_id: str
    name: str
    provider: str
    context_window: int
    cost_per_token: float

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Model":
        return cls(
            model_id=data["model_id"],
            name=data["name"],
            provider=data["provider"],
            context_window=data["context_window"],
            cost_per_token=data["cost_per_token"],
        )


@dataclass
class Analytics:
    """Usage analytics."""

    total_requests: int
    total_tokens: int
    total_cost: float
    avg_latency_ms: float
    success_rate: float

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Analytics":
        return cls(
            total_requests=data["total_requests"],
            total_tokens=data["total_tokens"],
            total_cost=data["total_cost"],
            avg_latency_ms=data["avg_latency_ms"],
            success_rate=data["success_rate"],
        )


class TSMError(Exception):
    """Base exception for TSM SDK."""

    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[Dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class AuthenticationError(TSMError):
    """Authentication failed."""
    pass


class RateLimitError(TSMError):
    """Rate limit exceeded."""
    pass


class QuotaExceededError(TSMError):
    """Quota exceeded."""
    pass


class TSMClient:
    """
    TSM Platform client.

    Main interface for interacting with TSM API.

    Example:
        client = TSMClient(api_key="your-api-key")
        response = await client.execute("What is AI?")
        print(response.output)
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.tsm-platform.com",
        timeout: int = 30,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def _ensure_session(self):
        """Ensure aiohttp session exists."""
        if self._session is None or self._session.closed:
            headers = {
                "X-API-Key": self.api_key,
                "Content-Type": "application/json",
                "User-Agent": "TSM-Python-SDK/1.0.0",
            }
            self._session = aiohttp.ClientSession(
                headers=headers,
                timeout=self.timeout,
            )

    async def close(self):
        """Close the client session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _request(
        self,
        method: str,
        path: str,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Make HTTP request to API."""
        await self._ensure_session()

        url = f"{self.base_url}{path}"

        async with self._session.request(method, url, json=json_data, params=params) as response:
            data = await response.json()

            if response.status >= 400:
                error_msg = data.get("error", "Unknown error")

                if response.status == 401:
                    raise AuthenticationError(error_msg, response.status, data)
                elif response.status == 429:
                    raise RateLimitError(error_msg, response.status, data)
                elif response.status == 402:
                    raise QuotaExceededError(error_msg, response.status, data)
                else:
                    raise TSMError(error_msg, response.status, data)

            return data

    async def execute(
        self,
        prompt: str,
        options: Optional[ExecuteOptions] = None,
    ) -> Response:
        """
        Execute AI model with prompt.

        Args:
            prompt: Input prompt
            options: Execution options

        Returns:
            Response object

        Raises:
            AuthenticationError: Invalid API key
            RateLimitError: Rate limit exceeded
            QuotaExceededError: Quota exceeded
        """
        opts = options or ExecuteOptions()

        payload = {
            "prompt": prompt,
            "model": opts.model,
            "provider": opts.provider.value if opts.provider else None,
            "temperature": opts.temperature,
            "max_tokens": opts.max_tokens,
            "stream": opts.stream,
            "metadata": opts.metadata,
        }

        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}

        data = await self._request("POST", "/api/execute", json_data=payload)
        return Response.from_dict(data)

    async def execute_stream(
        self,
        prompt: str,
        options: Optional[ExecuteOptions] = None,
    ) -> AsyncIterator[StreamChunk]:
        """
        Execute AI model with streaming response.

        Args:
            prompt: Input prompt
            options: Execution options

        Yields:
            StreamChunk objects
        """
        opts = options or ExecuteOptions()
        opts.stream = True

        await self._ensure_session()

        payload = {
            "prompt": prompt,
            "model": opts.model,
            "provider": opts.provider.value if opts.provider else None,
            "temperature": opts.temperature,
            "max_tokens": opts.max_tokens,
            "stream": True,
            "metadata": opts.metadata,
        }

        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}

        url = f"{self.base_url}/api/execute"

        async with self._session.post(url, json=payload) as response:
            if response.status >= 400:
                data = await response.json()
                error_msg = data.get("error", "Unknown error")
                raise TSMError(error_msg, response.status, data)

            async for line in response.content:
                if line:
                    line_str = line.decode('utf-8').strip()
                    if line_str.startswith("data: "):
                        json_str = line_str[6:]
                        if json_str == "[DONE]":
                            break

                        chunk_data = json.loads(json_str)
                        yield StreamChunk(
                            chunk_id=chunk_data["chunk_id"],
                            content=chunk_data["content"],
                            is_final=chunk_data.get("is_final", False),
                            metadata=chunk_data.get("metadata", {}),
                        )

    async def add_document(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Document:
        """Add document to memory store."""
        payload = {
            "content": content,
            "metadata": metadata or {},
        }

        data = await self._request("POST", "/api/documents", json_data=payload)
        return Document.from_dict(data)

    async def search_documents(
        self,
        query: str,
        top_k: int = 5,
    ) -> List[Document]:
        """Search documents."""
        params = {
            "query": query,
            "top_k": top_k,
        }

        data = await self._request("GET", "/api/documents/search", params=params)
        return [Document.from_dict(doc) for doc in data["documents"]]

    async def delete_document(self, document_id: str) -> bool:
        """Delete a document."""
        await self._request("DELETE", f"/api/documents/{document_id}")
        return True

    async def list_models(self) -> List[Model]:
        """List available models."""
        data = await self._request("GET", "/api/models")
        return [Model.from_dict(model) for model in data["models"]]

    async def get_analytics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Analytics:
        """Get usage analytics."""
        params = {}
        if start_date:
            params["start_date"] = start_date.isoformat()
        if end_date:
            params["end_date"] = end_date.isoformat()

        data = await self._request("GET", "/api/analytics", params=params)
        return Analytics.from_dict(data)

    async def clear_cache(self) -> bool:
        """Clear cache."""
        await self._request("POST", "/api/cache/clear")
        return True

    async def health_check(self) -> Dict[str, Any]:
        """Check API health."""
        return await self._request("GET", "/health")


# Synchronous wrapper for convenience
class TSMClientSync:
    """
    Synchronous wrapper for TSMClient.

    For use in non-async code.

    Example:
        client = TSMClientSync(api_key="your-api-key")
        response = client.execute("What is AI?")
        print(response.output)
    """

    def __init__(self, api_key: str, base_url: str = "https://api.tsm-platform.com", timeout: int = 30):
        self._async_client = TSMClient(api_key, base_url, timeout)

    def _run_async(self, coro):
        """Run async coroutine in new event loop."""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    def execute(self, prompt: str, options: Optional[ExecuteOptions] = None) -> Response:
        """Execute AI model (synchronous)."""
        return self._run_async(self._async_client.execute(prompt, options))

    def add_document(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> Document:
        """Add document (synchronous)."""
        return self._run_async(self._async_client.add_document(content, metadata))

    def search_documents(self, query: str, top_k: int = 5) -> List[Document]:
        """Search documents (synchronous)."""
        return self._run_async(self._async_client.search_documents(query, top_k))

    def delete_document(self, document_id: str) -> bool:
        """Delete document (synchronous)."""
        return self._run_async(self._async_client.delete_document(document_id))

    def list_models(self) -> List[Model]:
        """List models (synchronous)."""
        return self._run_async(self._async_client.list_models())

    def get_analytics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Analytics:
        """Get analytics (synchronous)."""
        return self._run_async(self._async_client.get_analytics(start_date, end_date))

    def clear_cache(self) -> bool:
        """Clear cache (synchronous)."""
        return self._run_async(self._async_client.clear_cache())

    def health_check(self) -> Dict[str, Any]:
        """Health check (synchronous)."""
        return self._run_async(self._async_client.health_check())

    def close(self):
        """Close client."""
        self._run_async(self._async_client.close())


__all__ = [
    "TSMClient",
    "TSMClientSync",
    "ExecuteOptions",
    "Response",
    "StreamChunk",
    "Document",
    "Model",
    "Analytics",
    "ModelProvider",
    "TSMError",
    "AuthenticationError",
    "RateLimitError",
    "QuotaExceededError",
]
