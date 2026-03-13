import threading
import time
import wave
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from pocket_tts import TTSModel

BUILTIN_VOICES = [
    "alba",
    "marius",
    "javert",
    "jean",
    "fantine",
    "cosette",
    "eponine",
    "azelma",
]

_model = None
_model_lock = threading.RLock()
_voice_cache = {}


def load_env() -> None:
    env_path = Path("secrets.env")
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)


def get_model() -> TTSModel:
    global _model
    with _model_lock:
        if _model is None:
            load_env()
            _model = TTSModel.load_model()
        return _model


def get_voice_state(voice: str):
    normalized_voice = (voice or "").strip() or "alba"
    with _model_lock:
        if normalized_voice not in _voice_cache:
            _voice_cache[normalized_voice] = get_model().get_state_for_audio_prompt(
                normalized_voice
            )
        return _voice_cache[normalized_voice]


def write_wav(path: Path, sample_rate: int, audio_float32: np.ndarray) -> None:
    audio = np.clip(audio_float32, -1.0, 1.0)
    pcm16 = (audio * 32767.0).astype(np.int16)

    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm16.tobytes())


def _tensor_to_float_np(audio_tensor) -> np.ndarray:
    audio = audio_tensor.detach().cpu().numpy().astype(np.float32)
    if audio.ndim > 1:
        audio = np.squeeze(audio)
    return audio


def split_text(text: str, max_chars: int = 180) -> list[str]:
    stripped = text.strip()
    if not stripped:
        return []

    words = stripped.split()
    chunks = []
    current = []
    current_len = 0

    for word in words:
        extra = len(word) + (1 if current else 0)
        if current and current_len + extra > max_chars:
            chunks.append(" ".join(current))
            current = [word]
            current_len = len(word)
        else:
            current.append(word)
            current_len += extra

    if current:
        chunks.append(" ".join(current))

    return chunks


def list_voices() -> list[str]:
    return BUILTIN_VOICES.copy()


def synthesize_to_wav(
    text: str,
    voice: str = "alba",
    output_path: str | None = None,
) -> dict:
    if not text or not text.strip():
        raise ValueError("text must not be empty")

    model = get_model()
    voice_state = get_voice_state(voice)

    started = time.perf_counter()
    audio_tensor = model.generate_audio(voice_state, text)
    elapsed = time.perf_counter() - started

    audio_np = _tensor_to_float_np(audio_tensor)

    destination = Path(output_path) if output_path else Path("outputs") / f"tts_{int(time.time())}.wav"
    write_wav(destination, model.sample_rate, audio_np)

    duration_seconds = float(audio_np.shape[-1]) / float(model.sample_rate)
    return {
        "output_path": str(destination),
        "sample_rate": int(model.sample_rate),
        "duration_seconds": round(duration_seconds, 3),
        "generation_seconds": round(elapsed, 3),
        "voice": voice,
    }


def synthesize_chunked_to_wavs(
    text: str,
    voice: str = "alba",
    chunk_size: int = 180,
    output_dir: str | None = None,
    merged_output_path: str | None = None,
    merge_output: bool = True,
) -> dict:
    if not text or not text.strip():
        raise ValueError("text must not be empty")
    if chunk_size < 40:
        raise ValueError("chunk_size must be at least 40")

    chunks = split_text(text, max_chars=chunk_size)
    if not chunks:
        raise ValueError("text produced no chunks")

    model = get_model()
    voice_state = get_voice_state(voice)

    ts = int(time.time())
    chunk_base_dir = Path(output_dir) if output_dir else Path("outputs") / f"chunks_{ts}"
    chunk_base_dir.mkdir(parents=True, exist_ok=True)

    chunk_results = []
    merged_audio = []
    total_generation_seconds = 0.0

    for idx, chunk_text in enumerate(chunks, start=1):
        started = time.perf_counter()
        audio_tensor = model.generate_audio(voice_state, chunk_text)
        elapsed = time.perf_counter() - started
        total_generation_seconds += elapsed

        audio_np = _tensor_to_float_np(audio_tensor)
        merged_audio.append(audio_np)

        chunk_path = chunk_base_dir / f"chunk_{idx:03d}.wav"
        write_wav(chunk_path, model.sample_rate, audio_np)

        chunk_duration = float(audio_np.shape[-1]) / float(model.sample_rate)
        chunk_results.append(
            {
                "index": idx,
                "text": chunk_text,
                "output_path": str(chunk_path),
                "duration_seconds": round(chunk_duration, 3),
                "generation_seconds": round(elapsed, 3),
            }
        )

    merged_path = None
    total_duration = sum(item["duration_seconds"] for item in chunk_results)

    if merge_output and merged_audio:
        merged = np.concatenate(merged_audio)
        merged_path_obj = (
            Path(merged_output_path)
            if merged_output_path
            else Path("outputs") / f"tts_chunked_{ts}.wav"
        )
        write_wav(merged_path_obj, model.sample_rate, merged)
        merged_path = str(merged_path_obj)

    return {
        "voice": voice,
        "chunk_count": len(chunk_results),
        "chunk_size": int(chunk_size),
        "sample_rate": int(model.sample_rate),
        "duration_seconds": round(total_duration, 3),
        "generation_seconds": round(total_generation_seconds, 3),
        "merged_output_path": merged_path,
        "chunks": chunk_results,
    }
