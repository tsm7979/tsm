# TSM Layer v1.0 - AI Control Plane Architecture

**Date:** March 28, 2026
**Mission:** Transform scattered SecOps-AI codebase into a unified AI Control Layer

---

## Executive Summary

We are consolidating 5+ scattered directories into a clean, production-ready **AI Control Plane** that sits between all applications and AI models. This is NOT a simplification—it's a strategic re-architecture to expose the massive power already built while hiding complexity behind clean abstractions.

### What We're Building

> **TSM Layer: The universal control plane for AI execution, governance, and trust**

Not an app. Not a chatbot. An **infrastructure layer** that:
- Intercepts all AI traffic
- Sanitizes and classifies inputs
- Routes to optimal models/tools
- Executes complex workflows
- Audits everything immutably
- Simulates before risky actions

---

## Source Directory Inventory

### Primary Sources (To Extract From)

1. **C:\Users\mymai\Desktop\SecOps-ai** ← MAIN CODEBASE
   - Full backend with 12+ subsystems
   - Frontend (Next.js)
   - Complete API layer
   - Training pipeline
   - Network/P2P layer

2. **C:\Users\mymai\Desktop\APP**
   - TSM99 prototype
   - Desktop app experiments
   - Early installers

3. **C:\Users\mymai\Desktop\frontend**
   - Standalone frontend experiments

4. **C:\Users\mymai\Desktop\git-workflow**
   - Git automation tools
   - Workflow experiments

5. **C:\Users\mymai\Desktop\TSM-Install-Test**
   - TSM-Platform-Complete (desktop package)

### Destination

**C:\Users\mymai\Desktop\TSMv1** ← CLEAN WORKSPACE

---

## 12-Layer Architecture (Final System Design)

```
┌─────────────────────────────────────────────────────┐
│               LAYER 1: Gateway                       │
│  Single entry point for all AI traffic              │
└─────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────┐
│        LAYER 2: Identity & Session                   │
│  Auth, RBAC, org context, trust scoring             │
└─────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────┐
│        LAYER 3: Firewall (Privacy)                   │
│  PII detection, sanitization, data isolation        │
└─────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────┐
│        LAYER 4: Policy & Governance                  │
│  Rules engine, compliance, approval gates           │
└─────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────┐
│        LAYER 5: Intelligent Router                   │
│  Model selection, cost optimization, routing        │
└─────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────┐
│        LAYER 6: Model Abstraction                    │
│  Unified interface to all LLM providers             │
└─────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────┐
│        LAYER 7: Execution Engine (Agentic)           │
│  Agent orchestration, planning, coordination        │
└─────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────┐
│        LAYER 8: Tool & Workflow Runtime              │
│  Tool registry, sandboxed execution, manifests      │
└─────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────┐
│        LAYER 9: Memory & Context                     │
│  Semantic store, episodic memory, RAG               │
└─────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────┐
│        LAYER 10: Trust & Audit                       │
│  Immutable traces, replay, compliance export        │
└─────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────┐
│        LAYER 11: Simulation & Safety                 │
│  Ghost sim, MCTS, pre-flight risk scoring           │
└─────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────┐
│        LAYER 12: Network Protocol (Future)           │
│  P2P mesh, AI-to-AI communication, packets          │
└─────────────────────────────────────────────────────┘
```

---

## New TSMv1 Directory Structure

