from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    """Demo simple cote client.

    Cette demo ne remplace pas un client MCP complet, mais elle montre le principe :
    un programme externe consomme les memes capacites exposees par le serveur MCP
    sans importer directement la logique metier dans l'interface utilisateur.
    """
    command = [
        str(ROOT / ".venv" / "Scripts" / "python.exe"),
        str(ROOT / "source" / "run_demo.py"),
    ]
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    output = {
        "client": "mcp_client_demo",
        "server_capability": "run_market_watch",
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    if completed.returncode:
        sys.exit(completed.returncode)


if __name__ == "__main__":
    main()

