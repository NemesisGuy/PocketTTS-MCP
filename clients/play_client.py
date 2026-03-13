import argparse
import platform
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tts_core import resolve_default_voice, synthesize_to_wav


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate speech and play it locally.")
    parser.add_argument("--text", required=True, help="Text to synthesize")
    parser.add_argument(
        "--voice",
        default=resolve_default_voice(),
        help="Voice name or prompt path",
    )
    parser.add_argument("--output", default="outputs/client.wav", help="Output wav path")
    parser.add_argument("--no-play", action="store_true", help="Do not play audio")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = synthesize_to_wav(text=args.text, voice=args.voice, output_path=args.output)
    output_file = Path(result["output_path"])
    print(result)

    if args.no_play:
        return

    if platform.system() == "Windows":
        import winsound

        winsound.PlaySound(str(output_file), winsound.SND_FILENAME)
    else:
        print("Auto-play is only wired for Windows in this client script.")


if __name__ == "__main__":
    main()
