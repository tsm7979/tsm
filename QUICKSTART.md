# TSM Layer - Quickstart

## 5-Minute Setup

### 1. Install Dependencies

```bash
cd C:\Users\mymai\Desktop\TSMv1
pip install fastapi uvicorn pydantic
```

### 2. Start Server

```bash
python start.py
```

### 3. Test It

Open browser: **http://localhost:8000/docs**

Or use curl:

```bash
curl http://localhost:8000/health
```

### 4. Send First Request

```bash
curl -X POST http://localhost:8000/ai-proxy \
  -H "Content-Type: application/json" \
  -d '{
    "input": "My SSN is 123-45-6789. Analyze this code.",
    "options": {}
  }'
```

**Expected:** SSN gets redacted automatically

## What Just Happened?

Every request flows through:

1. **Gateway** - Entry point
2. **Firewall** - PII removed (`[SSN_REDACTED]`)
3. **Policy** - Permission check
4. **Router** - Model selection
5. **Execution** - Run logic
6. **Trust** - Audit log
7. **Response** - Clean output

## Next Steps

See [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) for:
- Extracting remaining modules
- Building tool system
- Enterprise features

## Current Status

✅ Working:
- Gateway API
- Firewall/sanitization
- Risk classification
- Basic routing
- Audit logging

⏳ TODO:
- Real model providers
- Tool execution
- Workflow system
- Frontend UI

## Files Extracted

From **SecOps-ai** → **TSMv1**:

- ✅ `sanitizer.py` → `firewall/`
- ✅ `poly_orchestrator.py` → `router/`
- ✅ `model_providers/` → `models/`
- ✅ `execution_engine.py` → `execution/`
- ✅ `immutable_trace.py` → `trust/`

## Architecture

```
TSMv1/
├── gateway/       ← Entry point (working)
├── firewall/      ← Privacy (working)
├── router/        ← Routing (extracted)
├── models/        ← Providers (extracted)
├── execution/     ← Agentic (extracted)
├── trust/         ← Audit (extracted)
├── tools/         ← Tool system (stub)
├── policy/        ← Governance (stub)
├── memory/        ← Context (stub)
└── simulation/    ← Safety (stub)
```

**Goal:** Ship working AI Control Plane, not perfect everything.
