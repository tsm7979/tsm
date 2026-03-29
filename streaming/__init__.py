"""
Streaming Response Support
===========================

Server-Sent Events (SSE) and streaming responses for real-time output.
"""

from typing import AsyncIterator, Dict, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
import asyncio
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class StreamChunk:
    """A chunk of streaming data."""
    chunk_id: str
    content: str
    chunk_index: int
    is_final: bool = False
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "chunk_id": self.chunk_id,
            "content": self.content,
            "chunk_index": self.chunk_index,
            "is_final": self.is_final,
            "metadata": self.metadata or {},
        }

    def to_sse(self) -> str:
        """Convert to SSE format."""
        data = json.dumps(self.to_dict())
        return f"data: {data}\n\n"


class StreamBuffer:
    """
    Buffer for streaming responses.

    Accumulates chunks and manages backpressure.
    """

    def __init__(self, max_size: int = 100):
        """
        Initialize stream buffer.

        Args:
            max_size: Maximum buffer size
        """
        self.max_size = max_size
        self.buffer: asyncio.Queue = asyncio.Queue(maxsize=max_size)
        self.closed = False

        logger.debug(f"StreamBuffer initialized (max_size={max_size})")

    async def write(self, chunk: StreamChunk):
        """
        Write chunk to buffer.

        Args:
            chunk: Chunk to write
        """
        if self.closed:
            raise RuntimeError("Stream closed")

        await self.buffer.put(chunk)

    async def read(self) -> Optional[StreamChunk]:
        """
        Read chunk from buffer.

        Returns:
            Next chunk or None if closed
        """
        try:
            chunk = await asyncio.wait_for(
                self.buffer.get(),
                timeout=1.0
            )
            return chunk
        except asyncio.TimeoutError:
            if self.closed:
                return None
            raise

    async def read_all(self) -> AsyncIterator[StreamChunk]:
        """
        Read all chunks until stream closes.

        Yields:
            Stream chunks
        """
        while True:
            try:
                chunk = await self.read()
                if chunk is None:
                    break
                yield chunk

                if chunk.is_final:
                    break

            except asyncio.TimeoutError:
                if self.closed:
                    break
                continue

    def close(self):
        """Close stream buffer."""
        self.closed = True

    def is_closed(self) -> bool:
        """Check if buffer is closed."""
        return self.closed

    def size(self) -> int:
        """Get current buffer size."""
        return self.buffer.qsize()


