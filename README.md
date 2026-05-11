---
title: Aegis Legal
emoji: 🏛️
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

<div align="center">
  <h1 style="font-size: 3rem;">🏛️ Aegis Legal</h1>
  <p><b>Precision Legal Intelligence & Secure Cloud-Native RAG</b></p>
  
  [![License: MIT](https://img.shields.io/badge/License-MIT-gold.svg)](https://opensource.org/licenses/MIT)
  [![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
  [![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
  [![Deployment: Live](https://img.shields.io/badge/Deployment-Live-brightgreen.svg)](https://huggingface.co/spaces/ANkur-Garg/Aegis-Legal)
</div>

---

### 🛡️ Vision
Aegis Legal is a high-performance, production-ready Intelligence Engine designed for the legal sector. It bridges the gap between raw legal documents and actionable insights using a **Source-First** philosophy—ensuring every AI response is grounded in verifiable legal articles.

### 🧠 Core Intelligence
*   **Legal Semantic Splitter**: A proprietary chunking strategy that respects document boundaries (Articles, Sections, Clauses) instead of arbitrary character counts.
*   **Trust Evaluation Agent**: Integrated "AI Judge" that scores every response for *Faithfulness* and *Groundedness* before delivery.
*   **Contextual Memory**: Powered by Upstash Redis, providing ultra-low latency Short-Term Memory (STM) and Persistent Session History (LTM).

### 🏗️ Technical Architecture
- **API Framework**: FastAPI (Async Performance)
- **Vector Intelligence**: Qdrant Cloud (HNSW Indexing)
- **Identity & Audit**: Supabase (RBAC & Document Logs)
- **Privacy Shield**: Integrated PII masking and safety guardrails.

---

### 📊 API Reference (Production Endpoints)

| Endpoint | Method | Access | Description |
| :--- | :--- | :--- | :--- |
| `/api/v1/auth/register` | `POST` | Public | Register new legal researchers. |
| `/api/v1/auth/login` | `POST` | Public | Obtain JWT secure access tokens. |
| `/api/v1/chat` | `POST` | User | Streaming RAG query with citations. |
| `/api/v1/ingest` | `POST` | Admin | Secure document ingestion to Qdrant. |
| `/api/v1/history` | `GET` | User | Retrieve persistent session audit trails. |

---

### 🚀 CI/CD Pipeline
Aegis Legal uses a **Safety-First CI/CD** strategy via GitHub Actions:
1.  **Validation Phase**: Automatically runs the `pytest` regression suite on every push.
2.  **Deployment Phase**: Only if tests pass, the repository is mirrored to **HuggingFace Spaces** for immediate production use.

### 🔧 Configuration
Set the following secrets in your environment or hosting platform:
- `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY`
- `QDRANT_URL` / `QDRANT_API_KEY`
- `REDIS_URL`
- `GROQ_API_KEY` (or other LLM provider)

---

<div align="center">
  <sub>Built by Aegis Legal. Engineering Trust in Legal Technology.</sub>
</div>
