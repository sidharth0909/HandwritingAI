# HandwritingAI (app package)

This folder contains the full-stack app. For setup, models, API, and troubleshooting, see the **[root README](../README.md)**.

## Run (short)

```bash
# Backend — from this directory
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
python scripts/download_weights.py   # first time only
uvicorn main:app --reload --port 8080

# Frontend — new terminal
cd frontend
npm install
npm run dev
```

- UI: http://localhost:3000  
- API: http://127.0.0.1:8080/docs  

Active models: **DiffusionPen** (`diffusionpen`) and **Emuru** (`wordstylist`).
