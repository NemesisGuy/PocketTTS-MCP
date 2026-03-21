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
- `list_output_devices()`
- `get_audio_routing()`
- `set_audio_routing(output_device=None, auto_chat=None, persist_to_config=False, config_path=None, server_name="pockettts-local")`
- `synthesize(text, voice="alba", output_path=None)`
- `synthesize_chunked(text, voice="alba", chunk_size=180, output_dir=None, merged_output_path=None, merge_output=True)`
- `speak_now(text, voice="alba", output_path=None, block=True)`
- `speak_now(text, voice="alba", output_path=None, block=True, keep_file=False, output_device=None)`
- `synthesize(text, voice="bricktop", output_path=None)` (default when available)
- `synthesize_chunked(text, voice="bricktop", chunk_size=180, output_dir=None, merged_output_path=None, merge_output=True)` (default when available)
- `speak_now(text, voice="bricktop", output_path=None, block=True, output_device=None)` (default when available)
- `create_voice(voice_name, audio_path, overwrite=False)`

If `output_path` is not provided, audio files are written to `outputs/tts_<timestamp>.wav`.

For chunked generation, chunk WAV files are written into an output folder and can optionally be merged into one file.

Use `speak_now(...)` when you want the tool call to immediately play audio on your local Windows machine.
By default, `speak_now` plays from memory and does not save a WAV file unless you set `keep_file=True` or provide `output_path`.
Automatic routing: if your current Windows default output is an Arctis/Sonar **Game** device, PocketTTS will auto-route playback to the matching **Chat** device for that call.
If headset routing is not applicable, it falls back to normal system output behavior.

### Optional: Route Playback To Arctis Chat

If you use SteelSeries Arctis and want TTS to go to Chat only sometimes, use optional device routing.

1. In Windows Sound settings, confirm both output devices are present:
	 - `Headphones (Arctis 7 Game)`
	 - `Headset Earphone (Arctis 7 Chat)`
2. Set default output to `Headphones (Arctis 7 Game)`.
3. Set default communication device to `Headset Earphone (Arctis 7 Chat)`.
4. In PocketTTS, choose Chat explicitly only when needed:

MCP tool call example:

```json
{
	"text": "Private headset output test.",
	"voice": "bricktop",
	"output_device": "Headset Earphone (Arctis 7 Chat)"
}
```

List available output devices from MCP:

```python
list_output_devices()
```

If a device name appears multiple times (MME, WASAPI, WDM-KS), you can pass a device index instead of a name.

CLI device checks:

```powershell
.\.venv\Scripts\python.exe clients/play_client.py --list-devices
```

CLI playback to Arctis Chat:

```powershell
.\.venv\Scripts\python.exe clients/play_client.py --text "Chat route test" --output-device "Headset Earphone (Arctis 7 Chat)"
```

Optional: write selected output device into MCP config (`POCKETTTS_OUTPUT_DEVICE`):

```powershell
.\.venv\Scripts\python.exe clients/play_client.py --set-mcp-device "Headset Earphone (Arctis 7 Chat)" --mcp-config "C:/Users/Reign/.gemini/antigravity/mcp_config.json" --mcp-server-name "pockettts-local"
```

Optional: update auto-chat behavior only in MCP config (`POCKETTTS_AUTO_CHAT`):

```powershell
.\.venv\Scripts\python.exe clients/play_client.py --set-mcp-auto-chat on --mcp-config "C:/Users/Reign/.gemini/antigravity/mcp_config.json" --mcp-server-name "pockettts-local"
```

Set both device and auto-chat in one command:

```powershell
.\.venv\Scripts\python.exe clients/play_client.py --set-mcp-device "Headset Earphone (Arctis 7 Chat)" --set-mcp-auto-chat off --mcp-config "C:/Users/Reign/.gemini/antigravity/mcp_config.json" --mcp-server-name "pockettts-local"
```

Set MCP config back to normal system output:

```powershell
.\.venv\Scripts\python.exe clients/play_client.py --set-mcp-device system --mcp-config "C:/Users/Reign/.gemini/antigravity/mcp_config.json" --mcp-server-name "pockettts-local"
```

