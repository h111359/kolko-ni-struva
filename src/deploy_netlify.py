"""
deploy_netlify.py: Netlify deployment script for the React Analytics App.
Part of the kolko-ni-struva ETL pipeline (request R-20260425-1304).
Responsibilities: detect Netlify CLI availability, load deployment credentials
from environment variables or the project-root .env file (with interactive
fallback and auto-save on first use), build the React app via npm, and
deploy to Netlify. Falls back to manual deploy instructions when CLI is absent.

Credential loading precedence:
  1. Shell environment variable (highest priority).
  2. Project-root .env file (loaded via python-dotenv at import time).
  3. Interactive prompt (lowest priority; value auto-saved to .env for reuse).
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv, set_key


# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------
BASE_DIR: Path = Path(__file__).resolve().parent.parent
REACT_APP_DIR: Path = BASE_DIR / "react-app"
REACT_DIST_DIR: Path = REACT_APP_DIR / "dist"

# Project-root .env file used for persistent credential storage.
_ENV_FILE_PATH: Path = BASE_DIR / ".env"

# Environment variable names recognised by the Netlify CLI natively.
ENV_AUTH_TOKEN: str = "NETLIFY_AUTH_TOKEN"
ENV_SITE_ID: str = "NETLIFY_SITE_ID"

# Keys present in the shell before .env is loaded.  Used to distinguish
# shell-provided credentials from .env-file-provided credentials in logs.
_SHELL_ENV_KEYS: frozenset[str] = frozenset(os.environ.keys())

# Load project-root .env into os.environ.  By default load_dotenv does NOT
# override variables that are already set in the shell environment.
load_dotenv(_ENV_FILE_PATH)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def find_netlify_cmd() -> list[str] | None:
    """
    Resolve the Netlify CLI invocation command.

    Prefers a globally installed `netlify` binary. Does not attempt `npx` to
    avoid the interactive package-installation prompt that `npx` shows on
    first use when the package is not cached.

    Returns:
        A list representing the base command (e.g. ``['netlify']``), or
        ``None`` if no usable Netlify CLI binary is found on PATH.
    """
    if shutil.which("netlify"):
        return ["netlify"]
    return None


def print_manual_instructions() -> None:
    """
    Print step-by-step manual deployment instructions to stdout.

    Displayed when the Netlify CLI is not available on the operator's PATH.
    Instructions guide the operator through building the React app locally
    and uploading the artefact via the Netlify dashboard drag-and-drop UI.

    Side effects:
        Writes formatted instructions to stdout.
    """
    print()
    print("=" * 60)
    print("  Manual Deploy Instructions — React App to Netlify")
    print("=" * 60)
    print()
    print("  The Netlify CLI was not found on this machine.")
    print("  Follow these steps to deploy manually (all tiers, including free):")
    print()
    print("  Step 1 — Install Netlify CLI (optional, for future automated deploys):")
    print("    npm install -g netlify-cli")
    print()
    print("  Step 2 — Build the React app:")
    print("    cd react-app")
    print("    npm install      # first time only")
    print("    npm run build    # produces react-app/dist/")
    print()
    print("  Step 3 — Deploy via Netlify dashboard (drag-and-drop):")
    print("    a. Open https://app.netlify.com in your browser.")
    print("    b. Log in to your Netlify account.")
    print("    c. Navigate to your site (or create a new one).")
    print("    d. Go to: Deploys → Drag and drop your site output here.")
    print("    e. Drag the entire  react-app/dist/  folder onto the drop zone.")
    print("    f. Wait for the deploy to complete and note the deploy URL.")
    print()
    print("  Step 4 (alternative) — Deploy via Netlify CLI once installed:")
    print("    netlify login")
    print("    netlify link                    # link to your site")
    print("    cd react-app && npm run build")
    print("    netlify deploy --prod --dir dist")
    print()
    print("=" * 60)
    print()


def get_credential(env_var: str, label: str, instructions: str) -> str:
    """
    Return a required credential using the configured precedence chain.

    Precedence (highest to lowest):
      1. Shell environment variable — if set before this process started.
      2. .env file — loaded by ``load_dotenv`` at module import time.
      3. Interactive prompt — printed with acquisition ``instructions``.

    Args:
        env_var: Name of the environment variable to check first.
        label: Human-readable label for the credential (used in prompt text).
        instructions: Multi-line acquisition instructions printed before the
                      prompt when the env var is absent.

    Returns:
        The credential value as a stripped string.

    Raises:
        SystemExit: If the operator provides an empty value when prompted.
    """
    value = os.environ.get(env_var, "").strip()
    if value:
        # Differentiate shell env vars from values loaded from .env file.
        source = "environment variable" if env_var in _SHELL_ENV_KEYS else ".env file"
        print(f"  {label}: read from {source}.")
        return value

    print()
    print(instructions)
    value = input(f"  Enter {label}: ").strip()
    if not value:
        print(f"  ERROR: {label} cannot be empty. Aborting deploy.")
        sys.exit(1)
    return value


def _save_credential_to_env(env_var: str, value: str) -> None:
    """
    Persist a credential to the project-root .env file for future runs.

    Uses ``dotenv.set_key`` which creates the file if absent and updates the
    key in-place when it already exists.  Prints a confirmation on success.
    On failure, prints a non-fatal warning so the deploy can still proceed.

    Args:
        env_var: The environment variable name to write.
        value: The credential value to store.  Must not be empty.

    Side effects:
        Modifies ``_ENV_FILE_PATH`` on disk.
    """
    try:
        set_key(str(_ENV_FILE_PATH), env_var, value)
        print(f"  Saved {env_var} to .env for future runs.")
    except Exception as exc:  # noqa: BLE001 — catch-all intentional; save is non-fatal
        print(f"  Warning: could not save {env_var} to .env: {exc}")


def build_react_app() -> bool:
    """
    Run ``npm run build`` inside the React app directory.

    Executes the Vite production build which produces ``react-app/dist/``.
    Output (stdout and stderr) is inherited from the parent process so the
    operator can observe build progress.

    Returns:
        True if the build exited with code 0; False otherwise.

    Side effects:
        Writes build output to stdout/stderr.
        Creates or replaces ``react-app/dist/`` on success.
    """
    print()
    print(f"  Building React app in {REACT_APP_DIR} ...")
    try:
        result = subprocess.run(
            ["npm", "run", "build"],
            cwd=REACT_APP_DIR,
            check=True,
        )
        return result.returncode == 0
    except FileNotFoundError:
        print("  ERROR: 'npm' command not found. Ensure Node.js is installed.")
        return False
    except subprocess.CalledProcessError as exc:
        print(f"  ERROR: npm run build failed with exit code {exc.returncode}.")
        return False


def deploy_to_netlify(netlify_cmd: list[str], auth_token: str, site_id: str) -> bool:
    """
    Run the Netlify CLI production deploy command.

    Injects ``NETLIFY_AUTH_TOKEN`` and ``NETLIFY_SITE_ID`` into the subprocess
    environment. Credentials are never passed as command-line arguments
    (which would be visible in process listings).

    Args:
        netlify_cmd: Base invocation list (e.g. ``['netlify']``).
        auth_token: Netlify personal access token.
        site_id: Netlify site UUID.

    Returns:
        True if the deploy exited with code 0; False otherwise.

    Side effects:
        Writes deploy progress and deploy URL to stdout.
    """
    print()
    print("  Deploying to Netlify (production) ...")

    # Merge credentials into a copy of the current environment so all
    # inherited env vars (PATH, HOME, etc.) remain available to the CLI.
    deploy_env = os.environ.copy()
    deploy_env[ENV_AUTH_TOKEN] = auth_token
    deploy_env[ENV_SITE_ID] = site_id

    cmd = netlify_cmd + [
        "deploy",
        "--prod",
        "--dir", str(REACT_DIST_DIR),
    ]

    try:
        result = subprocess.run(cmd, env=deploy_env, check=True)
        return result.returncode == 0
    except FileNotFoundError:
        print(f"  ERROR: Netlify CLI command '{netlify_cmd[0]}' not found during deploy.")
        return False
    except subprocess.CalledProcessError as exc:
        print(f"  ERROR: netlify deploy failed with exit code {exc.returncode}.")
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """
    Orchestrate the Netlify deploy workflow.

    Flow:
    1. Detect Netlify CLI availability.
    2. If not available, print manual instructions and exit 0.
    3. Collect NETLIFY_AUTH_TOKEN via precedence chain (env → .env → prompt).
    4. Collect NETLIFY_SITE_ID via precedence chain (env → .env → prompt).
    5. Auto-save any interactively entered credential to .env for future runs.
    6. Build the React app via npm.
    7. Deploy via Netlify CLI.

    Side effects:
        Reads stdin when credentials are not available in env or .env.
        Writes to .env if credentials were entered interactively.
        Writes progress and deploy URL to stdout.
        Exits non-zero on build or deploy failure.
    """
    print()
    print("=" * 52)
    print("  Deploy React App to Netlify")
    print("=" * 52)

    netlify_cmd = find_netlify_cmd()
    if netlify_cmd is None:
        print_manual_instructions()
        sys.exit(0)

    auth_token_instructions = (
        "  NETLIFY_AUTH_TOKEN not found in environment or .env file.\n"
        "\n"
        "  How to obtain your Netlify personal access token:\n"
        "    1. Open https://app.netlify.com and log in.\n"
        "    2. Click your avatar (top-right) → User settings.\n"
        "    3. In the left sidebar, click 'Applications'.\n"
        "    4. Under 'Personal access tokens', click 'New access token'.\n"
        "    5. Give it a description (e.g. 'kolko-ni-struva deploy').\n"
        "    6. Copy the generated token — it is shown only once.\n"
        "\n"
        "  The token will be saved to .env so you are not prompted again.\n"
        "  Alternatively, copy .env.example to .env and fill in the values."
    )

    site_id_instructions = (
        "  NETLIFY_SITE_ID not found in environment or .env file.\n"
        "\n"
        "  How to obtain your Netlify site ID:\n"
        "    1. Open https://app.netlify.com and log in.\n"
        "    2. Click the name of your site.\n"
        "    3. Go to: Site configuration → General → Site details.\n"
        "    4. Copy the value labelled 'Site ID' (a UUID like\n"
        "       xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx).\n"
        "\n"
        "  If you have not created a site yet:\n"
        "    1. On the Netlify dashboard click 'Add new site'.\n"
        "    2. Choose 'Deploy manually'.\n"
        "    3. Drag any folder to create the site; its ID will then appear\n"
        "       in Site configuration → General → Site details.\n"
        "\n"
        "  The site ID will be saved to .env so you are not prompted again."
    )

    # Capture which credentials are already resolved before prompting.
    # A credential that is absent now was not in env vars or .env file and
    # will be entered interactively, so it must be saved afterwards.
    auth_token_needs_save: bool = not bool(os.environ.get(ENV_AUTH_TOKEN, "").strip())
    site_id_needs_save: bool = not bool(os.environ.get(ENV_SITE_ID, "").strip())

    auth_token = get_credential(ENV_AUTH_TOKEN, "Auth token", auth_token_instructions)
    site_id = get_credential(ENV_SITE_ID, "Site ID", site_id_instructions)

    # Auto-save credentials that were entered interactively.
    if auth_token_needs_save:
        _save_credential_to_env(ENV_AUTH_TOKEN, auth_token)
    if site_id_needs_save:
        _save_credential_to_env(ENV_SITE_ID, site_id)

    if not build_react_app():
        sys.exit(1)

    if not deploy_to_netlify(netlify_cmd, auth_token, site_id):
        sys.exit(1)

    print()
    print("  Deploy completed successfully.")
    print()


if __name__ == "__main__":
    main()
