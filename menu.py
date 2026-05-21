"""
menu.py: Interactive terminal menu for the kolko-ni-struva ETL pipeline.
Part of the kolko-ni-struva ETL pipeline (request R-20260419-0854).
Responsibilities: display pipeline statistics (ZIP count, date range, schema
state, config state), provide a numbered action menu (full refresh, download,
transform, Supabase sync, Netlify deploy, local React preview, exit), and
execute each action via subprocess.
"""
import configparser
import os
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

from dotenv import load_dotenv


# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.ini"
RAW_DIR = BASE_DIR / "data" / "raw"
FACTS_DIR = BASE_DIR / "data" / "schema" / "facts"
REACT_DIR = BASE_DIR / "react-app"  # Root of the Vite/React application
PREVIEW_URL = "http://localhost:4173"  # Default port used by `vite preview`
PREVIEW_PORT = 4173  # TCP port matching PREVIEW_URL; used for server-readiness polling


# ---------------------------------------------------------------------------
# Statistics helpers
# ---------------------------------------------------------------------------

def count_zips(raw_dir: Path) -> int:
    """
    Count ZIP files in raw_dir.

    Args:
        raw_dir: Directory containing downloaded ZIP archives.

    Returns:
        Integer count of .zip files present.
    """
    if not raw_dir.exists():
        return 0
    return sum(1 for p in raw_dir.iterdir() if p.suffix == ".zip")


def zip_date_range(raw_dir: Path) -> tuple:
    """
    Return the (min_date, max_date) of ZIP files in raw_dir.

    Args:
        raw_dir: Directory containing downloaded ZIP archives.

    Returns:
        Tuple of (min_date_str, max_date_str) or ("—", "—") when empty.
    """
    if not raw_dir.exists():
        return ("—", "—")
    dates = sorted(p.stem for p in raw_dir.iterdir() if p.suffix == ".zip")
    if not dates:
        return ("—", "—")
    return (dates[0], dates[-1])


def count_fact_files(facts_dir: Path) -> int:
    """
    Count processed fact CSV files in facts_dir.

    Args:
        facts_dir: Directory containing date-partitioned fact CSVs.

    Returns:
        Integer count of .csv files present.
    """
    if not facts_dir.exists():
        return 0
    return sum(1 for p in facts_dir.iterdir() if p.suffix == ".csv")


def schema_freshness(facts_dir: Path) -> str:
    """
    Return the newest fact CSV date string, or 'not built' when absent.

    Args:
        facts_dir: Directory containing date-partitioned fact CSVs.

    Returns:
        ISO date string of the newest fact file, or 'not built'.
    """
    if not facts_dir.exists():
        return "not built"
    dates = sorted(p.stem for p in facts_dir.iterdir() if p.suffix == ".csv")
    return dates[-1] if dates else "not built"


def read_state(config_path: Path) -> tuple:
    """
    Read last_downloaded_date and last_processed_date from config.ini.

    Args:
        config_path: Path to config.ini.

    Returns:
        Tuple of (last_downloaded_date_str, last_processed_date_str); empty
        strings when the file or keys are absent.
    """
    if not config_path.exists():
        return ("", "")
    cfg = configparser.ConfigParser()
    cfg.read(config_path, encoding="utf-8")
    dl = cfg.get("state", "last_downloaded_date", fallback="")
    pr = cfg.get("state", "last_processed_date", fallback="")
    return (dl, pr)


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def print_stats() -> None:
    """
    Print current pipeline statistics to stdout.

    Side effects:
        Reads filesystem (data/raw/, data/schema/facts/) and config.ini.
        Writes formatted output to stdout.
    """
    zip_count = count_zips(RAW_DIR)
    min_date, max_date = zip_date_range(RAW_DIR)
    fact_count = count_fact_files(FACTS_DIR)
    freshness = schema_freshness(FACTS_DIR)
    last_dl, last_pr = read_state(CONFIG_PATH)

    print()
    print("=" * 52)
    print("  Kolko Ni Struva — Pipeline Statistics")
    print("=" * 52)
    print(f"  Raw ZIPs available : {zip_count}")
    print(f"  Date range         : {min_date}  →  {max_date}")
    print(f"  Fact files built   : {fact_count}")
    print(f"  Schema freshness   : {freshness}")
    print(f"  Last downloaded    : {last_dl or '(none)'}")
    print(f"  Last processed     : {last_pr or '(none)'}")
    print("=" * 52)
    print()


