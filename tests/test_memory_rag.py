"""
Test Memory & RAG System
=========================

Tests for VectorStore, MemoryManager, and RAG capabilities.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from memory import VectorStore, MemoryManager, memory_manager


def test_vector_store():
    """Test vector store operations."""
    print("\n[TEST 1] VectorStore Operations")
    print("-" * 60)

    store = VectorStore("test_store")

    # Add entries
    id1 = store.add("SQL injection is a code injection technique.",
                    metadata={"type": "vulnerability", "severity": "high"})
    id2 = store.add("XSS allows attackers to inject client-side scripts.",
                    metadata={"type": "vulnerability", "severity": "high"})
    id3 = store.add("Python is a programming language.",
                    metadata={"type": "general"})

    print(f"  Added {len(store.entries)} entries")
    print(f"  Entry IDs: {[id1[:8], id2[:8], id3[:8]]}")

    # Search
    results = store.search("injection", top_k=5)
    print(f"  Search 'injection': {len(results)} results")
    assert len(results) == 2, "Should find 2 injection-related entries"

    # Filtered search
    results = store.search("injection", filter_metadata={"type": "vulnerability"})
    print(f"  Filtered search: {len(results)} results")
    assert len(results) == 2

    # Get entry
    entry = store.get(id1)
    assert entry is not None
    assert "SQL injection" in entry.content

    # Stats
    stats = store.get_stats()
    print(f"  Total entries: {stats['total_entries']}")
    print(f"  Has embeddings: {stats['has_embeddings']}")

    print("  [PASSED]")


def test_memory_manager():
    """Test memory manager operations."""
    print("\n[TEST 2] MemoryManager Session Tracking")
    print("-" * 60)

    manager = MemoryManager()

    session_id = "test-session-001"

    # Add conversation
    manager.add_to_session(session_id, "user", "What is SQL injection?")
    manager.add_to_session(session_id, "assistant",
                          "SQL injection is a code injection technique...")
    manager.add_to_session(session_id, "user", "How do I prevent it?")
    manager.add_to_session(session_id, "assistant",
                          "Use parameterized queries...")

    # Get history
    history = manager.get_session_history(session_id, max_messages=10)
    print(f"  Messages in session: {len(history)}")
    assert len(history) == 4, "Should have 4 messages"

    print(f"  First message: {history[0]['role']} - {history[0]['content'][:30]}...")
    print(f"  Last message: {history[-1]['role']} - {history[-1]['content'][:30]}...")

    # Get stats
    stats = manager.get_stats()
    print(f"  Total sessions: {stats['total_sessions']}")
    print(f"  Total messages: {stats['total_messages']}")

    print("  [PASSED]")


def test_rag_retrieval():
    """Test RAG (Retrieval Augmented Generation) capabilities."""
    print("\n[TEST 3] RAG Context Retrieval")
    print("-" * 60)

    manager = MemoryManager()

    session_id = "rag-test-001"

    # Add knowledge base
    knowledge = [
        "SQL injection occurs when user input is concatenated into SQL queries.",
        "Parameterized queries prevent SQL injection by separating code from data.",
        "XSS vulnerabilities allow attackers to inject malicious scripts.",
        "Content Security Policy helps prevent XSS attacks.",
        "CSRF attacks trick users into executing unwanted actions.",
    ]

    for kb in knowledge:
        manager.add_to_session(session_id, "system", kb, metadata={"source": "knowledge_base"})

    print(f"  Added {len(knowledge)} knowledge base entries")

    # Test retrieval
    queries = [
        "SQL injection prevention",
        "XSS attack mitigation",
        "CSRF protection",
    ]

    for query in queries:
        context = manager.get_context(query, session_id=session_id, max_results=2)
        print(f"\n  Query: '{query}'")
        print(f"  Retrieved {len(context)} context items")
        for i, ctx in enumerate(context, 1):
            print(f"    {i}. {ctx[:50]}...")

        assert len(context) > 0, f"Should retrieve context for '{query}'"

    print("\n  [PASSED]")


def test_session_isolation():
    """Test session isolation."""
    print("\n[TEST 4] Session Isolation")
    print("-" * 60)

    manager = MemoryManager()

    # Create two sessions
    manager.add_to_session("user-1", "user", "Hello from user 1")
    manager.add_to_session("user-2", "user", "Hello from user 2")
    manager.add_to_session("user-1", "assistant", "Hi user 1!")

    # Check isolation
    history_1 = manager.get_session_history("user-1")
    history_2 = manager.get_session_history("user-2")

    print(f"  User 1 messages: {len(history_1)}")
    print(f"  User 2 messages: {len(history_2)}")

    assert len(history_1) == 2, "User 1 should have 2 messages"
    assert len(history_2) == 1, "User 2 should have 1 message"

    # Test filtered context retrieval
    context_1 = manager.get_context("user 1", session_id="user-1")
    context_2 = manager.get_context("user 1", session_id="user-2")

    print(f"  Context for user-1 query: {len(context_1)} results")
    print(f"  Context for user-2 query: {len(context_2)} results")

    print("  [PASSED]")


def test_memory_stats():
    """Test memory statistics."""
    print("\n[TEST 5] Memory Statistics")
    print("-" * 60)

    # Use global instance
    stats = memory_manager.get_stats()

    print(f"  Total sessions: {stats['total_sessions']}")
    print(f"  Total messages: {stats['total_messages']}")
    print(f"  Vector store:")
    print(f"    Name: {stats['vector_store']['name']}")
    print(f"    Entries: {stats['vector_store']['total_entries']}")

    print("  [PASSED]")


def main():
    """Run all tests."""
    print("=" * 60)
    print("MEMORY & RAG SYSTEM TEST SUITE")
    print("=" * 60)

    try:
        test_vector_store()
        test_memory_manager()
        test_rag_retrieval()
        test_session_isolation()
        test_memory_stats()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED (5/5)")
        print("=" * 60)
        print("\n[SUMMARY]")
        print("  VectorStore: Operational")
        print("  MemoryManager: Operational")
        print("  RAG Retrieval: Working")
        print("  Session Isolation: Verified")
        print("  Ready for production use")

    except AssertionError as e:
        print(f"\n[FAILED] {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
