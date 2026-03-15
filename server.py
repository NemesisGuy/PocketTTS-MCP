import os
import socket
import subprocess
import sys
import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from tts_core import create_voice_embedding
from tts_core import list_voices as core_list_voices
from tts_core import list_output_devices as core_list_output_devices
from tts_core import resolve_default_voice
from tts_core import speak_now_local
from tts_core import synthesize_chunked_to_wavs
from tts_core import synthesize_to_wav

mcp = FastMCP("PocketTTS-MCP")
BASE_DIR = Path(__file__).resolve().parent
GUI_PORT = os.getenv("POCKETTTS_GUI_PORT", "7860")
DEFAULT_MCP_CONFIG_PATH = os.getenv("POCKETTTS_MCP_CONFIG_PATH", "")


def _is_port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        return sock.connect_ex((host, port)) == 0


def _start_gui_sidecar() -> None:
    if os.getenv("POCKETTTS_AUTOSTART_GUI", "1") != "1":
        return

    try:
        port = int(GUI_PORT)
    except ValueError:
        port = 7860

    if _is_port_open("127.0.0.1", port):
        return

    env = os.environ.copy()
    env.setdefault("POCKETTTS_GUI_PORT", str(port))
    env.setdefault("POCKETTTS_GUI_INBROWSER", "1")

    log_dir = BASE_DIR / "outputs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "gui_sidecar.log"

    with log_path.open("a", encoding="utf-8") as log_file:
        log_file.write("\n--- Starting GUI sidecar ---\n")

    log_file = log_path.open("a", encoding="utf-8")
    subprocess.Popen(
        [sys.executable, str(BASE_DIR / "gui.py")],
        cwd=str(BASE_DIR),
        env=env,
        stdout=log_file,
        stderr=log_file,
    )


def _normalize_auto_chat(value: str | bool | int | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int):
        return "1" if value != 0 else "0"

    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "on", "yes", "y"}:
        return "1"
    if normalized in {"0", "false", "off", "no", "n"}:
        return "0"
    raise ValueError("auto_chat must be one of: on/off, true/false, 1/0")


def _persist_env_to_mcp_config(
    config_path: str,
    server_name: str,
    output_device: str | int | None,
    auto_chat: str | bool | int | None,
) -> dict:
    target = Path(config_path)
    if not target.exists():
        raise FileNotFoundError(f"MCP config not found: {target}")

    data = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("MCP config root must be a JSON object")

    servers = data.setdefault("servers", {})
    if not isinstance(servers, dict):
        raise ValueError("MCP config 'servers' must be a JSON object")

    server_cfg = servers.setdefault(server_name, {})
    if not isinstance(server_cfg, dict):
        raise ValueError(f"Server '{server_name}' must be a JSON object")

    env = server_cfg.setdefault("env", {})
    if not isinstance(env, dict):
        raise ValueError(f"Server '{server_name}.env' must be a JSON object")

    changed = {}
    if output_device is not None:
        env["POCKETTTS_OUTPUT_DEVICE"] = str(output_device)
        changed["POCKETTTS_OUTPUT_DEVICE"] = env["POCKETTTS_OUTPUT_DEVICE"]

    auto_chat_norm = _normalize_auto_chat(auto_chat)
    if auto_chat_norm is not None:
        env["POCKETTTS_AUTO_CHAT"] = auto_chat_norm
        changed["POCKETTTS_AUTO_CHAT"] = auto_chat_norm

    target.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return {
        "config_path": str(target),
        "server": server_name,
        "persisted": changed,
    }


@mcp.tool(description="Simple health check for PocketTTS MCP server.")
def health() -> dict:
    return {"ok": True, "service": "PocketTTS-MCP"}


@mcp.tool(description="List built-in PocketTTS voice names.")
def list_voices() -> list[str]:
    return core_list_voices()


@mcp.tool(description="List available local output audio devices for explicit playback routing.")
def list_output_devices() -> list[dict]:
    return core_list_output_devices()


@mcp.tool(description="Get current audio routing env values used by PocketTTS playback.")
def get_audio_routing() -> dict:
    return {
        "POCKETTTS_OUTPUT_DEVICE": os.getenv("POCKETTTS_OUTPUT_DEVICE"),
        "POCKETTTS_AUTO_CHAT": os.getenv("POCKETTTS_AUTO_CHAT", "1"),
    }


@mcp.tool(description="Set audio routing for this MCP process, and optionally persist to MCP config JSON.")
def set_audio_routing(
    output_device: str | int | None = None,
    auto_chat: str | bool | int | None = None,
    persist_to_config: bool = False,
    config_path: str | None = None,
    server_name: str = "pockettts-local",
) -> dict:
    if output_device is None and auto_chat is None:
        raise ValueError("Provide output_device and/or auto_chat")

    changed_runtime = {}
    if output_device is not None:
        os.environ["POCKETTTS_OUTPUT_DEVICE"] = str(output_device)
        changed_runtime["POCKETTTS_OUTPUT_DEVICE"] = os.environ["POCKETTTS_OUTPUT_DEVICE"]

    auto_chat_norm = _normalize_auto_chat(auto_chat)
    if auto_chat_norm is not None:
        os.environ["POCKETTTS_AUTO_CHAT"] = auto_chat_norm
        changed_runtime["POCKETTTS_AUTO_CHAT"] = auto_chat_norm

    persisted = None
    if persist_to_config:
        target_path = (config_path or "").strip() or DEFAULT_MCP_CONFIG_PATH
        if not target_path:
            raise ValueError(
                "config_path is required when persist_to_config=True unless POCKETTTS_MCP_CONFIG_PATH is set"
            )
        persisted = _persist_env_to_mcp_config(
            config_path=target_path,
            server_name=server_name,
            output_device=output_device,
            auto_chat=auto_chat,
        )

    return {
        "runtime": changed_runtime,
        "persisted": persisted,
    }


@mcp.tool(description="Generate speech from text and write a WAV file.")
def synthesize(
    text: str,
    voice: str = resolve_default_voice(),
    output_path: str | None = None,
) -> dict:
    return synthesize_to_wav(text=text, voice=voice, output_path=output_path)


@mcp.tool(description="Generate speech in chunked mode and write chunk WAV files.")
def synthesize_chunked(
    text: str,
    voice: str = resolve_default_voice(),
    chunk_size: int = 180,
    output_dir: str | None = None,
    merged_output_path: str | None = None,
    merge_output: bool = True,
) -> dict:
    return synthesize_chunked_to_wavs(
        text=text,
        voice=voice,
        chunk_size=chunk_size,
        output_dir=output_dir,
        merged_output_path=merged_output_path,
        merge_output=merge_output,
    )


@mcp.tool(description="Generate speech and immediately play it on local machine (Windows).")
def speak_now(
    text: str,
    voice: str = resolve_default_voice(),
    output_path: str | None = None,
    block: bool = True,
    keep_file: bool = False,
    output_device: str | int | None = None,
) -> dict:
    return speak_now_local(
        text=text,
        voice=voice,
        output_path=output_path,
        block=block,
        keep_file=keep_file,
        output_device=output_device,
    )


@mcp.tool(description="Create a reusable voice embedding from an audio sample.")
def create_voice(
    voice_name: str,
    audio_path: str,
    overwrite: bool = False,
) -> dict:
    return create_voice_embedding(
        voice_name=voice_name,
        audio_path=audio_path,
        overwrite=overwrite,
    )


if __name__ == "__main__":
    try:
        _start_gui_sidecar()
        mcp.run()
    except KeyboardInterrupt:
        print("PocketTTS-MCP stopped.")
