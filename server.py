import os
import subprocess
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from tts_core import create_voice_embedding
from tts_core import list_voices as core_list_voices
from tts_core import play_audio_file
from tts_core import resolve_default_voice
from tts_core import synthesize_chunked_to_wavs
from tts_core import synthesize_to_wav

mcp = FastMCP("PocketTTS-MCP")
BASE_DIR = Path(__file__).resolve().parent
GUI_PORT = os.getenv("POCKETTTS_GUI_PORT", "7860")


def _start_gui_sidecar() -> None:
    if os.getenv("POCKETTTS_AUTOSTART_GUI", "1") != "1":
        return

    env = os.environ.copy()
    env.setdefault("POCKETTTS_GUI_PORT", GUI_PORT)
    subprocess.Popen(
        [sys.executable, str(BASE_DIR / "gui.py")],
        cwd=str(BASE_DIR),
        env=env,
    )


@mcp.tool(description="Simple health check for PocketTTS MCP server.")
def health() -> dict:
    return {"ok": True, "service": "PocketTTS-MCP"}


@mcp.tool(description="List built-in PocketTTS voice names.")
def list_voices() -> list[str]:
    return core_list_voices()


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
) -> dict:
    result = synthesize_to_wav(text=text, voice=voice, output_path=output_path)
    playback = play_audio_file(result["output_path"], block=block)
    result["playback"] = playback
    return result


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
    _start_gui_sidecar()
    mcp.run()
