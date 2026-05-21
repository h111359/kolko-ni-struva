"""
config_utils.py: Shared configuration bootstrap and atomic state-write helpers.
Part of the kolko-ni-struva ETL pipeline (request R-20260419-0854).
Responsibilities: load/bootstrap config.ini, atomically save state keys without
overwriting sibling keys written by another script in the same pipeline run.
"""
import configparser
from pathlib import Path


# Default values written when config.ini is absent or has no sections.
_DEFAULT_SETTINGS: dict = {
    "opendata_url": "https://kolkostruva.bg/opendata",
    "max_retries": "3",
    "retry_delay": "10",
    "log_level": "INFO",
}
_DEFAULT_STATE: dict = {
    "last_downloaded_date": "",
    "last_processed_date": "",
}


def load_config(config_path: Path) -> configparser.ConfigParser:
    """
    Read config.ini; bootstrap with defaults when absent or empty.

    Args:
        config_path: Absolute or project-relative path to config.ini.

    Returns:
        A populated ConfigParser instance with at minimum [settings] and
        [state] sections containing default values.

    Side effects:
        Writes a new config.ini to config_path when the file is absent or
        has no parseable sections.
    """
    cfg = configparser.ConfigParser()

    if config_path.exists():
        cfg.read(config_path, encoding="utf-8")

    changed = False

    if not cfg.has_section("settings"):
        cfg.add_section("settings")
        for key, val in _DEFAULT_SETTINGS.items():
            cfg.set("settings", key, val)
        changed = True

    if not cfg.has_section("state"):
        cfg.add_section("state")
        for key, val in _DEFAULT_STATE.items():
            cfg.set("state", key, val)
        changed = True

    if changed:
        _write_atomic(cfg, config_path)

    return cfg


def save_state(config_path: Path, **kwargs: str) -> None:
    """
    Persist one or more [state] key/value pairs to config.ini atomically.

    Always re-reads config_path from disk immediately before writing so that
    state keys written by a previously-run script in the same pipeline
    sequence are preserved.

    Args:
        config_path: Path to config.ini.  Must already exist (call
            load_config first to guarantee creation).
        **kwargs: Key/value pairs to set under [state].  Values must be
            strings.

    Side effects:
        Writes config_path atomically via a .partial temporary file and
        Path.replace().
    """
    # Re-read from disk to avoid overwriting keys written by another script.
    cfg = configparser.ConfigParser()
    cfg.read(config_path, encoding="utf-8")

    if not cfg.has_section("state"):
        cfg.add_section("state")

    for key, value in kwargs.items():
        cfg.set("state", key, value)

    _write_atomic(cfg, config_path)


def _write_atomic(cfg: configparser.ConfigParser, dest: Path) -> None:
    """
    Write a ConfigParser to dest via a .partial file and Path.replace().

    Args:
        cfg:  Populated ConfigParser instance to serialise.
        dest: Final destination path for the config file.

    Side effects:
        Creates dest.partial then renames it to dest atomically, ensuring no
        partial writes are visible to concurrent readers.
    """
    partial = dest.with_suffix(dest.suffix + ".partial")
    with open(partial, "w", encoding="utf-8") as fh:
        cfg.write(fh)
    # Path.replace() is used for cross-platform atomic overwrite.
    partial.replace(dest)
