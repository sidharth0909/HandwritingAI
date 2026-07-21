# HandwritingAI

Generate multi-page handwritten documents that match a user’s writing style. Upload pen-on-paper samples (or draw them), enter text, pick a model, and export PNG/PDF.

The app ships with two working models:

| Model | Backend id | Style input | Notes |
|-------|------------|-------------|--------|
| **DiffusionPen** | `diffusionpen` | 5–10 word samples (photo or canvas) | Latent diffusion + MobileNet style encoder (IAM) |
| **Emuru** (CVPR 2025) | `wordstylist` | 1+ clear photos (zero-shot) | T5 + VAE; auto-crops a word from a page photo via OCR |

> GANwriting is not in the active UI registry. Compare mode (`compare`) remains available via the API if both models are configured.

---

## Stack

| Layer | Technologies |
|-------|----------------|
| Frontend | React 18 (Vite), Tailwind CSS, fabric.js, react-dropzone, axios, Zustand |
| Backend | FastAPI, Pillow, ReportLab, python-docx, pdfplumber, PyTorch, transformers, diffusers, RapidOCR |
| Inference | DiffusionPen (local weights) · Emuru via Hugging Face cache (`blowing-up-groundhogs/emuru`) |

---

## Repository layout

```
DiffPen/                          # git root (GitHub: HandwritingAI)
├── README.md
├── .gitignore
└── handwriting-app/
    ├── frontend/                 # Vite React app (port 3000)
    ├── backend/                  # FastAPI app (port 8080 recommended)
    │   ├── models/               # DiffusionPen, WordStylist (Emuru)
    │   ├── emuru_worker.py       # Emuru subprocess worker
    │   ├── diffusionpen_core/    # Style encoder / UNet glue
    │   ├── routers/              # samples, generate, export
    │   ├── services/             # generation, compositor, exporter
    │   ├── scripts/              # download_weights.py, setup helpers
    │   ├── weights/              # gitignored — model checkpoints
    │   ├── uploads/              # gitignored — session samples
    │   └── outputs/              # gitignored — generated pages
    ├── docker-compose.yml
    └── .env.example
```

Large / local-only paths (weights, venvs, uploads, debug dumps) are listed in `.gitignore`.

---

## Quick start (local)

### 1. Backend

```bash
cd handwriting-app/backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
# optional helper (installs torch stack if needed):
# python setup_env.py

uvicorn main:app --reload --port 8080
```

- API docs: http://127.0.0.1:8080/docs  
- Health / models: http://127.0.0.1:8080/api/model-status  

### 2. Frontend

```bash
cd handwriting-app/frontend
npm install
npm run dev
```

Open http://localhost:3000  

Vite proxies `/api` to `http://localhost:8080` by default (`VITE_API_URL`).

### 3. Download model weights (first time)

From `handwriting-app/backend/` with the venv active:

```bash
python scripts/download_weights.py
```

Expect several GB under `backend/weights/` (gitignored):

- **DiffusionPen** — IAM checkpoint + VAE components  
- **Emuru** — Hugging Face cache under `backend/weights/emuru/`

---

## App flow

1. **Model** — Choose DiffusionPen or Emuru (changing model clears prior samples).  
2. **Samples** — Upload (and optionally draw for DiffusionPen). Emuru expects clear pen-on-paper photos; one page photo is enough.  
3. **Text** — Type or upload a PDF/DOCX/TXT; set page count; generate.  
4. **Output** — Two-column view:
   - Left: your samples, input text, **style source** (your style vs built-in Emuru sample), style crop, per-word source  
   - Right: generated page(s), PNG/PDF download  

Jobs are processed in the background. The UI polls `GET /api/status/{job_id}` every ~2s.

---

## Models in detail

### DiffusionPen

- Needs **5–10** single-word samples (upload or canvas).  
- Style encoder aggregates sample images; generation uses latent diffusion.  
- First generation loads weights into memory (slow once); later runs are faster.  
- CPU: often **several minutes per page**. Set `DEVICE=cuda` for GPU.

### Emuru (`wordstylist`)

- Zero-shot: **1 clear photo** is enough (optional extras up to 5).  
- Worker (`emuru_worker.py`) cleans notebook photos, OCRs word boxes (RapidOCR), crops a style word, and runs Emuru with matching `style_text`.  
- If a word fails quality checks, that word may fall back to Emuru’s bundled `sample.png` — the output page reports **user / fallback / mixed**.  
- Prefer dark ink on white paper. Canvas/digital scribbles usually fail.  
- CPU: about **1–3 minutes** for a short phrase after model load.

---

## API summary

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/samples` | Multipart `files`; optional `session_id`, `model` (`wordstylist` → min 1 sample; else min 5) |
| `POST` | `/api/parse-doc` | Extract text from `.pdf` / `.docx` / `.txt` |
| `POST` | `/api/generate` | JSON `{ session_id, text, model, pages }` → `{ job_id }` |
| `GET` | `/api/status/{job_id}` | `{ status, progress, message }` |
| `GET` | `/api/result/{job_id}` | `{ pages, meta, … }` — `meta` includes style source info |
| `GET` | `/api/file/{job_id}/{filename}` | Serve generated PNG (or `style_used.png`) |
| `POST` | `/api/export/pdf` | Build PDF from a finished job |
| `GET` | `/api/model-status` | Per-model `loaded` / `weights_exist` |

Valid `model` values: `diffusionpen`, `wordstylist`, `compare`.

---

## Environment variables

Copy `handwriting-app/.env.example` → `handwriting-app/backend/.env` (and adjust as needed).

| Variable | Default | Description |
|----------|---------|-------------|
| `ENV` | `local` | Environment label |
| `UPLOAD_DIR` | `uploads` | Sample storage |
| `OUTPUT_DIR` | `outputs` | Generated pages |
| `MAX_PAGES` | `10` | Cap on pages per job |
| `DEVICE` | `cpu` | `cuda` for GPU inference |
| `VITE_API_URL` | `http://localhost:8080` | Frontend → API base (Vite proxy / axios) |

---

## Docker

```bash
cd handwriting-app
docker compose up --build
```

Compose maps backend **8000** and frontend **3000**. For local non-Docker use, this project commonly runs the API on **8080** to match the Vite proxy — keep ports consistent with `VITE_API_URL`.

Volumes: `backend/uploads`, `backend/outputs`.

---

## Tips & troubleshooting

- **Only one uvicorn** on the API port. Two processes sharing `8080` drop in-memory jobs/styles and the UI looks “stuck.”  
- After backend restart, **re-upload samples** (style store is in-memory).  
- Emuru: use a real phone/scanner photo of handwriting, not blank or canvas-only strokes.  
- Weights and venvs are **not** in git — every clone must run `pip install` + `download_weights.py`.  
- Do not commit `backend/weights/`, `.venv/`, `uploads/`, or `outputs/`.

---

## License / credits

- **DiffusionPen** — style-conditioned handwriting diffusion (IAM-oriented pipeline in this repo).  
- **Emuru** — [blowing-up-groundhogs/emuru](https://huggingface.co/blowing-up-groundhogs/emuru) (CVPR 2025).  
- App: HandwritingAI — see repository for license and contribution notes.