def print_menu() -> None:
    """Print the numbered action menu to stdout."""
    print("  Actions:")
    print("    1) Full refresh      (download + transform + update supabase)")
    print("    2) Download only     (python src/extract.py)")
    print("    3) Transform only    (python src/transform.py)")
    print("    4) Update Supabase DB  (python src/load_supabase.py)")
    print("    5) Deploy React app to Netlify")
    print("    6) Preview React app locally")
    print("    0) Exit")
    print()


# ---------------------------------------------------------------------------
# Action runners
# ---------------------------------------------------------------------------

def run_script(script_path: str) -> bool:
    """
    Execute a Python script via subprocess and print its output.

    Args:
        script_path: Relative path to the Python script to run (e.g.
                     'src/extract.py').

    Returns:
        True if the script exited with code 0; False otherwise.

    Side effects:
        Prints stdout on success.  Prints stdout + stderr (prefixed 'STDERR:')
        on failure.  List-form subprocess prevents shell injection.
    """
    print(f"Running: python {script_path}")
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            check=True,
            capture_output=True,
            text=True,
        )
        if result.stdout:
            print(result.stdout, end="")
        return True
    except subprocess.CalledProcessError as exc:
        print(f"ERROR: Script exited with code {exc.returncode}")
        if exc.stdout:
            print(exc.stdout, end="")
        if exc.stderr:
            print(f"STDERR: {exc.stderr}", end="")
        return False


def action_download() -> None:
    """Run only the download step (src/extract.py)."""
    run_script("src/extract.py")


def action_transform() -> None:
    """Run only the transform step (src/transform.py)."""
    run_script("src/transform.py")


def action_full_refresh() -> None:
    """Run the complete ETL pipeline: download, transform, then sync to Supabase.

    Stops on first failure — if extract or transform exits with a non-zero
    code, the next step is not executed.
    """
    if not run_script("src/extract.py"):
        return
    if not run_script("src/transform.py"):
        return
    run_script("src/load_supabase.py")


def action_update_supabase() -> None:
    """Sync the latest star-schema data to the Supabase cloud database."""
    run_script("src/load_supabase.py")


def action_deploy_netlify() -> None:
    """
    Run the interactive Netlify deploy script (src/deploy_netlify.py).

    Invokes the deploy script without capturing I/O so that stdin is
    inherited by the child process, enabling the interactive credential
    prompts defined in deploy_netlify.py to reach the operator's terminal.

    Side effects:
        Launches src/deploy_netlify.py as a subprocess.
        Output and input pass through to/from the operator's terminal.
    """
    # Do not use capture_output here — deploy_netlify.py needs stdin
    # passthrough for the interactive credential collection prompts.
    subprocess.run([sys.executable, "src/deploy_netlify.py"])


