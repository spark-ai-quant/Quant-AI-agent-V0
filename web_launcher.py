from __future__ import annotations

import os
import socket
import sys
from pathlib import Path

from streamlit.web import bootstrap, cli as st_cli


INNER_PROJECT_PARTS = ("Quant-AI-agent-main", "Quant-AI-agent-main")
STREAMLIT_APP_NAME = "streamlit_app.py"


def get_runtime_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def get_inner_project_root(base_dir: Path | None = None) -> Path:
    root = base_dir or get_runtime_root()
    return root.joinpath(*INNER_PROJECT_PARTS)


def get_streamlit_app_path(base_dir: Path | None = None) -> Path:
    return get_inner_project_root(base_dir) / STREAMLIT_APP_NAME


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        return sock.getsockname()[1]


def validate_project_layout(project_root: Path) -> None:
    required_paths = (
        project_root / "main.py",
        project_root / "streamlit_app.py",
        project_root / "agent",
        project_root / "templates",
    )

    missing = [str(path) for path in required_paths if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "Missing packaged project files:\n" + "\n".join(missing)
        )


def build_streamlit_flags(port: int) -> dict[str, object]:
    return {
        "global.developmentMode": False,
        "server.headless": False,
        "server.port": port,
        "server.address": "127.0.0.1",
        "browser.gatherUsageStats": False,
        "browser.serverAddress": "127.0.0.1",
        "server.fileWatcherType": "none",
    }


def launch() -> None:
    runtime_root = get_runtime_root()
    project_root = get_inner_project_root(runtime_root)
    app_path = get_streamlit_app_path(runtime_root)
    validate_project_layout(project_root)

    port = find_free_port()
    app_url = f"http://127.0.0.1:{port}"

    os.chdir(project_root)
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # Keep Streamlit in end-user mode and suppress analytics prompts.
    os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    os.environ["STREAMLIT_GLOBAL_DEVELOPMENT_MODE"] = "false"
    os.environ["STREAMLIT_SERVER_HEADLESS"] = "false"
    os.environ["STREAMLIT_SERVER_FILE_WATCHER_TYPE"] = "none"
    flags = build_streamlit_flags(port)
    bootstrap.load_config_options(flag_options=flags)
    st_cli.check_credentials()

    print(f"Project root: {project_root}")
    print(f"Starting local web app at: {app_url}")
    print("If the browser does not open automatically, visit the URL above.")
    print("Close this window to stop the web app.")

    bootstrap.run(
        str(app_path),
        False,
        [],
        flags,
    )


if __name__ == "__main__":
    launch()
