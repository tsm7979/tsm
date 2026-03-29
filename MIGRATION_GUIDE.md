# TSM Layer Migration Guide

**From:** Scattered repositories (SecOps-ai, APP, frontend, etc.)
**To:** Clean TSMv1 unified architecture
**Date:** March 28, 2026

---

## Overview

This guide documents the complete migration from multiple fragmented codebases into a single, production-ready AI Control Plane.

---

## Migration Status

### ✅ Phase 1: Foundation (COMPLETE)

**What's Done:**
1. ✅ Clean directory structure created
2. ✅ Gateway API built (`/gateway/api.py`)
3. ✅ Request pipeline orchestrator (`/gateway/pipeline.py`)
4. ✅ Firewall layer extracted (`/firewall/sanitizer.py`, `/firewall/classifier.py`)
5. ✅ All 12 layer stubs created
6. ✅ Project configuration (requirements.txt, pyproject.toml)
7. ✅ Comprehensive README

**What's Working:**
- `/health` endpoint
- Basic request flow through all layers
- PII detection and sanitization
- Risk classification
- Audit logging

---

## Source Directory Map

### Primary Extraction Targets

```
C:\Users\mymai\Desktop\
├── SecOps-ai\              ← MAIN SOURCE
│   ├── backend\src\core\   ← Core modules
│   ├── frontend\           ← Next.js app
│   └── data\               ← Workflow corpus
│
├── APP\                    ← Desktop prototypes
│   └── TSM99\
│
├── frontend\               ← Standalone experiments
│
├── git-workflow\           ← Git automation
│
├── TSM-Install-Test\       ← Desktop packages
│
└── TSMv1\                  ← NEW CLEAN WORKSPACE ✅
```

---

## Next Extraction Steps

### Phase 2A: Complete Router & Model Layer

**Priority:** P0 (Critical)

#### 1. Extract Poly-Orchestrator

**Source:**
```
C:\Users\mymai\Desktop\SecOps-ai\backend\src\core\llm\poly_orchestrator.py
```

**Destination:**
```
C:\Users\mymai\Desktop\TSMv1\router\orchestrator.py
```

**Steps:**
```bash
# Copy and refactor
cp SecOps-ai/backend/src/core/llm/poly_orchestrator.py TSMv1/router/orchestrator.py

# Update imports to use TSMv1 structure
# Integrate with decision_engine in router/__init__.py
```

#### 2. Extract Model Providers

**Source:**
```
SecOps-ai/backend/src\core\llm\model_providers\
├── base_provider.py
├── openai_provider.py
├── claude_provider.py
├── gemini_provider.py
└── local_provider.py
```

**Destination:**
```
TSMv1/models/providers/
```

**Steps:**
```bash
# Copy all provider files
cp -r SecOps-ai/backend/src/core/llm/model_providers/* TSMv1/models/providers/

# Update models/__init__.py to use real providers
# Implement ModelExecutor.call() with provider routing
```

**Expected Result:**
- Real model calls working
- Multi-provider support
- Fallback strategies

---

### Phase 2B: Extract Execution & Agentic Layer

**Priority:** P0 (Critical)

#### 1. Extract Execution Engine

**Source:**
```
SecOps-ai/backend/src/core/agentic\
├── execution_engine.py
├── agent_core.py
├── reasoning_loop.py
├── planner.py (if exists)
└── coordinator.py (if exists)
```

**Destination:**
```
TSMv1/execution/
├── engine.py          ← from execution_engine.py
├── agent.py           ← from agent_core.py
├── reasoning_loop.py
├── planner.py
└── coordinator.py
```

**Steps:**
```bash
# Copy execution modules
cp SecOps-ai/backend/src/core/agentic/execution_engine.py TSMv1/execution/engine.py
cp SecOps-ai/backend/src/core/agentic/reasoning_loop.py TSMv1/execution/
cp SecOps-ai/backend/src/core/agentic/agent_core.py TSMv1/execution/agent.py

# Refactor imports
# Integrate with ExecutionEngine in execution/__init__.py
```

---

### Phase 2C: Extract Trust & Audit Layer

**Priority:** P0 (Critical)

#### 1. Extract Immutable Trace

**Source:**
```
SecOps-ai/backend/src/core/audit/immutable_trace.py
SecOps-ai/backend/src/core/trust_ledger/ledger.py
```

**Destination:**
```
TSMv1/trust/
├── logger.py      ← from immutable_trace.py
├── ledger.py      ← from trust_ledger/ledger.py
├── replay.py      ← build new
└── verifier.py    ← build new
```

**Steps:**
```bash
cp SecOps-ai/backend/src/core/audit/immutable_trace.py TSMv1/trust/logger.py
cp SecOps-ai/backend/src/core/trust_ledger/ledger.py TSMv1/trust/

# Integrate with AuditLogger in trust/__init__.py
# Ensure writes to immutable JSONL file
```

