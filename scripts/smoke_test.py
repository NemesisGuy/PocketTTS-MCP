from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from server import list_voices, speak_now, synthesize


def main() -> None:
    voices = list_voices()
    print({"voices": voices})

    out = Path("outputs") / "smoke_quick.wav"
    result = synthesize("PocketTTS smoke test is green.", output_path=str(out))
    print({"synthesize": result})

    preview = Path("outputs") / "smoke_preview.wav"
    spoken = speak_now(
        "Smoke test complete. Default voice is active.",
        block=False,
        output_path=str(preview),
    )
    print({"speak_now": spoken})


if __name__ == "__main__":
    main()
