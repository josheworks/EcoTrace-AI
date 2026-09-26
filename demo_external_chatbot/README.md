# Demo External Chatbot — EcoTrace AI Integration Example

This directory demonstrates how to integrate `ecotrace-ai` into an existing external Python chatbot or LLM application.

## Quickstart

### 1. Install EcoTrace AI
```bash
pip install ecotrace-ai
```

### 2. Run the Chatbot
```bash
python chatbot.py
```

### 3. Launch the Observability Dashboard
In a second terminal window, launch the dashboard:
```bash
ecotrace dashboard --port 8000
```
Open `http://localhost:8000/ecotrace-ai/` in your browser. Live telemetry from `chatbot.py` will auto-update on the dashboard every 2.5 seconds!
