# TSM Layer v1.0 — AI Control Plane

> **The universal control layer for AI execution, governance, and trust**

---

## What Is This?

**TSM Layer** is an AI infrastructure platform that sits between your applications and AI models.

It is **NOT**:
- ❌ An LLM
- ❌ A chatbot
- ❌ Another AI tool

It **IS**:
- ✅ A control plane for AI traffic
- ✅ A governance and compliance layer
- ✅ A privacy firewall
- ✅ An execution engine
- ✅ An audit system

---

## Why Does This Exist?

**Problem:**
Organizations using AI face critical challenges:
- Data leakage to external models
- No audit trail or compliance
- No control over model selection
- No governance or policy enforcement
- No way to verify AI actions

**Solution:**
Every AI request flows through TSM Layer:

```
Your App → TSM Layer → AI Models
           ↓
     [Privacy + Governance + Audit + Trust]
```

---

## 12-Layer Architecture

```
┌─────────────────────────────────────┐
│  1. Gateway        │ Single entry   │
│  2. Identity       │ Auth & context │
│  3. Firewall       │ PII removal    │
│  4. Policy         │ Governance     │
│  5. Router         │ Model select   │
│  6. Models         │ Abstraction    │
│  7. Execution      │ Agentic core   │
│  8. Tools          │ Capabilities   │
│  9. Memory         │ Context store  │
│ 10. Trust          │ Audit logs     │
│ 11. Simulation     │ Pre-flight     │
│ 12. Network        │ Protocol       │
└─────────────────────────────────────┘
```

Every request passes through **all applicable layers** before reaching a model.

---

## Quickstart

### Installation

```bash
# Clone or copy to TSMv1 directory
cd TSMv1

# Install dependencies
pip install -r requirements.txt

# Run the server
python -m uvicorn gateway.api:app --reload --port 8000
```

### First Request

```python
import requests

response = requests.post(
    "http://localhost:8000/ai-proxy",
    json={
        "input": "Analyze this code for security issues",
        "options": {"model_preference": "gpt-4"}
    }
)

print(response.json())
```

**Output:**
```json
{
  "result": "Analysis complete...",
  "trace_id": "abc123...",
  "metadata": {
    "risk_tier": "medium",
    "model_used": "gpt-4",
    "sanitized": false
  }
}
```

---

## Core Features

### 1. **AI Firewall** — Privacy by Default

All inputs are sanitized before reaching external models:

```python
# Input
"My SSN is 123-45-6789, analyze this database"

# After firewall
"My SSN is [SSN_REDACTED], analyze this database"
```

**Detects & removes:**
- PII (emails, phones, SSN)
- Secrets (API keys, passwords, tokens)
- Internal data (IPs, paths, URLs)
- Credentials

### 2. **Intelligent Routing** — Right Model, Right Time

TSM decides which model to use based on:
- Risk classification
- Cost optimization
- Data sensitivity
- Model capabilities

**Example:**
- High-risk data → local model
- General queries → cloud model
- Security tasks → specialized tool

### 3. **Policy Engine** — Govern Every Action

Define what's allowed:

```python
# Policy rule
if risk_tier == "critical":
    require_approval()
    use_local_only()
```

### 4. **Immutable Audit** — Complete Transparency

Every request is logged:

```bash
GET /audit/trace_id

{
  "input": "original input",
  "sanitized": "sanitized version",
  "model_used": "gpt-4",
  "policy_decision": "allowed",
  "timestamp": "2026-03-28T..."
}
```

**Replayable. Explainable. Compliant.**

### 5. **Tool Execution** — AI Does Work

Not just chat — actual execution:

```python
POST /tool/execute

{
  "tool_name": "security_scan",
  "inputs": {"repo": "github.com/..."}
}
```

### 6. **Simulation** — Test Before Execution

Risky operations are simulated first:

```python
# Detects destructive operations
if "DELETE FROM users" in input:
    simulate() → BLOCKED
```

---

## API Reference

### Core Endpoints

#### `POST /ai-proxy`
Universal AI request handler.

**Request:**
```json
{
  "input": "string",
  "context": {},
  "model_preference": "gpt-4",
  "options": {}
}
```