```
C:\Users\mymai\Desktop\TSMv1\
│
├── /gateway                    ← LAYER 1: Entry point
│   ├── api.py                 # Main FastAPI app
│   ├── router.py              # Request routing
│   └── middleware.py          # Request/response interceptors
│
├── /identity                   ← LAYER 2: Auth & context
│   ├── auth.py                # Authentication
│   ├── rbac.py                # Role-based access control
│   ├── session.py             # Session management
│   └── trust_scorer.py        # Identity trust scoring
│
├── /firewall                   ← LAYER 3: Privacy & sanitization
│   ├── sanitizer.py           # PII detection & removal
│   ├── classifier.py          # Input risk classification
│   ├── data_isolation.py      # Context-aware redaction
│   └── patterns/              # Detection patterns
│
├── /policy                     ← LAYER 4: Governance
│   ├── engine.py              # Policy decision engine
│   ├── rules.py               # Rule definitions
│   ├── compliance.py          # Compliance frameworks
│   └── approval.py            # Approval workflows
│
├── /router                     ← LAYER 5: Intelligent routing
│   ├── decision_engine.py     # Routing decisions
│   ├── cost_model.py          # Cost optimization
│   ├── latency_model.py       # Performance prediction
│   └── fallback.py            # Failover strategies
│
├── /models                     ← LAYER 6: Model abstraction
│   ├── registry.py            # Model catalog
│   ├── providers/             # Provider implementations
│   │   ├── openai.py
│   │   ├── anthropic.py
│   │   ├── local.py
│   │   └── base.py
│   └── selector.py            # Model selection logic
│
├── /execution                  ← LAYER 7: Agentic core
│   ├── engine.py              # Execution orchestrator
│   ├── planner.py             # Task planning
│   ├── agent.py               # Agent implementation
│   ├── coordinator.py         # Multi-agent coordination
│   └── reasoning_loop.py      # Reasoning logic
│
├── /tools                      ← LAYER 8: Tool system (CRITICAL)
│   ├── registry.py            # Tool discovery & catalog
│   ├── runtime.py             # Sandboxed execution
│   ├── manifest.py            # Tool manifest parser
│   ├── compiler.py            # Workflow → Tool compiler
│   ├── validator.py           # Input/output validation
│   └── packs/                 # Tool packages
│       ├── security/
│       ├── analysis/
│       ├── automation/
│       └── README.md
│
├── /memory                     ← LAYER 9: Context & state
│   ├── semantic_store.py      # Vector embeddings
│   ├── episodic_store.py      # Conversation history
│   ├── context_manager.py     # Context window management
│   └── rag.py                 # Retrieval augmented generation
│
├── /trust                      ← LAYER 10: Audit & replay
│   ├── logger.py              # Immutable logging
│   ├── ledger.py              # Trust ledger
│   ├── replay.py              # Action replay
│   └── verifier.py            # Signature verification
│
├── /simulation                 ← LAYER 11: Safety (DIFFERENTIATOR)
│   ├── ghost_sim.py           # Sandbox simulation
│   ├── mcts_engine.py         # Monte Carlo tree search
│   ├── risk_scorer.py         # Risk prediction
│   └── validator.py           # Pre-flight validation
│
├── /network                    ← LAYER 12: Protocol (Future moat)
│   ├── node.py                # Network node
│   ├── protocol.py            # Communication protocol
│   ├── mesh.py                # P2P mesh
│   └── packets.py             # Threat intelligence packets
│
├── /connectors                 # Enterprise integrations
│   ├── github.py
│   ├── aws.py
│   ├── kubernetes.py
│   └── database.py
│
├── /db                         # Database layer
│   ├── models.py              # SQLAlchemy models
│   ├── session.py             # DB session management
│   └── migrations/            # Alembic migrations
│
├── /web                        # Frontend application
│   ├── app/                   # Next.js app
│   ├── components/
│   ├── hooks/
│   └── public/
│
├── /cli                        # CLI tools
│   ├── tsm.py                 # Main CLI
│   └── commands/
│
├── /sdk                        # Client SDKs
│   ├── python/
│   └── javascript/
│
├── /examples                   # Usage examples
│   ├── quickstart.py
│   ├── enterprise_integration.py
│   └── tool_development.py
│
├── /archive                    # Non-core modules
│   ├── workflows/             # Old workflow corpus
│   ├── desktop/               # Desktop app experiments
│   └── training/              # Model training (separate concern)
│
├── /docs                       # Documentation
│   ├── architecture.md
│   ├── api_reference.md
│   ├── tool_development.md
│   └── deployment.md
│
├── /tests                      # Test suite
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── requirements.txt            # Python dependencies
├── pyproject.toml              # Project metadata
├── docker-compose.yml          # Local development
└── README.md                   # Getting started
```

---

## Module Migration Map

### From SecOps-ai/backend/src/core → TSMv1

