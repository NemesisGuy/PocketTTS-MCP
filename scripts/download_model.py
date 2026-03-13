import argparse
import os
from pathlib import Path

from dotenv import load_dotenv
from huggingface_hub import snapshot_download


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download a PocketTTS model from Hugging Face."
    )
    parser.add_argument(
        "--model-id",
        default=os.getenv("HF_MODEL_ID", "kyutai/pocket-tts"),
        help="Hugging Face model repo id (default: kyutai/pocket-tts)",
    )
    parser.add_argument(
        "--output-dir",
        default=os.getenv("HF_MODEL_DIR", "models/pocket-tts"),
        help="Local directory to store model files",
    )
    parser.add_argument(
        "--env-file",
        default="secrets.env",
        help="Path to env file containing HUGGINGFACE_HUB_TOKEN",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    env_path = Path(args.env_file)
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)

    token = os.getenv("HUGGINGFACE_HUB_TOKEN")
    if not token:
        raise RuntimeError(
            "Missing HUGGINGFACE_HUB_TOKEN. Add it to secrets.env or export it in your shell."
        )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Downloading '{args.model_id}' into '{output_dir}'...")
    snapshot_download(
        repo_id=args.model_id,
        local_dir=str(output_dir),
        token=token,
    )
    print("Model download complete.")


if __name__ == "__main__":
    main()