**Response:**
```json
{
  "result": "AI response",
  "trace_id": "unique-id",
  "metadata": {
    "risk_tier": "low|medium|high|critical",
    "model_used": "model-name",
    "execution_time_ms": 234
  }
}
```

#### `POST /tool/execute`
Execute a registered tool.

**Request:**
```json
{
  "tool_name": "security_scan",
  "inputs": {"repo": "url"},
  "options": {}
}
```

#### `GET /audit/{trace_id}`
Retrieve complete audit trail.

#### `GET /tools`
List available tools.

#### `GET /health`
System health check.

---

## Use Cases

### Enterprise AI Gateway

```
Internal Apps → TSM Layer → Models
                   ↓
            [Compliance + Audit]
```

**Benefits:**
- All AI traffic audited
- PII automatically removed
- Policy enforcement
- Cost tracking

### Security Analysis Platform

```
GitHub → TSM → Security Tools
               ↓
          [Analysis + Fix]
```

**Benefits:**
- Automated vulnerability scanning
- AI-powered fix suggestions
- Audit trail for compliance

### Multi-Model Router

```
User Query → TSM → Best Model
              ↓
       [Cost Optimization]
```

**Benefits:**
- Automatic model selection
- Fallback strategies
- Cost reduction

---

## Architecture Principles

### 1. Privacy First
**Never send raw data to external models.**
- All inputs sanitized
- PII removed
- Secrets redacted
- Internal data hashed

### 2. Governance Required
**Every action needs permission.**
- Policy checks before execution
- Risk classification
- Approval workflows
- Compliance tracking

### 3. Audit Everything
**Complete transparency.**
- Immutable logs
- Replayable actions
- Explainable decisions
- Compliance export

### 4. Simulate Risky Actions
**Test before execution.**
- Ghost simulation for high-risk
- MCTS validation
- Rollback capability

### 5. Model Agnostic
**Any model, any provider.**
- OpenAI, Anthropic, local models
- Same interface
- Easy switching

---

## Deployment

### Local Development

```bash
uvicorn gateway.api:app --reload --port 8000
```

### Docker

```dockerfile
FROM python:3.10

WORKDIR /app
COPY . /app

RUN pip install -r requirements.txt

CMD ["uvicorn", "gateway.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Production (Kubernetes)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tsm-layer
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: tsm-layer
        image: tsm-layer:latest
        ports:
        - containerPort: 8000
```

---

## Roadmap

### Phase 1: Core Runtime (✅ Complete)
- Gateway API
- Firewall layer
- Router
- Trust/audit
- Basic tool system

### Phase 2: Enterprise Features (In Progress)
- Advanced policy engine
- Multi-org support
- Enterprise connectors (GitHub, AWS, K8s)
- Advanced simulation

### Phase 3: Network Protocol (Future)
- P2P mesh
- AI-to-AI communication
- Decentralized trust

---

## Contributing

This is a consolidation of multiple repositories. Key extractions:

**Source Directories:**
- `C:\Users\mymai\Desktop\SecOps-ai` → Core backend modules
- `C:\Users\mymai\Desktop\APP` → Tool experiments
- `C:\Users\mymai\Desktop\frontend` → UI components

**Migration Map:**
See [TSM_LAYER_ARCHITECTURE.md](TSM_LAYER_ARCHITECTURE.md) for complete module mapping.

---

## Why This Will Work

### Technical Depth
Most AI startups are thin wrappers.

TSM Layer has:
- 12 distinct architectural layers
- Privacy engineering built-in
- Policy enforcement
- Simulation engine
- Network protocol foundation

**This is infrastructure, not product.**

### Clear Value Prop
**"We sit between every app and every AI model."**

That's:
- Cloudflare for AI
- Control plane for AI
- Trust layer for AI

### Expansion Path

```
V1: AI Firewall + Router
  ↓
V2: Enterprise Control Plane
  ↓
V3: AI Communication Protocol
```

---

## License

MIT License (for OSS core)

Enterprise features require license.

---

## Contact

For enterprise deployments, integrations, or support:
- **Documentation:** [./docs/](./docs/)
- **Issues:** GitHub Issues
- **Architecture:** [TSM_LAYER_ARCHITECTURE.md](TSM_LAYER_ARCHITECTURE.md)

---

**Built to be the layer that AI can't exist without.**
