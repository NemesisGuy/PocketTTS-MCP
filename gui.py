import os

import gradio as gr

from tts_core import create_voice_embedding
from tts_core import list_voices
from tts_core import resolve_default_voice
from tts_core import synthesize_chunked_to_wavs
from tts_core import synthesize_to_wav


def _run_generation(
    text: str,
    voice: str,
    use_chunked: bool,
    chunk_size: int,
    output_path: str,
):
    output_path = (output_path or "").strip() or None

    if use_chunked:
        result = synthesize_chunked_to_wavs(
            text=text,
            voice=voice,
            chunk_size=chunk_size,
            merged_output_path=output_path,
            merge_output=True,
        )
        audio_path = result.get("merged_output_path")
        status = (
            f"Generated {result['chunk_count']} chunks in "
            f"{result['generation_seconds']}s."
        )
        return status, result, audio_path

    result = synthesize_to_wav(text=text, voice=voice, output_path=output_path)
    status = f"Generated in {result['generation_seconds']}s."
    return status, result, result.get("output_path")


def _refresh_voice_dropdown():
    voices = list_voices()
    default_voice = resolve_default_voice()
    return gr.update(choices=voices, value=default_voice if default_voice in voices else (voices[0] if voices else None))


def _save_voice_embedding(voice_name: str, audio_sample: str, overwrite: bool):
    if not audio_sample:
        raise gr.Error("Upload an audio sample first.")
    if not voice_name or not voice_name.strip():
        raise gr.Error("Enter a voice name.")

    result = create_voice_embedding(
        voice_name=voice_name,
        audio_path=audio_sample,
        overwrite=overwrite,
    )
    voices = list_voices()
    status = f"Saved voice '{result['voice']}'"
    return status, result, gr.update(choices=voices, value=result["voice"])


def create_app() -> gr.Blocks:
    with gr.Blocks(title="PocketTTS GUI") as app:
        gr.Markdown("# PocketTTS GUI")
        gr.Markdown("Local text-to-speech with PocketTTS.")

        text = gr.Textbox(label="Text", lines=6, placeholder="Type text to synthesize...")
        voice = gr.Dropdown(
            label="Voice",
            choices=list_voices(),
            value=resolve_default_voice(),
            allow_custom_value=True,
        )
        use_chunked = gr.Checkbox(label="Use chunked generation", value=False)
        chunk_size = gr.Slider(
            label="Chunk size (chars)",
            minimum=80,
            maximum=400,
            step=10,
            value=180,
        )
        output_path = gr.Textbox(
            label="Output path (optional)",
            placeholder="outputs/my_tts.wav",
        )

        generate = gr.Button("Generate", variant="primary")
        refresh_voices = gr.Button("Refresh voices")
        status = gr.Textbox(label="Status")
        metadata = gr.JSON(label="Metadata")
        audio = gr.Audio(label="Audio", type="filepath")

        generate.click(
            fn=_run_generation,
            inputs=[text, voice, use_chunked, chunk_size, output_path],
            outputs=[status, metadata, audio],
        )

        refresh_voices.click(
            fn=_refresh_voice_dropdown,
            outputs=[voice],
        )

        gr.Markdown("## Voice Cloning")
        clone_voice_name = gr.Textbox(
            label="New voice name",
            placeholder="my-voice",
        )
        clone_audio = gr.Audio(
            label="Audio sample (WAV/MP3)",
            type="filepath",
            sources=["upload", "microphone"],
        )
        clone_overwrite = gr.Checkbox(label="Overwrite existing", value=False)
        clone_button = gr.Button("Save embedding", variant="secondary")
        clone_status = gr.Textbox(label="Clone status")
        clone_metadata = gr.JSON(label="Clone metadata")

        clone_button.click(
            fn=_save_voice_embedding,
            inputs=[clone_voice_name, clone_audio, clone_overwrite],
            outputs=[clone_status, clone_metadata, voice],
        )

    return app


def main() -> None:
    app = create_app()
    app.launch(
        server_name="0.0.0.0",
        server_port=int(os.getenv("POCKETTTS_GUI_PORT", "7860")),
        theme=gr.themes.Soft(),
    )


if __name__ == "__main__":
    main()
