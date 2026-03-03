import os
import uuid
import shutil
import logging
import subprocess
import tempfile
import urllib.request
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI()
logger = logging.getLogger("tts-server")

VOICE_NAME = os.getenv("VOICE_NAME", "en_US-lessac-medium")
VOICES_DIR = os.getenv("VOICES_DIR", "/voices")
VOICE_DOWNLOAD_BASE_URL = os.getenv(
    "VOICE_DOWNLOAD_BASE_URL",
    "https://huggingface.co/rhasspy/piper-voices/resolve/main",
)
DOWNLOAD_TIMEOUT_SECONDS = int(os.getenv("VOICE_DOWNLOAD_TIMEOUT_SECONDS", "300"))

class TTSRequest(BaseModel):
    text: str

def get_voice_paths():
    voices_dir = Path(VOICES_DIR)
    model_path = voices_dir / f"{VOICE_NAME}.onnx"
    config_path = voices_dir / f"{VOICE_NAME}.onnx.json"
    return voices_dir, model_path, config_path

def build_voice_download_urls():
    try:
        locale, speaker, quality = VOICE_NAME.rsplit("-", 2)
        language = locale.split("_", 1)[0]
    except ValueError as exc:
        raise RuntimeError(
            f"Invalid VOICE_NAME '{VOICE_NAME}'. Expected format like en_US-lessac-medium."
        ) from exc

    relative_dir = f"{language}/{locale}/{speaker}/{quality}"
    model_filename = f"{VOICE_NAME}.onnx"
    config_filename = f"{VOICE_NAME}.onnx.json"

    return (
        f"{VOICE_DOWNLOAD_BASE_URL}/{relative_dir}/{model_filename}?download=true",
        f"{VOICE_DOWNLOAD_BASE_URL}/{relative_dir}/{config_filename}?download=true",
    )

def download_file(url: str, destination: Path):
    temp_destination = destination.with_suffix(destination.suffix + ".part")
    with urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
        with temp_destination.open("wb") as output_file:
            shutil.copyfileobj(response, output_file)
    temp_destination.replace(destination)

def ensure_voice_downloaded():
    voices_dir, model_path, config_path = get_voice_paths()
    if model_path.exists() and config_path.exists():
        return model_path, config_path

    voices_dir.mkdir(parents=True, exist_ok=True)
    model_url, config_url = build_voice_download_urls()

    try:
        if not model_path.exists():
            download_file(model_url, model_path)
        if not config_path.exists():
            download_file(config_url, config_path)
    except Exception as exc:
        for path in (model_path, config_path):
            part_file = path.with_suffix(path.suffix + ".part")
            if part_file.exists():
                part_file.unlink()
        raise RuntimeError(
            f"Failed to download voice '{VOICE_NAME}' from {VOICE_DOWNLOAD_BASE_URL}: {exc}"
        ) from exc

    return model_path, config_path

@app.on_event("startup")
def warm_voice_cache():
    try:
        ensure_voice_downloaded()
    except RuntimeError as exc:
        logger.warning("Voice warmup failed: %s", exc)

@app.post("/tts")
def tts(req: TTSRequest):
    text = (req.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is empty")

    # Output wav temp
    out_wav = os.path.join(tempfile.gettempdir(), f"tts_{uuid.uuid4().hex}.wav")

    try:
        model_path, json_path = ensure_voice_downloaded()
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    # chạy piper
    proc = subprocess.run(
        ["piper", "--model", str(model_path), "--config", str(json_path), "--output_file", out_wav],
        input=text.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        raise HTTPException(status_code=500, detail=proc.stderr.decode("utf-8", errors="ignore")[:1000])

    return FileResponse(out_wav, media_type="audio/wav", filename="speech.wav")
