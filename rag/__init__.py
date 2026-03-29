"""
Advanced RAG (Retrieval Augmented Generation)
==============================================

Enhanced RAG with embedding-based semantic search and hybrid retrieval.
"""

from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import math
import logging

logger = logging.getLogger(__name__)


@dataclass
class Document:
    """A document in the knowledge base."""
    doc_id: str
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def get_text_chunks(self, chunk_size: int = 512) -> List[str]:
        """Split document into chunks."""
        words = self.content.split()
        chunks = []

        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i:i + chunk_size])
            chunks.append(chunk)

        return chunks


@dataclass
class SearchResult:
    """A search result."""
    document: Document
    score: float
    rank: int
    method: str  # "semantic", "keyword", "hybrid"
    highlights: List[str] = field(default_factory=list)


class EmbeddingProvider:
    """
    Abstract embedding provider.

    In production, integrate with:
    - OpenAI embeddings
    - Sentence Transformers
    - Cohere embeddings
    - Custom fine-tuned models
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize embedding provider.

        Args:
            model_name: Embedding model name
        """
        self.model_name = model_name
        self.embedding_dim = 384  # Placeholder dimension

        logger.info(f"EmbeddingProvider initialized (model={model_name})")

    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for text.

        Args:
            text: Input text

        Returns:
            Embedding vector

        Note: This is a placeholder. In production, use actual embedding model.
        """
        # Placeholder: Generate pseudo-embedding based on text hash
        # In production, use actual model like sentence-transformers
        import hashlib
        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)

        # Generate deterministic pseudo-random embedding
        embedding = []
        for i in range(self.embedding_dim):
            val = math.sin(hash_val + i) * math.cos(hash_val - i)
            embedding.append(val)

        # Normalize
        norm = math.sqrt(sum(x*x for x in embedding))
        if norm > 0:
            embedding = [x / norm for x in embedding]

        return embedding

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of input texts

        Returns:
            List of embedding vectors
        """
        embeddings = []
        for text in texts:
            embedding = await self.embed_text(text)
            embeddings.append(embedding)

        return embeddings