Python device inspection (same concept as your snippet):

```python
import sounddevice as sd
print(sd.query_devices())
```

If you prefer a global optional default for this project, set env var `POCKETTTS_OUTPUT_DEVICE` to device name or index.
Use `POCKETTTS_OUTPUT_DEVICE=system` (or `default`) to force normal system output only.
Use `POCKETTTS_AUTO_CHAT=0` to disable automatic Game -> Chat routing.

### Three Configuration Paths

You can configure routing in 3 ways:

1. MCP tool (agent-driven):

```python
set_audio_routing(output_device="Headset Earphone (Arctis 7 Chat)")
set_audio_routing(auto_chat="off")
set_audio_routing(output_device="system", auto_chat="on", persist_to_config=True, config_path="C:/Users/Reign/.gemini/antigravity/mcp_config.json")
```

2. CLI command (user-driven):

```powershell
.\.venv\Scripts\python.exe clients/play_client.py --set-mcp-device "Headset Earphone (Arctis 7 Chat)" --set-mcp-auto-chat off --mcp-config "C:/Users/Reign/.gemini/antigravity/mcp_config.json" --mcp-server-name "pockettts-local"
```

3. Edit MCP config JSON directly by setting `env` keys under your server entry:

```json
{
	"servers": {
		"pockettts-local": {
			"command": "...",
			"args": ["..."],
			"env": {
				"POCKETTTS_OUTPUT_DEVICE": "system",
				"POCKETTTS_AUTO_CHAT": "1"
			}
		}
	}
}
```

### AGENTS.md Example (Prefer Chat Output)

If you want agent behavior to consistently prefer chat output, add this policy section to your `AGENTS.md`:

```md
## PocketTTS Audio Routing Policy

When generating speech with pockettts-local:

1. Prefer chat output channel first.
2. Before calling `speak_now`, call:
	- `set_audio_routing(output_device="Headset Earphone (Arctis 7 Chat)", auto_chat="off")`
3. Then call `speak_now(...)`.

Fallback behavior:

1. If chat device is unavailable, call:
	- `set_audio_routing(output_device="system", auto_chat="on")`
2. Continue with `speak_now(...)`.

Do not use CLI for routing when MCP tools are available.
Use MCP tools first: `list_output_devices`, `get_audio_routing`, `set_audio_routing`.
```

For hardware-agnostic behavior, replace the explicit Arctis device name with: "pick first output device whose name contains `Chat`; otherwise use `system`".

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

### Example MCP Config (VS Code)

```json
{
	"servers": {
		"pockettts-local": {
			"command": "C:/Users/Reign/Documents/Python Projects/PocketTTS-MCP/.venv/Scripts/python.exe",
			"args": [
				"C:/Users/Reign/Documents/Python Projects/PocketTTS-MCP/server.py"
			],
			"env": {
				"POCKETTTS_AUTOSTART_GUI": "0",
				"POCKETTTS_OUTPUT_DEVICE": "system",
				"POCKETTTS_AUTO_CHAT": "1"
			}
		}
	}
}
```

### Example MCP Config (Google Antigravity)

Antigravity uses `mcpServers` for launch command config. In your setup it can also use a separate `servers` block for env overrides.

```json
{
	"mcpServers": {
		"pockettts-local": {
			"command": "C:\\Users\\Reign\\Documents\\Python Projects\\PocketTTS-MCP\\.venv\\Scripts\\python.exe",
			"args": [
				"C:\\Users\\Reign\\Documents\\Python Projects\\PocketTTS-MCP\\server.py"
			],
			"env": {
				"POCKETTTS_AUTOSTART_GUI": "0",
				"POCKETTTS_MCP_CONFIG_PATH": "C:\\Users\\Reign\\.gemini\\antigravity\\mcp_config.json"
			}
		}
	},
	"servers": {
		"pockettts-local": {
			"env": {
				"POCKETTTS_OUTPUT_DEVICE": "40",
				"POCKETTTS_AUTO_CHAT": "0"
			}
		}
	}
}
```