def _wait_for_server(host: str, port: int, timeout: float = 30.0, interval: float = 0.25) -> bool:
    """
    Poll a TCP port until a server accepts connections or the timeout expires.

    Args:
        host: Hostname or IP address to connect to.
        port: TCP port number to poll.
        timeout: Maximum seconds to wait before returning False.
        interval: Seconds to sleep between consecutive connection attempts.

    Returns:
        True when the port accepts a connection within the timeout window;
        False if the timeout expires before the server becomes reachable.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return True
        except OSError:
            # Server not ready yet; wait before retrying.
            time.sleep(interval)
    return False


def action_local_preview() -> None:
    """
    Build the React app and start the Vite local preview server.

    Validates that VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY are present in
    the root .env file before attempting a build, so the operator receives a
    clear error message instead of a silent empty bundle.  Runs 'npm run build'
    then starts 'npm run preview' from the react-app/ directory as a
    non-blocking subprocess.  Polls the preview port until the server is ready,
    then opens the browser — avoiding the race condition where the browser
    opens before the server has bound to its port.  The local URL is always
    printed to the terminal.

    Args:
        None.

    Returns:
        None.

    Side effects:
        Reads the root .env file via python-dotenv (does not override existing
        shell env vars).  Executes npm commands in react-app/ via subprocess.
        Prints the local preview URL to stdout.  Blocks until the preview
        server is stopped (Ctrl+C).
    """
    # Load the root .env without overriding values already set in the shell
    # environment so that CI/CD overrides are respected.
    env_path = BASE_DIR / ".env"
    load_dotenv(dotenv_path=env_path, override=False)

    # Validate VITE_ credentials before running the build.  A missing or
    # empty credential causes Vite to embed undefined into the bundle, which
    # makes the React app show only the credentials-error screen.
    vite_url = os.environ.get("VITE_SUPABASE_URL", "").strip()
    vite_key = os.environ.get("VITE_SUPABASE_ANON_KEY", "").strip()
    missing = []
    if not vite_url:
        missing.append("VITE_SUPABASE_URL")
    if not vite_key:
        missing.append("VITE_SUPABASE_ANON_KEY")
    if missing:
        print(
            f"ERROR: Missing Supabase credentials for the React build: "
            f"{', '.join(missing)}.\n"
            f"  Add these keys to the root .env file (or export them as "
            f"environment variables) and try again.\n"
            f"  Example:\n"
            f"    VITE_SUPABASE_URL=https://<project>.supabase.co\n"
            f"    VITE_SUPABASE_ANON_KEY=<your-anon-key>"
        )
        return

    print("Building React app for local preview...")
    try:
        subprocess.run(
            ["npm", "run", "build"],
            cwd=REACT_DIR,
            check=True,
        )
    except FileNotFoundError:
        print("ERROR: 'npm' not found. Install Node.js and npm to use local preview.")
        return
    except subprocess.CalledProcessError as exc:
        print(f"ERROR: npm run build failed with code {exc.returncode}")
        return

    print(f"\nStarting preview server — local URL: {PREVIEW_URL}")
    print("  Press Ctrl+C to stop.\n")

    # Start the preview server non-blocking so the browser is opened only after
    # the server is confirmed ready on its TCP port.  Opening the browser before
    # the server binds causes a "connection refused" error in the browser.
    proc = subprocess.Popen(["npm", "run", "preview"], cwd=REACT_DIR)
    try:
        # Poll until the server accepts connections, then open the browser.
        if _wait_for_server("localhost", PREVIEW_PORT):
            try:
                webbrowser.open(PREVIEW_URL)
            except Exception:  # noqa: BLE001 — any open failure is silently skipped
                pass
        else:
            print(
                f"  WARNING: Preview server did not become ready on port "
                f"{PREVIEW_PORT} within 30 s. Open {PREVIEW_URL} manually."
            )
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        print("\nPreview server stopped.")


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main() -> None:
    """
    Display pipeline statistics and a numbered menu; loop until the user
    selects Exit.

    Side effects:
        Reads stdin for menu selection.  Writes to stdout.  Invokes ETL
        scripts via subprocess on menu selection.
    """
    while True:
        print_stats()
        print_menu()

        try:
            choice = input("  Enter choice [0-6]: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        print()

        if choice == "0":
            print("Exiting.")
            break
        elif choice == "1":
            action_full_refresh()
        elif choice == "2":
            action_download()
        elif choice == "3":
            action_transform()
        elif choice == "4":
            action_update_supabase()
        elif choice == "5":
            action_deploy_netlify()
        elif choice == "6":
            action_local_preview()
        else:
            print("  Invalid choice. Please enter 0, 1, 2, 3, 4, 5, or 6.")

        print()


if __name__ == "__main__":
    main()