class StreamingResponse:
    """
    Streaming response manager.

    Handles streaming output from LLMs and other async sources.
    """

    def __init__(
        self,
        request_id: str,
        buffer_size: int = 100
    ):
        """
        Initialize streaming response.

        Args:
            request_id: Request identifier
            buffer_size: Stream buffer size
        """
        self.request_id = request_id
        self.buffer = StreamBuffer(max_size=buffer_size)
        self.chunk_count = 0
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None

        logger.info(f"StreamingResponse created: {request_id}")

    async def write_chunk(
        self,
        content: str,
        is_final: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Write a chunk to the stream.

        Args:
            content: Chunk content
            is_final: Whether this is the final chunk
            metadata: Optional chunk metadata
        """
        if self.started_at is None:
            self.started_at = datetime.utcnow()

        chunk = StreamChunk(
            chunk_id=f"{self.request_id}-{self.chunk_count}",
            content=content,
            chunk_index=self.chunk_count,
            is_final=is_final,
            metadata=metadata
        )

        await self.buffer.write(chunk)
        self.chunk_count += 1

        if is_final:
            self.completed_at = datetime.utcnow()
            self.buffer.close()

        logger.debug(
            f"Wrote chunk {self.chunk_count} "
            f"(final={is_final}, size={len(content)})"
        )

    async def stream(self) -> AsyncIterator[StreamChunk]:
        """
        Stream all chunks.

        Yields:
            Stream chunks
        """
        async for chunk in self.buffer.read_all():
            yield chunk

    async def stream_sse(self) -> AsyncIterator[str]:
        """
        Stream in SSE format.

        Yields:
            SSE formatted chunks
        """
        async for chunk in self.stream():
            yield chunk.to_sse()

    async def collect(self) -> str:
        """
        Collect all chunks into a single string.

        Returns:
            Complete response text
        """
        chunks = []
        async for chunk in self.stream():
            chunks.append(chunk.content)

        return "".join(chunks)

    def get_stats(self) -> Dict[str, Any]:
        """Get streaming statistics."""
        duration = None
        if self.started_at and self.completed_at:
            duration = (self.completed_at - self.started_at).total_seconds()

        return {
            "request_id": self.request_id,
            "chunk_count": self.chunk_count,
            "buffer_size": self.buffer.size(),
            "closed": self.buffer.is_closed(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": duration,
        }


class StreamMultiplexer:
    """
    Multiplex multiple streams into one.

    Useful for combining outputs from multiple sources.
    """

    def __init__(self):
        """Initialize stream multiplexer."""
        self.streams: Dict[str, AsyncIterator[StreamChunk]] = {}
        self.output_buffer = StreamBuffer()

        logger.debug("StreamMultiplexer initialized")

    def add_stream(self, stream_id: str, stream: AsyncIterator[StreamChunk]):
        """
        Add a stream to multiplex.

        Args:
            stream_id: Stream identifier
            stream: Stream to add
        """
        self.streams[stream_id] = stream
        logger.debug(f"Added stream: {stream_id}")

    async def multiplex(self) -> AsyncIterator[StreamChunk]:
        """
        Multiplex all streams.

        Yields:
            Combined stream chunks
        """
        tasks = []

        # Create tasks for each stream
        for stream_id, stream in self.streams.items():
            task = asyncio.create_task(
                self._read_stream(stream_id, stream)
            )
            tasks.append(task)

        # Wait for all streams to complete
        await asyncio.gather(*tasks)

        # Close output buffer
        self.output_buffer.close()

        # Yield all buffered chunks
        async for chunk in self.output_buffer.read_all():
            yield chunk

    async def _read_stream(self, stream_id: str, stream: AsyncIterator[StreamChunk]):
        """Read from a single stream and buffer."""
        async for chunk in stream:
            # Tag chunk with stream ID
            if chunk.metadata is None:
                chunk.metadata = {}
            chunk.metadata["stream_id"] = stream_id

            await self.output_buffer.write(chunk)


class StreamRateLimiter:
    """
    Rate limiter for streaming responses.

    Throttles output speed to avoid overwhelming clients.
    """

    def __init__(
        self,
        chunks_per_second: float = 10.0,
        burst_size: int = 5
    ):
        """
        Initialize stream rate limiter.

        Args:
            chunks_per_second: Chunk rate limit
            burst_size: Burst capacity
        """
        self.chunks_per_second = chunks_per_second
        self.burst_size = burst_size
        self.tokens = float(burst_size)
        self.last_update = asyncio.get_event_loop().time()

        logger.debug(
            f"StreamRateLimiter initialized "
            f"(rate={chunks_per_second}/s, burst={burst_size})"
        )

    async def acquire(self):
        """Acquire permission to send a chunk."""
        while True:
            # Refill tokens
            now = asyncio.get_event_loop().time()
            elapsed = now - self.last_update
            self.tokens = min(
                self.burst_size,
                self.tokens + (self.chunks_per_second * elapsed)
            )
            self.last_update = now

            # Try to consume token
            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return

            # Wait for refill
            wait_time = (1.0 - self.tokens) / self.chunks_per_second
            await asyncio.sleep(wait_time)

    async def throttle_stream(
        self,
        stream: AsyncIterator[StreamChunk]
    ) -> AsyncIterator[StreamChunk]:
        """
        Apply rate limiting to stream.

        Args:
            stream: Input stream

        Yields:
            Throttled chunks
        """
        async for chunk in stream:
            await self.acquire()
            yield chunk


class StreamTransformer:
    """
    Transform streaming data.

    Apply transformations to chunks as they stream.
    """

    def __init__(self, transform_fn: Callable[[str], str]):
        """
        Initialize stream transformer.

        Args:
            transform_fn: Transformation function
        """
        self.transform_fn = transform_fn

    async def transform(
        self,
        stream: AsyncIterator[StreamChunk]
    ) -> AsyncIterator[StreamChunk]:
        """
        Transform stream.

        Args:
            stream: Input stream

        Yields:
            Transformed chunks
        """
        async for chunk in stream:
            # Apply transformation
            transformed_content = self.transform_fn(chunk.content)

            # Create new chunk
            transformed_chunk = StreamChunk(
                chunk_id=chunk.chunk_id,
                content=transformed_content,
                chunk_index=chunk.chunk_index,
                is_final=chunk.is_final,
                metadata=chunk.metadata
            )

            yield transformed_chunk


class StreamAggregator:
    """
    Aggregate streaming chunks by time windows.

    Useful for reducing chunk frequency.
    """

    def __init__(self, window_seconds: float = 0.5):
        """
        Initialize stream aggregator.

        Args:
            window_seconds: Aggregation window
        """
        self.window_seconds = window_seconds

    async def aggregate(
        self,
        stream: AsyncIterator[StreamChunk]
    ) -> AsyncIterator[StreamChunk]:
        """
        Aggregate stream chunks.

        Args:
            stream: Input stream

        Yields:
            Aggregated chunks
        """
        buffer = []
        last_flush = asyncio.get_event_loop().time()

        async for chunk in stream:
            buffer.append(chunk)

            now = asyncio.get_event_loop().time()
            should_flush = (
                chunk.is_final or
                (now - last_flush) >= self.window_seconds
            )

            if should_flush and buffer:
                # Combine buffered chunks
                combined_content = "".join(c.content for c in buffer)

                aggregated = StreamChunk(
                    chunk_id=buffer[0].chunk_id,
                    content=combined_content,
                    chunk_index=buffer[0].chunk_index,
                    is_final=chunk.is_final,
                    metadata=buffer[0].metadata
                )

                yield aggregated

                buffer.clear()
                last_flush = now


# Utility functions

async def stream_from_iterable(
    items: list,
    chunk_size: int = 1,
    delay_seconds: float = 0.1
) -> AsyncIterator[StreamChunk]:
    """
    Create stream from iterable.

    Args:
        items: Items to stream
        chunk_size: Items per chunk
        delay_seconds: Delay between chunks

    Yields:
        Stream chunks
    """
    chunk_index = 0

    for i in range(0, len(items), chunk_size):
        chunk_items = items[i:i + chunk_size]
        content = "".join(str(item) for item in chunk_items)

        is_final = (i + chunk_size) >= len(items)

        chunk = StreamChunk(
            chunk_id=f"chunk-{chunk_index}",
            content=content,
            chunk_index=chunk_index,
            is_final=is_final
        )

        yield chunk

        chunk_index += 1

        if not is_final:
            await asyncio.sleep(delay_seconds)


async def stream_from_generator(
    generator: AsyncIterator[str],
    chunk_prefix: str = "chunk"
) -> AsyncIterator[StreamChunk]:
    """
    Create stream from async generator.

    Args:
        generator: Async string generator
        chunk_prefix: Chunk ID prefix

    Yields:
        Stream chunks
    """
    chunk_index = 0

    async for content in generator:
        chunk = StreamChunk(
            chunk_id=f"{chunk_prefix}-{chunk_index}",
            content=content,
            chunk_index=chunk_index,
            is_final=False  # Generator doesn't know when it's done
        )

        yield chunk
        chunk_index += 1
