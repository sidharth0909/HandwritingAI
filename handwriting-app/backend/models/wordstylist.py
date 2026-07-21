import json
import os
import shutil
import subprocess
import sys
import tempfile

from PIL import Image

from .base import BaseHandwritingModel

_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_EMURU_VENV_PYTHON = os.path.join(_BACKEND_DIR, "emuru_venv", "Scripts", "python.exe")
_MAIN_VENV_PYTHON = os.path.join(_BACKEND_DIR, ".venv", "Scripts", "python.exe")


def _resolve_python() -> str | None:
    """Prefer dedicated emuru_venv; fall back to backend .venv / current interpreter."""
    for candidate in (_EMURU_VENV_PYTHON, _MAIN_VENV_PYTHON, sys.executable):
        if candidate and os.path.exists(candidate):
            return candidate
    return None


EMURU_WORKER = os.path.join(_BACKEND_DIR, "emuru_worker.py")
EMURU_CACHE = os.path.join(_BACKEND_DIR, "weights", "emuru")


class WordStylist(BaseHandwritingModel):
    name = "wordstylist"

    def __init__(self):
        self.python = _resolve_python()
        self.is_loaded = bool(self.python and os.path.exists(EMURU_WORKER))
        self.last_meta: dict = {}

    def load(self):
        self.python = _resolve_python()
        self.is_loaded = bool(self.python and os.path.exists(EMURU_WORKER))
        if self.is_loaded:
            print(f"Emuru subprocess ready ({self.python}).", flush=True)
        else:
            print(
                f"Emuru Python not found. Tried: {_EMURU_VENV_PYTHON}, "
                f"{_MAIN_VENV_PYTHON}, {sys.executable}",
                flush=True,
            )

    def generate(self, words: list[str], style_image_paths: list[str]) -> list[Image.Image]:
        self.last_meta = {
            "style_source": "unavailable",
            "style_label": None,
            "style_text": None,
            "word_sources": ["mock"] * len(words),
            "words": list(words),
            "style_crop": None,
        }
        if not self.is_loaded or not style_image_paths:
            print(
                "Emuru unavailable — using mock "
                f"(loaded={self.is_loaded}, paths={len(style_image_paths or [])})",
                flush=True,
            )
            from .mock_draw import draw_mock_word

            self.last_meta["style_source"] = "mock"
            return [draw_mock_word(w) for w in words]

        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                cmd = [
                    self.python,
                    "-u",
                    EMURU_WORKER,
                    "--style-image",
                    style_image_paths[0],
                    "--words",
                    *words,
                    "--output-dir",
                    tmp_dir,
                    "--cache-dir",
                    EMURU_CACHE,
                ]
                print(f"Emuru cmd: {cmd[0]} ... ({len(words)} words)", flush=True)

                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )
                stdout_lines: list[str] = []
                assert proc.stdout is not None
                try:
                    for line in proc.stdout:
                        line = line.rstrip("\n")
                        stdout_lines.append(line)
                        print(f"Emuru| {line}", flush=True)
                    returncode = proc.wait(timeout=600)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    print("Emuru subprocess timed out", flush=True)
                    from .mock_draw import draw_mock_word

                    self.last_meta["style_source"] = "error"
                    return [draw_mock_word(w) for w in words]

                if returncode != 0:
                    print(f"Emuru subprocess error (code {returncode})", flush=True)
                    from .mock_draw import draw_mock_word

                    self.last_meta["style_source"] = "error"
                    return [draw_mock_word(w) for w in words]

                images = []
                word_sources = []
                for line in stdout_lines:
                    if line.startswith("STYLE_META:"):
                        try:
                            self.last_meta = json.loads(line.split(":", 1)[1])
                        except json.JSONDecodeError:
                            pass
                    elif line.startswith("GENERATED:"):
                        # GENERATED:idx:path[:source] — path may contain drive colons on Windows
                        rest = line[len("GENERATED:") :]
                        src = "user"
                        if rest.rsplit(":", 1)[-1] in ("user", "fallback", "mock"):
                            rest, src = rest.rsplit(":", 1)
                        idx_str, path = rest.split(":", 1)
                        images.append(Image.open(path).copy())
                        word_sources.append(src)

                # Keep style crop in memory (temp dir is deleted when we leave the with-block)
                crop_src = self.last_meta.get("style_crop")
                self._style_crop_image = None
                if crop_src and os.path.isfile(crop_src):
                    try:
                        self._style_crop_image = Image.open(crop_src).convert("RGB").copy()
                    except Exception:
                        self._style_crop_image = None

                if word_sources:
                    self.last_meta["word_sources"] = word_sources
                if not self.last_meta.get("style_source") and word_sources:
                    if all(s == "fallback" for s in word_sources):
                        self.last_meta["style_source"] = "fallback"
                    elif all(s == "user" for s in word_sources):
                        self.last_meta["style_source"] = "user"
                    else:
                        self.last_meta["style_source"] = "mixed"

                if not images:
                    print("Emuru produced no GENERATED lines — using mock", flush=True)
                    from .mock_draw import draw_mock_word

                    self.last_meta["style_source"] = "mock"
                    return [draw_mock_word(w) for w in words]

                print(f"Emuru generated {len(images)} word images", flush=True)
                return images

        except Exception as e:
            print(f"Emuru error: {e}", flush=True)
            from .mock_draw import draw_mock_word

            self.last_meta["style_source"] = "error"
            return [draw_mock_word(w) for w in words]