| Source Module | Destination | Layer | Priority |
|--------------|-------------|-------|----------|
| `sanitization/sanitizer.py` | `/firewall/sanitizer.py` | 3 | **P0** |
| `sanitization/data_isolation.py` | `/firewall/data_isolation.py` | 3 | **P0** |
| `llm/poly_orchestrator.py` | `/router/decision_engine.py` | 5 | **P0** |
| `llm/model_providers/*` | `/models/providers/*` | 6 | **P0** |
| `agentic/execution_engine.py` | `/execution/engine.py` | 7 | **P0** |
| `agentic/reasoning_loop.py` | `/execution/reasoning_loop.py` | 7 | **P0** |
| `agentic/agent_core.py` | `/execution/agent.py` | 7 | P1 |
| `audit/immutable_trace.py` | `/trust/logger.py` | 10 | **P0** |
| `trust_ledger/ledger.py` | `/trust/ledger.py` | 10 | **P0** |
| `healing/ghost_sim.py` | `/simulation/ghost_sim.py` | 11 | P1 |
| `simulation/mcts_engine.py` | `/simulation/mcts_engine.py` | 11 | P1 |
| `network/p2p_client.py` | `/network/node.py` | 12 | P2 |
| `network/signal_protocol.py` | `/network/protocol.py` | 12 | P2 |
| `memory/semantic_store.py` | `/memory/semantic_store.py` | 9 | P1 |
| `memory/episodic_store.py` | `/memory/episodic_store.py` | 9 | P1 |
| `compliance/policy_engine.py` | `/policy/engine.py` | 4 | P1 |
| `tools/*` | `/tools/` | 8 | **P0** |
| `evolution/*` | `/archive/evolution/` | N/A | P3 |
| `economics/*` | `/policy/cost_governance.py` | 4 | P2 |

### Workflow Corpus → Tool Packages

| Source Workflow | New Tool | Category | Status |
|----------------|----------|----------|--------|
| `invest/` | `market_research_tool` | analysis | Convert |
| `security playbooks` | `security_scan_tool` | security | **Keep** |
| `recipe_meal_plan` | N/A | demo | Archive |
| `travel_recommendation` | N/A | demo | Archive |
| `tetris_game` | N/A | demo | Archive |
| `arxiv_daily_digest` | `research_digest_tool` | knowledge | Convert |

---

## The GATEWAY Layer (Most Critical)

This is the **single entry point** that must be built first. Everything flows through here.

### Core API Surface

```python
# /gateway/api.py

from fastapi import FastAPI, Request
from .pipeline import execute_request

app = FastAPI(title="TSM Layer - AI Control Plane")

@app.post("/ai-proxy")
async def ai_proxy(request: Request):
    """
    Universal AI request handler

    Pipeline:
    1. Identity → Extract user/org context
    2. Firewall → Sanitize & classify
    3. Policy → Check permissions
    4. Router → Select model/tool
    5. Execution → Run logic
    6. Trust → Log everything
    7. Return → Sanitized response
    """
    return await execute_request(request)

@app.post("/tool/execute")
async def execute_tool(tool_name: str, inputs: dict):
    """Execute a registered tool"""
    pass

@app.post("/workflow/run")
async def run_workflow(workflow_id: str, inputs: dict):
    """Execute a multi-step workflow"""
    pass

@app.get("/audit/{trace_id}")
async def get_audit(trace_id: str):
    """Retrieve audit trail for a request"""
    pass
```

### Request Pipeline

```python
# /gateway/pipeline.py

async def execute_request(request):
    # 1. Identity
    context = await identity.extract_context(request)

    # 2. Firewall
    clean_input = await firewall.sanitize(request.input)
    risk = await firewall.classify(clean_input)

    # 3. Policy
    allowed = await policy.check(context, risk)
    if not allowed:
        raise PolicyViolation()

    # 4. Router
    target = await router.select(clean_input, risk, context)

    # 5. Execution
    if target.type == "model":
        result = await models.call(target.model, clean_input)
    elif target.type == "tool":
        result = await tools.execute(target.tool, clean_input)
    elif target.type == "workflow":
        result = await execution.run_workflow(target.workflow, clean_input)

    # 6. Trust
    await trust.log({
        "input": request.input,
        "sanitized": clean_input,
        "risk": risk,
        "target": target,
        "result": result,
        "context": context
    })

    # 7. Return
    return result
```

---

## The TOOL SYSTEM (Strategic Differentiator)

This transforms workflows from "scripts" into "infrastructure primitives."

### Tool Manifest Schema

