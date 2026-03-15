import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tts_core import list_output_devices
from tts_core import play_audio_file
from tts_core import resolve_default_voice
from tts_core import synthesize_to_wav


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate speech and play it locally.")
    parser.add_argument("--text", help="Text to synthesize")
    parser.add_argument(
        "--voice",
        default=resolve_default_voice(),
        help="Voice name or prompt path",
    )
    parser.add_argument("--output", default="outputs/client.wav", help="Output wav path")
    parser.add_argument("--no-play", action="store_true", help="Do not play audio")
    parser.add_argument(
        "--output-device",
        default=None,
        help="Optional output device name or index (for example: 'Headset Earphone (Arctis 7 Chat)').",
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="List output audio devices and exit.",
    )
    parser.add_argument(
        "--set-mcp-device",
        default=None,
        help="Optional device name/index (or 'system') to save into MCP config as POCKETTTS_OUTPUT_DEVICE.",
    )
    parser.add_argument(
        "--set-mcp-auto-chat",
        default=None,
        help="Optional auto-chat setting to save into MCP config as POCKETTTS_AUTO_CHAT (on/off, true/false, 1/0).",
    )
    parser.add_argument(
        "--mcp-config",
        default=None,
        help="Path to MCP config JSON file (for --set-mcp-device).",
    )
    parser.add_argument(
        "--mcp-server-name",
        default="pockettts-local",
        help="Server key inside MCP config (default: pockettts-local).",
    )
    return parser.parse_args()


def _coerce_device(value: str | None) -> str | int | None:
    if value is None:
        return None
    trimmed = value.strip()
    if not trimmed:
        return None
    if trimmed.isdigit():
        return int(trimmed)
    return trimmed


def _update_mcp_config_device(
    config_path: str,
    server_name: str,
    device_value: str | None = None,
    auto_chat_value: str | None = None,
) -> dict:
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"MCP config not found: {path}")

    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)

    if not isinstance(data, dict):
        raise ValueError("MCP config root must be a JSON object")

    servers = data.setdefault("servers", {})
    if not isinstance(servers, dict):
        raise ValueError("MCP config 'servers' must be a JSON object")

    server = servers.setdefault(server_name, {})
    if not isinstance(server, dict):
        raise ValueError(f"Server '{server_name}' must be a JSON object")

    env = server.setdefault("env", {})
    if not isinstance(env, dict):
        raise ValueError(f"Server '{server_name}.env' must be a JSON object")

    changed = {}

    if device_value is not None:
        env["POCKETTTS_OUTPUT_DEVICE"] = str(device_value)
        changed["POCKETTTS_OUTPUT_DEVICE"] = env["POCKETTTS_OUTPUT_DEVICE"]

    if auto_chat_value is not None:
        normalized = auto_chat_value.strip().lower()
        if normalized in {"1", "true", "on", "yes", "y"}:
            env["POCKETTTS_AUTO_CHAT"] = "1"
        elif normalized in {"0", "false", "off", "no", "n"}:
            env["POCKETTTS_AUTO_CHAT"] = "0"
        else:
            raise ValueError(
                "--set-mcp-auto-chat must be one of: on/off, true/false, 1/0"
            )
        changed["POCKETTTS_AUTO_CHAT"] = env["POCKETTTS_AUTO_CHAT"]

    if not changed:
        raise ValueError("Provide --set-mcp-device and/or --set-mcp-auto-chat")

    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    result = {
        "config_path": str(path),
        "server": server_name,
    }
    result.update(changed)
    return result


def main() -> None:
    args = parse_args()

    if args.set_mcp_device is not None or args.set_mcp_auto_chat is not None:
        config_path = (args.mcp_config or "").strip()
        if not config_path:
            raise ValueError(
                "--mcp-config is required when using --set-mcp-device or --set-mcp-auto-chat"
            )
        result = _update_mcp_config_device(
            config_path=config_path,
            server_name=args.mcp_server_name,
            device_value=args.set_mcp_device,
            auto_chat_value=args.set_mcp_auto_chat,
        )
        print(result)
        return

    if args.list_devices:
        devices = list_output_devices()
        print("Output devices:")
        for dev in devices:
            print(
                f"[{dev['index']}] {dev['name']} "
                f"(hostapi={dev['hostapi']}, channels={dev['max_output_channels']})"
            )
        return

    if not args.text or not args.text.strip():
        raise ValueError(
            "--text is required unless using --list-devices or MCP config set flags"
        )

    result = synthesize_to_wav(text=args.text, voice=args.voice, output_path=args.output)
    output_file = Path(result["output_path"])
    print(result)

    if args.no_play:
        return

    playback = play_audio_file(
        str(output_file),
        block=True,
        output_device=_coerce_device(args.output_device),
    )
    print({"playback": playback})


if __name__ == "__main__":
    main()
