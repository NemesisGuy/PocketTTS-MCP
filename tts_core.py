import threading
import time
import wave
from pathlib import Path
import platform
import re
import io

import numpy as np
import safetensors.torch
from dotenv import load_dotenv
from pocket_tts import TTSModel, export_model_state

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

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_VOICE_NAME = "bricktop"

_model = None
_model_lock = threading.RLock()
_voice_cache = {}


def _custom_voice_dir() -> Path:
    base = BASE_DIR / "voice_embeddings"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _outputs_dir() -> Path:
    out = BASE_DIR / "outputs"
    out.mkdir(parents=True, exist_ok=True)
    return out


def _normalize_voice_name(name: str) -> str:
    normalized = (name or "").strip().lower()
    normalized = re.sub(r"[^a-z0-9_-]+", "-", normalized)
    normalized = re.sub(r"-+", "-", normalized).strip("-")
    if not normalized:
        raise ValueError("voice name must contain letters or numbers")
    return normalized


def _custom_voice_path(name: str) -> Path:
    return _custom_voice_dir() / f"{_normalize_voice_name(name)}.safetensors"


def _custom_voice_names() -> list[str]:
    return sorted(p.stem for p in _custom_voice_dir().glob("*.safetensors"))


def _load_model_state(path: Path) -> dict:
    flat = safetensors.torch.load_file(str(path))
    nested = {}
    for key, value in flat.items():
        if "/" not in key:
            continue
        module_name, tensor_name = key.split("/", 1)
        nested.setdefault(module_name, {})[tensor_name] = value
    if not nested:
        raise ValueError(f"Invalid voice embedding format: {path}")
    return nested


def load_env() -> None:
    env_path = BASE_DIR / "secrets.env"
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
            custom_path = _custom_voice_path(normalized_voice)
            if custom_path.exists():
                _voice_cache[normalized_voice] = _load_model_state(custom_path)
            else:
                if normalized_voice not in BUILTIN_VOICES:
                    raise ValueError(
                        f"Unknown voice '{normalized_voice}'. Available voices: {', '.join(list_voices())}"
                    )
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


def _wav_bytes_from_float(audio_float32: np.ndarray, sample_rate: int) -> bytes:
    audio = np.clip(audio_float32, -1.0, 1.0)
    pcm16 = (audio * 32767.0).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm16.tobytes())
    return buf.getvalue()


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
    combined = BUILTIN_VOICES.copy()
    for custom in _custom_voice_names():
        if custom not in combined:
            combined.append(custom)
    return combined


def resolve_default_voice() -> str:
    voices = list_voices()
    if DEFAULT_VOICE_NAME in voices:
        return DEFAULT_VOICE_NAME
    if "alba" in voices:
        return "alba"
    return voices[0] if voices else "alba"


def create_voice_embedding(
    voice_name: str,
    audio_path: str,
    overwrite: bool = False,
) -> dict:
    source = Path(audio_path)
    if not source.exists():
        raise FileNotFoundError(f"Audio sample not found: {source}")

    normalized_name = _normalize_voice_name(voice_name)
    destination = _custom_voice_path(normalized_name)

    if destination.exists() and not overwrite:
        raise FileExistsError(
            f"Voice embedding already exists: {destination.name}. Use overwrite=True to replace."
        )

    model = get_model()
    state = model.get_state_for_audio_prompt(str(source))
    export_model_state(state, str(destination))

    with _model_lock:
        _voice_cache[normalized_name] = _load_model_state(destination)

    return {
        "voice": normalized_name,
        "embedding_path": str(destination),
        "source_audio": str(source),
        "voices": list_voices(),
    }


def synthesize_to_wav(
    text: str,
    voice: str | None = None,
    output_path: str | None = None,
) -> dict:
    if not text or not text.strip():
        raise ValueError("text must not be empty")

    selected_voice = (voice or "").strip() or resolve_default_voice()
    model = get_model()
    voice_state = get_voice_state(selected_voice)

    started = time.perf_counter()
    audio_tensor = model.generate_audio(voice_state, text)
    elapsed = time.perf_counter() - started

    audio_np = _tensor_to_float_np(audio_tensor)

    destination = (
        Path(output_path)
        if output_path
        else _outputs_dir() / f"tts_{int(time.time())}.wav"
    )
    write_wav(destination, model.sample_rate, audio_np)

    duration_seconds = float(audio_np.shape[-1]) / float(model.sample_rate)
    return {
        "output_path": str(destination),
        "sample_rate": int(model.sample_rate),
        "duration_seconds": round(duration_seconds, 3),
        "generation_seconds": round(elapsed, 3),
        "voice": selected_voice,
    }