class VectorIndex:
    """
    Vector index for semantic search.

    In production, use:
    - Pinecone
    - Weaviate
    - Chroma
    - FAISS
    - Milvus
    """

    def __init__(self, embedding_provider: EmbeddingProvider):
        """
        Initialize vector index.

        Args:
            embedding_provider: Embedding provider
        """
        self.embedding_provider = embedding_provider
        self.documents: Dict[str, Document] = {}
        self.index: List[Tuple[str, List[float]]] = []  # (doc_id, embedding)

        logger.info("VectorIndex initialized")

    async def add_document(self, document: Document):
        """
        Add document to index.

        Args:
            document: Document to add
        """
        # Generate embedding if not provided
        if document.embedding is None:
            document.embedding = await self.embedding_provider.embed_text(
                document.content
            )

        # Store document
        self.documents[document.doc_id] = document

        # Add to index
        self.index.append((document.doc_id, document.embedding))

        logger.debug(f"Added document to index: {document.doc_id}")

    async def add_batch(self, documents: List[Document]):
        """Add multiple documents."""
        for doc in documents:
            await self.add_document(doc)

    def remove_document(self, doc_id: str):
        """Remove document from index."""
        if doc_id in self.documents:
            del self.documents[doc_id]

        self.index = [
            (did, emb) for did, emb in self.index
            if did != doc_id
        ]

        logger.debug(f"Removed document from index: {doc_id}")

    async def search(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        Semantic search.

        Args:
            query: Search query
            top_k: Number of results
            filter_metadata: Optional metadata filters

        Returns:
            List of search results
        """
        # Generate query embedding
        query_embedding = await self.embedding_provider.embed_text(query)

        # Calculate similarities
        similarities = []
        for doc_id, doc_embedding in self.index:
            doc = self.documents[doc_id]

            # Apply metadata filters
            if filter_metadata:
                if not all(
                    doc.metadata.get(k) == v
                    for k, v in filter_metadata.items()
                ):
                    continue

            # Cosine similarity
            similarity = self._cosine_similarity(query_embedding, doc_embedding)
            similarities.append((doc_id, similarity))

        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)

        # Build results
        results = []
        for rank, (doc_id, score) in enumerate(similarities[:top_k], 1):
            doc = self.documents[doc_id]

            result = SearchResult(
                document=doc,
                score=score,
                rank=rank,
                method="semantic"
            )
            results.append(result)

        return results

    def _cosine_similarity(
        self,
        vec1: List[float],
        vec2: List[float]
    ) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        return {
            "total_documents": len(self.documents),
            "index_size": len(self.index),
            "embedding_dim": self.embedding_provider.embedding_dim,
        }


class KeywordIndex:
    """
    Keyword-based inverted index for BM25 search.

    Traditional keyword search for hybrid retrieval.
    """

    def __init__(self):
        """Initialize keyword index."""
        self.documents: Dict[str, Document] = {}
        self.inverted_index: Dict[str, List[str]] = defaultdict(list)
        self.doc_lengths: Dict[str, int] = {}
        self.avg_doc_length: float = 0.0

        logger.info("KeywordIndex initialized")

    def add_document(self, document: Document):
        """Add document to keyword index."""
        # Store document
        self.documents[document.doc_id] = document

        # Tokenize
        tokens = self._tokenize(document.content)

        # Update inverted index
        for token in set(tokens):
            self.inverted_index[token].append(document.doc_id)

        # Track document length
        self.doc_lengths[document.doc_id] = len(tokens)

        # Update average doc length
        self._update_avg_length()

        logger.debug(f"Added document to keyword index: {document.doc_id}")

    def remove_document(self, doc_id: str):
        """Remove document from keyword index."""
        if doc_id not in self.documents:
            return

        # Remove from inverted index
        for token_docs in self.inverted_index.values():
            if doc_id in token_docs:
                token_docs.remove(doc_id)

        # Remove document
        del self.documents[doc_id]
        if doc_id in self.doc_lengths:
            del self.doc_lengths[doc_id]

        # Update average
        self._update_avg_length()

    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        BM25 keyword search.

        Args:
            query: Search query
            top_k: Number of results
            filter_metadata: Optional metadata filters

        Returns:
            List of search results
        """
        # Tokenize query
        query_tokens = self._tokenize(query)

        # Calculate BM25 scores
        scores = {}
        for token in query_tokens:
            if token not in self.inverted_index:
                continue

            # Get documents containing token
            doc_ids = self.inverted_index[token]

            for doc_id in doc_ids:
                doc = self.documents[doc_id]

                # Apply metadata filters
                if filter_metadata:
                    if not all(
                        doc.metadata.get(k) == v
                        for k, v in filter_metadata.items()
                    ):
                        continue

                # Calculate BM25 score
                score = self._bm25_score(
                    token,
                    doc_id,
                    query_tokens
                )

                if doc_id not in scores:
                    scores[doc_id] = 0.0
                scores[doc_id] += score

        # Sort by score
        sorted_docs = sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        # Build results
        results = []
        for rank, (doc_id, score) in enumerate(sorted_docs[:top_k], 1):
            doc = self.documents[doc_id]

            # Extract highlights
            highlights = self._extract_highlights(doc.content, query_tokens)

            result = SearchResult(
                document=doc,
                score=score,
                rank=rank,
                method="keyword",
                highlights=highlights
            )
            results.append(result)

        return results

    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization."""
        # Lowercase and split
        tokens = text.lower().split()

        # Remove punctuation
        tokens = [
            ''.join(c for c in token if c.isalnum())
            for token in tokens
        ]

        # Remove empty
        tokens = [t for t in tokens if t]

        return tokens

    def _bm25_score(
        self,
        term: str,
        doc_id: str,
        query_tokens: List[str],
        k1: float = 1.5,
        b: float = 0.75
    ) -> float:
        """Calculate BM25 score for term in document."""
        # Term frequency in document
        doc_tokens = self._tokenize(self.documents[doc_id].content)
        tf = doc_tokens.count(term)

        # Document frequency
        df = len(self.inverted_index[term])

        # Inverse document frequency
        N = len(self.documents)
        idf = math.log((N - df + 0.5) / (df + 0.5) + 1.0)

        # Document length normalization
        doc_len = self.doc_lengths[doc_id]
        norm = 1 - b + b * (doc_len / self.avg_doc_length)

        # BM25 score
        score = idf * (tf * (k1 + 1)) / (tf + k1 * norm)

        return score

    def _update_avg_length(self):
        """Update average document length."""
        if self.doc_lengths:
            self.avg_doc_length = sum(self.doc_lengths.values()) / len(self.doc_lengths)
        else:
            self.avg_doc_length = 0.0

    def _extract_highlights(
        self,
        text: str,
        query_tokens: List[str],
        context_words: int = 5
    ) -> List[str]:
        """Extract text highlights around query terms."""
        words = text.split()
        highlights = []

        for i, word in enumerate(words):
            word_clean = ''.join(c for c in word.lower() if c.isalnum())

            if word_clean in query_tokens:
                # Extract context
                start = max(0, i - context_words)
                end = min(len(words), i + context_words + 1)

                highlight = " ".join(words[start:end])
                if start > 0:
                    highlight = "..." + highlight
                if end < len(words):
                    highlight = highlight + "..."

                highlights.append(highlight)

        return highlights[:3]  # Max 3 highlights


class HybridRAG:
    """
    Hybrid RAG combining semantic and keyword search.

    Uses both vector similarity and BM25 for best results.
    """

    def __init__(
        self,
        embedding_provider: Optional[EmbeddingProvider] = None,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3
    ):
        """
        Initialize hybrid RAG.

        Args:
            embedding_provider: Embedding provider (creates default if None)
            semantic_weight: Weight for semantic search
            keyword_weight: Weight for keyword search
        """
        self.embedding_provider = embedding_provider or EmbeddingProvider()
        self.semantic_weight = semantic_weight
        self.keyword_weight = keyword_weight

        self.vector_index = VectorIndex(self.embedding_provider)
        self.keyword_index = KeywordIndex()

        logger.info(
            f"HybridRAG initialized "
            f"(semantic={semantic_weight}, keyword={keyword_weight})"
        )

    async def add_document(self, document: Document):
        """Add document to both indexes."""
        await self.vector_index.add_document(document)
        self.keyword_index.add_document(document)

    async def add_batch(self, documents: List[Document]):
        """Add multiple documents."""
        for doc in documents:
            await self.add_document(doc)

    def remove_document(self, doc_id: str):
        """Remove document from both indexes."""
        self.vector_index.remove_document(doc_id)
        self.keyword_index.remove_document(doc_id)

    async def search(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
        use_semantic: bool = True,
        use_keyword: bool = True
    ) -> List[SearchResult]:
        """
        Hybrid search combining semantic and keyword methods.

        Args:
            query: Search query
            top_k: Number of results
            filter_metadata: Optional metadata filters
            use_semantic: Use semantic search
            use_keyword: Use keyword search

        Returns:
            List of search results
        """
        # Get results from both methods
        semantic_results = []
        keyword_results = []

        if use_semantic:
            semantic_results = await self.vector_index.search(
                query,
                top_k=top_k * 2,  # Get more for fusion
                filter_metadata=filter_metadata
            )

        if use_keyword:
            keyword_results = self.keyword_index.search(
                query,
                top_k=top_k * 2,
                filter_metadata=filter_metadata
            )

        # Combine scores using Reciprocal Rank Fusion
        combined_scores = {}

        # Add semantic scores
        for result in semantic_results:
            doc_id = result.document.doc_id
            rr_score = 1.0 / (result.rank + 60)  # RRF constant = 60
            combined_scores[doc_id] = self.semantic_weight * rr_score

        # Add keyword scores
        for result in keyword_results:
            doc_id = result.document.doc_id
            rr_score = 1.0 / (result.rank + 60)

            if doc_id in combined_scores:
                combined_scores[doc_id] += self.keyword_weight * rr_score
            else:
                combined_scores[doc_id] = self.keyword_weight * rr_score

        # Sort by combined score
        sorted_docs = sorted(
            combined_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        # Build final results
        results = []
        for rank, (doc_id, score) in enumerate(sorted_docs[:top_k], 1):
            doc = (
                self.vector_index.documents.get(doc_id) or
                self.keyword_index.documents.get(doc_id)
            )

            if not doc:
                continue

            # Get highlights from keyword search
            highlights = []
            for kr in keyword_results:
                if kr.document.doc_id == doc_id:
                    highlights = kr.highlights
                    break

            result = SearchResult(
                document=doc,
                score=score,
                rank=rank,
                method="hybrid",
                highlights=highlights
            )
            results.append(result)

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get RAG statistics."""
        return {
            "vector_index": self.vector_index.get_stats(),
            "keyword_index": {
                "total_documents": len(self.keyword_index.documents),
                "unique_terms": len(self.keyword_index.inverted_index),
                "avg_doc_length": self.keyword_index.avg_doc_length,
            },
            "weights": {
                "semantic": self.semantic_weight,
                "keyword": self.keyword_weight,
            }
        }


# Global RAG instance
rag = HybridRAG()
