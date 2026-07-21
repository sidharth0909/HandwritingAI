# HandwritingAI

Full-stack application that generates handwritten pages from user-provided style samples. The current release uses a **mock PIL pipeline** so upload, generation, preview, and PDF export work end-to-end before real model weights are integrated.

## Stack

| Layer | Technologies |
|-------|----------------|
| Frontend | React (Vite), TailwindCSS, fabric.js, react-dropzone, axios, zustand |
| Backend | FastAPI, Pillow, ReportLab, python-docx, python-dotenv, torch |

## Project structure

```
handwriting-app/
├── frontend/src/components/   # Sidebar, Step1–4, UploadZone, DrawCanvas, PagePreview
├── frontend/src/store/        # Zustand global state
├── backend/routers/           # samples, generate, export
├── backend/models/            # DiffusionPen, GANwriting, WordStylist (mock)
├── backend/services/          # style_extractor, compositor, exporter
├── backend/storage/           # In-memory job_store (TODO: Redis)
├── backend/uploads/           # Runtime sample storage (gitignored)
├── backend/outputs/           # Runtime generated PNGs (gitignored)
└── docker-compose.yml
```

## Run locally (without Docker)

### Backend

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

## Run with Docker

```bash
docker compose up --build
```

- Frontend: http://localhost:3000  
- Backend: http://localhost:8000  
- Volumes: `backend/uploads`, `backend/outputs`

## How the mock pipeline works

1. **POST /api/samples** — Saves images to `uploads/{session_id}/`, runs `extract_style()` (256-zero embedding mock), stores style in `job_store`.
2. **POST /api/generate** — Background task tokenizes text, calls `model.generate()` (PIL mock words with slanted serif glyphs), composes A4 pages (2480×3508), saves PNGs to `outputs/{job_id}/`.
3. **GET /api/status/{job_id}** — Poll `{ status, progress, message }`.
4. **GET /api/result/{job_id}** — Returns page URLs or compare map.
5. **GET /api/file/{job_id}/{filename}** — Serves PNG files.
6. **POST /api/export/pdf** — Builds multi-page PDF via ReportLab.

## API summary

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/samples` | Multipart `files`, optional `session_id` |
| POST | `/api/parse-doc` | Extract text from PDF/DOCX |
| POST | `/api/generate` | `{ session_id, text, model, pages }` |
| GET | `/api/status/{job_id}` | Job status |
| GET | `/api/result/{job_id}` | Page URLs / compare map |
| GET | `/api/file/{job_id}/{filename}` | PNG file |
| POST | `/api/export/pdf` | `{ job_id, model? }` |

Models: `diffusionpen`, `ganwriting`, `wordstylist`, or `compare`.

## Plug in real model weights

1. Implement `load()` and `generate()` in `backend/models/diffusionpen.py`, `ganwriting.py`, `wordstylist.py`.
2. Replace mock logic in `backend/services/style_extractor.py` with a real encoder.
3. Swap `backend/storage/job_store.py` for Redis — keep the same key structure (`style:{session_id}`, job dict fields).

Look for `# TODO: Replace with real model inference` and `# TODO: Swap with Redis` in the codebase.

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ENV` | `local` | Environment name |
| `UPLOAD_DIR` | `uploads` | Sample upload directory |
| `OUTPUT_DIR` | `outputs` | Generated PNG directory |
| `MAX_PAGES` | `10` | Max pages per job |
| `VITE_API_URL` | `http://localhost:8000` | Frontend API base URL |
| `DEVICE` | `cpu` | Set to `cuda` on a GPU server for faster inference |

## Setting up real models

### Step 1 — Environment

From `handwriting-app/backend/`, activate the existing venv (do not create a new one):

```bash
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

python setup_env.py
```

This installs CPU PyTorch (if needed), diffusers, transformers, and the rest of the backend stack.

### Step 2 — Download weights

```bash
python scripts/download_weights.py
```

Warning: total download is roughly **~5 GB** (DiffusionPen repo + filtered Stable Diffusion v1.5 components). Files are stored under `backend/weights/` and are gitignored.

### Step 3 — Run the backend

```bash
uvicorn main:app --reload --port 8000
```

DiffusionPen **loads on the first generation request** (not at server startup). Watch the terminal for progress messages (`Loading VAE...`, etc.).

### CPU inference time

On CPU, expect roughly **3–7 minutes per page** depending on text length and hardware. The UI polls job status every 2 seconds while waiting.

### GPU / cloud deployment

On a machine with CUDA, set in `backend/.env`:

```
DEVICE=cuda
```

Restart the backend. DiffusionPen reads `DEVICE` from the environment and moves models to GPU automatically.

### GANwriting and WordStylist

Weights for these models are **not integrated yet**. They continue to use the enhanced PIL mock until their weight folders are added under `backend/weights/ganwriting/` and `backend/weights/wordstylist/`. The model selection screen shows a status badge per model (`Ready`, `Not loaded`, or `Weights missing`).

### Model status API

`GET /api/model-status` returns `loaded` and `weights_exist` for each model so the frontend can show readiness before you generate.
