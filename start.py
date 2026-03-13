import os


def main() -> None:
    mode = os.getenv("POCKETTTS_MODE", "gui").strip().lower()

    if mode == "mcp":
        from server import mcp

        mcp.run()
        return

    from gui import main as run_gui

    run_gui()


if __name__ == "__main__":
    main()
