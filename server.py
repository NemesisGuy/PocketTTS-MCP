from mcp.server.fastmcp import FastMCP
from tts_core import list_voices as core_list_voices
from tts_core import synthesize_chunked_to_wavs
from tts_core import synthesize_to_wav

mcp = FastMCP("PocketTTS-MCP")


@mcp.tool(description="Simple health check for PocketTTS MCP server.")
def health() -> dict:
    return {"ok": True, "service": "PocketTTS-MCP"}


@mcp.tool(description="List built-in PocketTTS voice names.")
def list_voices() -> list[str]:
    return core_list_voices()


@mcp.tool(description="Generate speech from text and write a WAV file.")
def synthesize(
    text: str,
    voice: str = "alba",
    output_path: str | None = None,
) -> dict:
    return synthesize_to_wav(text=text, voice=voice, output_path=output_path)


@mcp.tool(description="Generate speech in chunked mode and write chunk WAV files.")
def synthesize_chunked(
    text: str,
    voice: str = "alba",
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


if __name__ == "__main__":
    mcp.run()
