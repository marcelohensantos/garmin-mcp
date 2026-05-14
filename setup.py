#!/usr/bin/env python3
"""Interactive setup — creates .env, installs deps, tests connection, prints MCP config."""
import getpass
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
VENV = ROOT / ".venv"
PYTHON = VENV / "bin" / "python"
PIP = VENV / "bin" / "pip"


def _bold(s):  return f"\033[1m{s}\033[0m"
def _green(s): return f"\033[32m{s}\033[0m"
def _red(s):   return f"\033[31m{s}\033[0m"
def _dim(s):   return f"\033[2m{s}\033[0m"


def header(title):
    print(f"\n{_bold(title)}")
    print("─" * len(title))


def ok(msg):  print(f"  {_green('✓')}  {msg}")
def fail(msg): print(f"  {_red('✗')}  {msg}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Step 1 — credentials
# ---------------------------------------------------------------------------

def setup_credentials():
    header("Garmin Connect credentials")
    env_path = ROOT / ".env"

    if env_path.exists():
        print("  .env already exists. Overwrite? [y/N] ", end="", flush=True)
        if input().strip().lower() != "y":
            ok("Keeping existing .env")
            return

    email    = input("  Email: ").strip()
    password = getpass.getpass("  Password: ")
    env_path.write_text(f"GARMIN_EMAIL={email}\nGARMIN_PASSWORD={password}\n")
    ok(".env created")


# ---------------------------------------------------------------------------
# Step 2 — virtual environment + dependencies
# ---------------------------------------------------------------------------

def setup_venv():
    header("Installing dependencies")

    if not VENV.exists():
        print("  Creating virtual environment...", flush=True)
        subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)

    print("  Installing requirements...", flush=True)
    subprocess.run(
        [str(PIP), "install", "-q", "-r", str(ROOT / "requirements.txt")],
        check=True,
    )
    ok("Dependencies ready")


# ---------------------------------------------------------------------------
# Step 3 — connection test
# ---------------------------------------------------------------------------

def test_connection():
    header("Testing Garmin Connect")
    result = subprocess.run(
        [str(PYTHON), str(ROOT / "src" / "check.py")],
        env={**__import__("os").environ, "PYTHONPATH": str(ROOT / "src")},
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        fail("Connection failed:")
        print(result.stderr or result.stdout)
        print(
            "\n  Hint: if this is your first login, the OAuth flow may need"
            "\n  a one-time browser confirmation. Check your Garmin email for"
            "\n  a verification link, then run  make check  manually."
        )
        sys.exit(1)

    for line in result.stdout.splitlines():
        print(f"  {line}")


# ---------------------------------------------------------------------------
# Step 4 — print MCP config
# ---------------------------------------------------------------------------

def print_mcp_config():
    header("MCP client configuration")
    server = ROOT / "src" / "server.py"
    config = f"""\
  {{
    "mcpServers": {{
      "garmin": {{
        "command": "{PYTHON}",
        "args": ["{server}"]
      }}
    }}
  }}"""

    print(f"\n  {_bold('Claude Desktop')} — add to claude_desktop_config.json:")
    print(f"\n{config}")
    print(f"\n  {_bold('Claude Code')} — add to .mcp.json at your project root:")
    print(f"\n{config}")
    print(f"\n  {_dim('Restart the client after saving.')}\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print(f"\n{_bold('Garmin MCP — setup')}")
    print("══════════════════")

    setup_credentials()
    setup_venv()
    test_connection()
    print_mcp_config()


if __name__ == "__main__":
    main()