---

### Phase 2D: Extract Simulation Layer

**Priority:** P1 (High)

#### 1. Extract Ghost Sim

**Source:**
```
SecOps-ai/backend/src/core/healing/ghost_sim.py
SecOps-ai/backend/src/core/simulation/mcts_engine.py (if exists)
```

**Destination:**
```
TSMv1/simulation/
├── ghost_sim.py
├── mcts_engine.py
└── risk_scorer.py
```

**Steps:**
```bash
cp SecOps-ai/backend/src/core/healing/ghost_sim.py TSMv1/simulation/
# Find and copy MCTS if it exists
# Integrate with GhostSimulator in simulation/__init__.py
```

---

### Phase 2E: Extract Memory Layer

**Priority:** P1 (High)

**Source:**
```
SecOps-ai/backend/src/core/memory\
├── semantic_store.py
├── episodic_store.py
└── policy_memory.py
```

**Destination:**
```
TSMv1/memory/
├── semantic_store.py
├── episodic_store.py
├── context_manager.py  ← build new
└── rag.py             ← build new
```

**Steps:**
```bash
cp SecOps-ai/backend/src/core/memory/semantic_store.py TSMv1/memory/
cp SecOps-ai/backend/src/core/memory/episodic_store.py TSMv1/memory/

# Integrate with ContextManager
# Build RAG system on top
```

---

### Phase 2F: Extract Policy Engine

**Priority:** P1 (High)

**Source:**
```
SecOps-ai/backend/src/core/compliance/policy_engine.py
SecOps-ai/backend/src/core/autonomy/policy_engine.py
```

**Destination:**
```
TSMv1/policy/
├── engine.py      ← merge both policy engines
├── rules.py       ← build rule system
├── compliance.py  ← compliance frameworks
└── approval.py    ← approval workflows
```

---

### Phase 2G: Build Tool System

**Priority:** P0 (Critical)

This is the strategic differentiator.

#### 1. Build Tool Registry

**New File:**
```
TSMv1/tools/registry.py
```

**Requirements:**
- Tool discovery from manifests
- Schema validation
- Permission checking
- Sandboxed execution

#### 2. Build Tool Compiler

**New File:**
```
TSMv1/tools/compiler.py
```

**Purpose:**
- Convert workflows → tool manifests
- Package tools with dependencies
- Version control

#### 3. Convert Security Playbooks

**Source:**
```
SecOps-ai/backend/src/core/learning/playbooks/
```

**Destination:**
```
TSMv1/tools/packs/security/
├── sql_injection_scan/
│   ├── manifest.json
│   ├── tool.py
│   └── schema.json
└── xss_detection/
    ├── manifest.json
    ├── tool.py
    └── schema.json
```

#### 4. Archive Non-Core Workflows

**Source:**
```
SecOps-ai/backend/data/workflow_corpus/
├── recipe_meal_plan/     → ARCHIVE
├── travel_recommendation/→ ARCHIVE
├── tetris_game/          → ARCHIVE
└── invest/               → CONVERT TO TOOL
```

**Destination:**
```
TSMv1/archive/workflows/
```

---

## Phase 3: Enterprise Features

### 3A: Database Layer

**Source:**
```
SecOps-ai/backend/src/db/models.py
SecOps-ai/backend/src/db/session.py
```

**Destination:**
```
TSMv1/db/
├── models.py
├── session.py
└── migrations/
```

**Note:** Only migrate essential models. Leave experimental tables behind.

---

### 3B: Frontend Migration

**Source:**
```
SecOps-ai/frontend/
├── app/
├── components/
└── hooks/
```

**Destination:**
```
TSMv1/web/
├── app/
├── components/
└── hooks/
```

**Strategy:**
- Copy only dashboard and core pages
- Remove marketing pages (keep in archive)
- Update API calls to use new gateway

---

### 3C: Enterprise Connectors

**Source:**
```
SecOps-ai/backend/src/integrations/
```

**Destination:**
```
TSMv1/connectors/
├── github.py
├── aws.py
├── kubernetes.py
└── database.py
```

---

## Phase 4: Network Layer (Future)

**Source:**
```
SecOps-ai/backend/src/core/network/
├── p2p_client.py
├── signal_protocol.py
```

**Destination:**
```
TSMv1/network/
├── node.py
├── protocol.py
├── mesh.py
└── packets.py
```

**Note:** This is P2. Focus on core runtime first.

---

## What to Archive (Not Migrate)

### 1. Desktop App
**Source:** `SecOps-ai/desktop-app/`, `APP/TSM99/`
**Reason:** Not core to platform
**Archive:** `TSMv1/archive/desktop/`

### 2. Training Pipeline
**Source:** `SecOps-ai/training/`
**Reason:** Separate product concern
**Archive:** `TSMv1/archive/training/`

