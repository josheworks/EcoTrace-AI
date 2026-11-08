# EcoTrace AI

> **Production-oriented AI Workload Observability & Optimization SDK**

EcoTrace AI (`ecotrace-ai`) is a lightweight, provider-agnostic Python SDK and observability platform for recording, analyzing, and optimizing AI/LLM workloads in real time.

---

## Core Pipeline

```text
OBSERVE ──> DETECT ──> ANALYZE ──> OPTIMIZE ──> MEASURE
```

1. **Observe**: Capture AI requests and responses across multiple LLM providers (OpenAI, Google Gemini, Groq, Generic).
2. **Detect**: Identify exact duplicate and semantically redundant AI requests via deterministic SHA-256 fingerprint hashing.
3. **Analyze**: Measure token consumption, latency distribution (P50, P95, P99), and overall workload efficiency.
4. **Optimize**: Recommend actionable strategies such as response caching and model right-sizing.
5. **Measure**: Quantify cost ($ USD), energy (Wh/kWh), carbon footprint (gCO2), and calculate composite **EcoScore** (0–100 grade A–F).

---

## Architecture

```text
Developer Application (e.g. Chatbot)
        │
        ▼  pip install ecotrace-ai
EcoTrace SDK (Client, @track, RequestCapture)
        │
        ▼  Automatic Secret Redaction (API Keys, Bearer Tokens)
Local SQLite Telemetry Storage (ecotrace.db)
        │
        ▼  CLI: ecotrace dashboard --port 8000
EcoTrace Analytics Dashboard & FastAPI Backend
        │
        ▼  Auto-polling every 2.5s
http://localhost:8000/ecotrace/
```

- **Provider Agnostic**: Normalized `RequestEvent` abstraction decoupled from vendor SDKs.
- **Zero API Key Leakage**: Secret keys (`sk-...`, `gsk_...`, `AIzaSy...`, auth headers) are automatically redacted prior to storage.
- **Live Real-time Dashboard**: Built-in FastAPI server and single-page web UI auto-polling live telemetry.

---

## Quickstart & Installation

```bash
pip install ecotrace-ai
```

### 1. Integrate SDK into your LLM Application

```python
from ecotrace import EcoTrace, RequestCapture, ResponseCapture

# Initialize EcoTrace with SQLite storage
eco = EcoTrace(storage="sqlite", storage_path="ecotrace.db")

# Track request / response pair
request = RequestCapture(
    prompt="What are best practices for LLM cost optimization?",
    provider="openai",
    model="gpt-4o-mini"
)

response = ResponseCapture(
    response="Cache repeated prompts and use model right-sizing...",
    input_tokens=15,
    output_tokens=30,
    latency_ms=140.2
)

result = eco.track(request, response)
print(f"Tracked Event: {result.event.request_id} | Duplicate: {result.is_duplicate}")
```

### 2. Launch the Observability Dashboard CLI

```bash
ecotrace dashboard --port 8000 --db ecotrace.db
```

Open `http://localhost:8000/ecotrace/` in your browser. Real-time telemetry automatically appears as requests are processed!

---

## CLI Reference

```bash
# Launch dashboard on custom port and database path
ecotrace dashboard --port 8765 --db my_events.db

# Seed sample data for testing/demonstration
ecotrace dashboard --port 8000 --seed
```

---

## Component Status Matrix

| Component | Status | Details |
|---|---|---|
| SDK Foundation | ✅ Complete | Package structure, `EcoTrace` client, `RequestEvent` data model |
| Provider Abstractions | ✅ Complete | `BaseProvider`, `OpenAIProvider`, `GeminiProvider`, `GroqProvider`, `GenericProvider` |
| Storage Layer | ✅ Complete | `MemoryStorage` and `SQLiteStorage` with WAL journal mode |
| Capture & Tracking | ✅ Complete | `RequestCapture`, `ResponseCapture`, `Tracker`, `Session`, `EventEmitter` |
| Secret Sanitization | ✅ Complete | Automatic redaction of provider keys (`sk-...`, `gsk_...`, `AIzaSy...`) |
| Duplicate Detection | ✅ Complete | `DuplicateDetector` using deterministic request fingerprint hashing |
| Intelligence Modules | ✅ Complete | `TokenAnalyzer`, `LatencyAnalyzer`, `SimilarityAnalyzer`, `EfficiencyAnalyzer` |
| Optimization Engine | ✅ Complete | `Optimizer`, `RecommendationEngine`, `CachingStrategy`, `ModelDowngradeStrategy` |
| Impact Estimators | ✅ Complete | `CostCalculator`, `EnergyEstimator`, `CarbonEstimator`, `EcoScoreCalculator` |
| CLI Launcher | ✅ Complete | `ecotrace dashboard --port <port> --db <path>` |
| Dashboard UI & APIs | ✅ Complete | Single-page UI at `/ecotrace-ai/` with 2.5s real-time auto-polling & FastAPI endpoints |

---

## Demonstration App

A complete working example chatbot is provided in `demo_external_chatbot/`:

```bash
cd demo_external_chatbot
python chatbot.py
```

---

## License

[MIT License](LICENSE)