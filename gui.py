import gradio as gr

from tts_core import list_voices, synthesize_chunked_to_wavs, synthesize_to_wav


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


def create_app() -> gr.Blocks:
    with gr.Blocks(title="PocketTTS GUI") as app:
        gr.Markdown("# PocketTTS GUI")
        gr.Markdown("Local text-to-speech with PocketTTS.")

        text = gr.Textbox(label="Text", lines=6, placeholder="Type text to synthesize...")
        voice = gr.Dropdown(
            label="Voice",
            choices=list_voices(),
            value="alba",
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
        status = gr.Textbox(label="Status")
        metadata = gr.JSON(label="Metadata")
        audio = gr.Audio(label="Audio", type="filepath")

        generate.click(
            fn=_run_generation,
            inputs=[text, voice, use_chunked, chunk_size, output_path],
            outputs=[status, metadata, audio],
        )

    return app


def main() -> None:
    app = create_app()
    app.launch(server_name="0.0.0.0", server_port=7860, theme=gr.themes.Soft())


if __name__ == "__main__":
    main()
