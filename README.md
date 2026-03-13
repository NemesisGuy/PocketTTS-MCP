# PocketTTS-MCP

PocketTTS-MCP starter workspace for downloading and preparing a local PocketTTS model for an MCP server.

## What this includes

- A token-based Hugging Face model downloader script.
- Local project setup for Python dependencies.
- Safe defaults to keep secrets and model files out of git.
- An MCP server entrypoint with synth tools and voice listing.
- A local web GUI.
- Docker and docker-compose support.

## Prerequisites

- Python 3.10+
- A valid Hugging Face access token in `secrets.env`

## Quick Start

1. Create and activate a virtual environment:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

3. Ensure `secrets.env` contains your token:

```env
HUGGINGFACE_HUB_TOKEN=hf_xxx
```

4. Download the default PocketTTS model (`kyutai/pocket-tts`):

```powershell
.\.venv\Scripts\python.exe scripts/download_model.py
```

The model will be downloaded to `models/pocket-tts` by default.

## Run Instructions

From project root:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Run MCP server (stdio):

```powershell
.\.venv\Scripts\python.exe server.py
```

Important: this is a stdio server for MCP clients. Do not type random text or press Enter in that terminal after launch. Any manual input is treated as JSON-RPC and can produce `Invalid JSON` errors.
By default, starting MCP also launches the Gradio GUI sidecar on port 7860.
It will try to open your browser automatically.

If sidecar GUI does not appear, check:

- `http://localhost:7860`
- `outputs/gui_sidecar.log` for startup errors

Disable sidecar launch if needed:

```powershell
$env:POCKETTTS_AUTOSTART_GUI="0"
.\.venv\Scripts\python.exe server.py
```

Run GUI:

```powershell
.\.venv\Scripts\python.exe gui.py
```

Run local client:

```powershell
.\.venv\Scripts\python.exe clients/play_client.py --text "PocketTTS is ready"
```

Note: `--text` is required for `play_client.py`.

Default voice preference is `bricktop` when available.

Run Docker GUI:

```powershell
docker compose up --build
```

## Optional: Custom Model or Output Path

```powershell
.\.venv\Scripts\python.exe scripts/download_model.py --model-id kyutai/pocket-tts --output-dir models/pockettts-main
```

## Smoke Test

```powershell
.\.venv\Scripts\python.exe scripts/smoke_test.py
```

## Next Step for MCP Server

The project includes [server.py](server.py), which exposes PocketTTS tools over MCP stdio.

### Start the MCP server

```powershell
.\.venv\Scripts\python.exe server.py
```

### Exposed tools

- `health()`
- `list_voices()`
- `synthesize(text, voice="alba", output_path=None)`
- `synthesize_chunked(text, voice="alba", chunk_size=180, output_dir=None, merged_output_path=None, merge_output=True)`
- `speak_now(text, voice="alba", output_path=None, block=True)`
- `speak_now(text, voice="alba", output_path=None, block=True, keep_file=False)`
- `synthesize(text, voice="bricktop", output_path=None)` (default when available)
- `synthesize_chunked(text, voice="bricktop", chunk_size=180, output_dir=None, merged_output_path=None, merge_output=True)` (default when available)
- `speak_now(text, voice="bricktop", output_path=None, block=True)` (default when available)
- `create_voice(voice_name, audio_path, overwrite=False)`

If `output_path` is not provided, audio files are written to `outputs/tts_<timestamp>.wav`.

For chunked generation, chunk WAV files are written into an output folder and can optionally be merged into one file.

Use `speak_now(...)` when you want the tool call to immediately play audio on your local Windows machine.
By default, `speak_now` plays from memory and does not save a WAV file unless you set `keep_file=True` or provide `output_path`.

## Local GUI

Start the GUI:

```powershell
.\.venv\Scripts\python.exe gui.py
```

Then open http://localhost:7860

### Voice Cloning In GUI

1. Open the GUI.
2. In **Voice Cloning**, enter a new voice name.
3. Upload or record an audio sample.
4. Click **Save embedding**.
5. The new voice is saved to `voice_embeddings/<name>.safetensors` and appears in the voice dropdown.

After that, use the saved voice name in GUI, MCP tools, or the local client.

## Tiny Local Client (Generate + Autoplay)

```powershell
.\.venv\Scripts\python.exe clients/play_client.py --text "Yo bro, PocketTTS is online."
```

On Windows, it auto-plays the WAV after generation.

## Docker

Build and run GUI in Docker:

```powershell
docker compose up --build
```

This serves the GUI on port 7860 and mounts:

- `./models` to persist model files
- `./outputs` to persist generated audio

To run MCP mode in Docker instead of GUI:

```powershell
docker run --rm -it --env-file secrets.env -e POCKETTTS_MODE=mcp pockettts-mcp
```

### Example MCP config snippet

```json
{
	"servers": {
		"pockettts-local": {
			"command": "C:/Users/Reign/Documents/Python Projects/PocketTTS-MCP/.venv/Scripts/python.exe",
			"args": [
				"C:/Users/Reign/Documents/Python Projects/PocketTTS-MCP/server.py"
			]
		}
	}
}
```