### 3. Build Scripts
**Source:** `BUILD_*.bat`, installer scripts
**Reason:** Not needed for API-first platform
**Archive:** `TSMv1/archive/build-scripts/`

### 4. Random Workflows
**Source:** Recipes, travel, tetris, etc.
**Reason:** Not enterprise relevant
**Archive:** `TSMv1/archive/workflows/`

### 5. Experimental Features
**Source:** Half-built evolution, economics modules
**Reason:** Incomplete, dilutes focus
**Archive:** `TSMv1/archive/experimental/`

---

## Testing Strategy

### Test Each Layer

```bash
# Test firewall
pytest tests/unit/test_firewall.py

# Test router
pytest tests/unit/test_router.py

# Test execution
pytest tests/unit/test_execution.py

# Test end-to-end
pytest tests/e2e/test_pipeline.py
```

### Example E2E Test

```python
# tests/e2e/test_pipeline.py

async def test_full_pipeline():
    """Test complete request flow"""

    # Send request
    response = await client.post("/ai-proxy", json={
        "input": "My SSN is 123-45-6789. Analyze this."
    })

    # Verify PII redacted
    trace = await client.get(f"/audit/{response.json()['trace_id']}")
    assert "[SSN_REDACTED]" in trace["sanitized_input"]

    # Verify audit logged
    assert trace["timestamp"]
    assert trace["model_used"]
```

---

## Performance Targets

### Latency
- P50: <200ms
- P95: <500ms
- P99: <1000ms

### Throughput
- Min: 100 req/sec
- Target: 1000 req/sec

### Audit
- 100% request coverage
- <10ms logging overhead

---

## Deployment Checklist

### Before Production

- [ ] All P0 modules extracted
- [ ] End-to-end tests passing
- [ ] Load testing complete
- [ ] Security audit done
- [ ] Documentation complete
- [ ] Environment configs ready
- [ ] Monitoring setup
- [ ] Incident response plan

---

## Quick Commands

### Start Development Server

```bash
cd C:\Users\mymai\Desktop\TSMv1
pip install -r requirements.txt
uvicorn gateway.api:app --reload --port 8000
```

### Run Tests

```bash
pytest tests/ -v --cov
```

### Check Code Quality

```bash
black .
ruff check .
mypy .
```

### Build Docker Image

```bash
docker build -t tsm-layer:latest .
docker run -p 8000:8000 tsm-layer:latest
```

---

## Migration Timeline

### Week 1-2: Core Runtime (P0)
- ✅ Gateway, firewall, stubs (DONE)
- ⏳ Extract router & models
- ⏳ Extract execution engine
- ⏳ Extract trust layer

### Week 3-4: Tool System (P0)
- Build tool registry
- Build tool compiler
- Convert security playbooks
- Test tool execution

### Week 5-6: Enterprise Features (P1)
- Extract policy engine
- Extract memory layer
- Extract simulation
- Migrate database models

### Week 7-8: Frontend & Connectors (P1)
- Migrate Next.js frontend
- Build enterprise connectors
- Integration testing
- Performance tuning

---

## Success Criteria

### Technical
- [ ] All requests flow through gateway
- [ ] PII detection working
- [ ] Risk classification accurate
- [ ] Audit coverage 100%
- [ ] Tool execution working
- [ ] Latency <500ms P95

### Business
- [ ] Clear value proposition
- [ ] Demo-ready
- [ ] Documentation complete
- [ ] OSS-ready core
- [ ] Enterprise features identified

---

## Key Principles

### 1. Extract, Don't Rewrite
Copy working code. Refactor imports. Don't rebuild from scratch.

### 2. Archive, Don't Delete
Move non-core to /archive. May have value later.

### 3. Test Continuously
Don't migrate everything then test. Test each layer.

### 4. Focus on Core
Gateway → Firewall → Router → Execution → Trust → Tools

### 5. Ship Incrementally
Don't wait for perfection. Ship working core, iterate.

---

## Questions & Decisions

### Q: Keep desktop app?
**A:** Archive. Not core to platform.

### Q: Keep training pipeline?
**A:** Archive. Separate product concern.

### Q: Which workflows to keep?
**A:** Security playbooks only. Archive demos.

### Q: One repo or multiple?
**A:** One monorepo. Easier to manage.

### Q: OSS everything?
**A:** Core OSS. Enterprise features closed source.

---

## Next Immediate Steps

1. **Extract router** (C:\Users\mymai\Desktop\SecOps-ai\backend\src\core\llm\poly_orchestrator.py)
2. **Extract model providers** (model_providers/*)
3. **Extract execution engine** (agentic/execution_engine.py)
4. **Extract trust layer** (audit/immutable_trace.py)
5. **Test end-to-end flow**

---

**Goal:** Ship a working AI Control Plane that's demo-ready and fundable.

**Not:** A complete rewrite of everything.

**Strategy:** Strategic extraction of what matters.