```json
{
  "name": "security_scan",
  "version": "1.0.0",
  "category": "security",
  "description": "Scans code repositories for vulnerabilities",
  "permissions": ["repo:read", "file:read"],
  "risk_tier": "medium",
  "runtime": "sandbox",
  "inputs": {
    "repo_url": {"type": "string", "required": true},
    "scan_type": {"type": "enum", "values": ["full", "quick"]}
  },
  "outputs": {
    "vulnerabilities": {"type": "array"},
    "risk_score": {"type": "number"}
  },
  "sandbox_config": {
    "network": false,
    "filesystem": "readonly"
  },
  "dependencies": ["semgrep", "bandit"]
}
```

### Tool Registry

```python
# /tools/registry.py

class ToolRegistry:
    def __init__(self):
        self.tools = {}

    def register(self, manifest_path):
        """Load tool from manifest"""
        manifest = load_manifest(manifest_path)
        self.tools[manifest.name] = Tool(manifest)

    def discover(self, category=None, risk_tier=None):
        """Find tools by criteria"""
        return [t for t in self.tools.values()
                if matches(t, category, risk_tier)]

    async def execute(self, tool_name, inputs, context):
        """Execute tool with governance"""
        tool = self.tools[tool_name]

        # Validate inputs
        await tool.validate_inputs(inputs)

        # Check permissions
        await policy.check_tool_access(context, tool)

        # Run in sandbox
        result = await sandbox.execute(tool, inputs)

        # Log
        await trust.log_tool_execution(tool, inputs, result)

        return result
```

---

## Migration Priority & Timeline

### Phase 1: Core Runtime (Week 1-2)

**P0 - Must Have:**
1. Gateway API (`/gateway/`)
2. Firewall layer (`/firewall/`)
3. Router layer (`/router/`)
4. Model abstraction (`/models/`)
5. Trust layer (`/trust/`)

**Deliverable:** Working `/ai-proxy` endpoint

### Phase 2: Execution Layer (Week 3-4)

**P0:**
1. Execution engine (`/execution/`)
2. Tool registry (`/tools/registry.py`)
3. Tool runtime (`/tools/runtime.py`)

**P1:**
1. Memory layer (`/memory/`)
2. Policy engine (`/policy/`)

**Deliverable:** Tool execution working

### Phase 3: Enterprise Features (Week 5-6)

**P1:**
1. Simulation layer (`/simulation/`)
2. Complete policy system (`/policy/`)
3. Enterprise connectors (`/connectors/`)
4. Frontend UI (`/web/`)

**Deliverable:** Enterprise-ready platform

### Phase 4: Network Layer (Week 7-8)

**P2 - Future Moat:**
1. Network protocol (`/network/`)
2. P2P mesh
3. AI-to-AI communication

**Deliverable:** Protocol foundation

---

## What to Archive (Not Delete)

Move to `/archive/` but don't include in core:

1. **Desktop app** - PyQt UI experiments
2. **Training pipeline** - Model training is separate product
3. **Random workflows** - Travel, recipes, games
4. **Old installers** - BUILD_*.bat scripts
5. **Experimental features** - Half-built modules

These may have value later, but they dilute the core product.

---

## Key Architectural Decisions

### 1. Single Gateway
All traffic flows through one entry point. No fragmented APIs.

### 2. Tool-First Execution
Workflows become tools. Tools are first-class primitives.

### 3. Privacy by Default
Every input passes through firewall. No exceptions.

### 4. Simulation Before Action
Risky operations get pre-flighted in ghost sim.

### 5. Immutable Audit
Every request is logged immutably. Enterprise requirement.

### 6. Model Agnostic
Any model, any provider, same interface.

---

## Success Metrics

**Technical:**
- All requests through gateway: 100%
- Audit coverage: 100%
- Tool execution success rate: >95%
- P95 latency: <500ms

**Business:**
- Developer adoption (OSS downloads)
- Enterprise pilots (self-hosted deployments)
- Tool ecosystem growth (community tools)

---

## Next Steps

1. Review this architecture
2. Create migration scripts
3. Build gateway layer
4. Extract core modules systematically
5. Test end-to-end flow
6. Document API
7. Ship OSS version

---

**This is not a rewrite. This is a strategic extraction and elevation of what already exists into a fundable, scalable AI infrastructure company.**