def synthesize_audio(
    text: str,
    voice: str | None = None,
) -> dict:
    if not text or not text.strip():
        raise ValueError("text must not be empty")

    selected_voice = (voice or "").strip() or resolve_default_voice()
    model = get_model()
    voice_state = get_voice_state(selected_voice)

    started = time.perf_counter()
    audio_tensor = model.generate_audio(voice_state, text)
    elapsed = time.perf_counter() - started

    audio_np = _tensor_to_float_np(audio_tensor)
    duration_seconds = float(audio_np.shape[-1]) / float(model.sample_rate)
    return {
        "audio": audio_np,
        "sample_rate": int(model.sample_rate),
        "duration_seconds": round(duration_seconds, 3),
        "generation_seconds": round(elapsed, 3),
        "voice": selected_voice,
    }


def synthesize_chunked_to_wavs(
    text: str,
    voice: str | None = None,
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

    selected_voice = (voice or "").strip() or resolve_default_voice()
    model = get_model()
    voice_state = get_voice_state(selected_voice)

    ts = int(time.time())
    chunk_base_dir = Path(output_dir) if output_dir else _outputs_dir() / f"chunks_{ts}"
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
            else _outputs_dir() / f"tts_chunked_{ts}.wav"
        )
        write_wav(merged_path_obj, model.sample_rate, merged)
        merged_path = str(merged_path_obj)

    return {
        "voice": selected_voice,
        "chunk_count": len(chunk_results),
        "chunk_size": int(chunk_size),
        "sample_rate": int(model.sample_rate),
        "duration_seconds": round(total_duration, 3),
        "generation_seconds": round(total_generation_seconds, 3),
        "merged_output_path": merged_path,
        "chunks": chunk_results,
    }


def play_audio_file(path: str, block: bool = True) -> dict:
    audio_path = Path(path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    if platform.system() != "Windows":
        raise RuntimeError("Local playback is currently supported on Windows only")

    import winsound

    flags = winsound.SND_FILENAME
    if not block:
        flags |= winsound.SND_ASYNC

    winsound.PlaySound(str(audio_path), flags)
    return {"played": True, "path": str(audio_path), "blocking": bool(block)}


def play_audio_bytes(wav_bytes: bytes, block: bool = True) -> dict:
    if platform.system() != "Windows":
        raise RuntimeError("Local playback is currently supported on Windows only")

    if not block:
        raise RuntimeError("In-memory playback supports blocking mode only")

    import winsound

    winsound.PlaySound(wav_bytes, winsound.SND_MEMORY)
    return {"played": True, "path": None, "blocking": True, "mode": "memory"}


def speak_now_local(
    text: str,
    voice: str | None = None,
    output_path: str | None = None,
    block: bool = True,
    keep_file: bool = False,
) -> dict:
    # Default behavior avoids disk writes by using in-memory playback.
    if output_path is None and block and not keep_file:
        generated = synthesize_audio(text=text, voice=voice)
        wav_bytes = _wav_bytes_from_float(generated["audio"], generated["sample_rate"])
        playback = play_audio_bytes(wav_bytes, block=True)
        return {
            "output_path": None,
            "sample_rate": generated["sample_rate"],
            "duration_seconds": generated["duration_seconds"],
            "generation_seconds": generated["generation_seconds"],
            "voice": generated["voice"],
            "playback": playback,
            "persisted": False,
        }

    result = synthesize_to_wav(text=text, voice=voice, output_path=output_path)
    playback = play_audio_file(result["output_path"], block=block)
    result["playback"] = playback
    result["persisted"] = True

    # Auto-cleanup transient file when caller did not ask to keep it.
    if output_path is None and block and not keep_file:
        try:
            Path(result["output_path"]).unlink(missing_ok=True)
            result["persisted"] = False
        except OSError:
            pass

    return result
