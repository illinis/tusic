"""Local settings and atomic JSON score files. No network calls or database needed."""

from dataclasses import dataclass
import json
import os
from pathlib import Path
import sys
import tempfile

from .practice import Session


def _environment_path(name: str, fallback: Path) -> Path:
    value = os.environ.get(name)
    path = Path(value).expanduser() if value else fallback
    return path if path.is_absolute() else fallback


def default_config_directory() -> Path:
    if sys.platform == "win32":
        return _environment_path("APPDATA", Path.home() / "AppData" / "Roaming") / "Tusic"
    return _environment_path("XDG_CONFIG_HOME", Path.home() / ".config") / "tusic"


def default_scores_directory() -> Path:
    if sys.platform == "win32":
        return _environment_path("LOCALAPPDATA", Path.home() / "AppData" / "Local") / "Tusic" / "scores"
    return _environment_path("XDG_DATA_HOME", Path.home() / ".local" / "share") / "tusic" / "scores"


def atomic_write_json(path: Path, data: dict) -> None:
    """Replace one file only after its complete new contents are on disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=f".{path.stem}-", suffix=".tmp", delete=False) as handle:
            temporary_path = Path(handle.name)
            json.dump(data, handle, indent=2, ensure_ascii=False, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def ensure_writable_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryFile(dir=path):
        pass


@dataclass(frozen=True)
class Settings:
    scores_directory: Path
    spelling: str = "sharps"


class SettingsStore:
    def __init__(self, directory: Path | None = None):
        self.directory = directory if directory is not None else default_config_directory()
        self.path = self.directory / "settings.json"

    def load(self) -> tuple[Settings, str | None]:
        default = Settings(default_scores_directory())
        if not self.path.exists():
            return default, None
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or data.get("schema_version") != 1:
                raise ValueError("Unsupported settings format.")
            location = data.get("scores_directory")
            if not isinstance(location, str) or not location.strip():
                raise ValueError("The score folder is missing.")
            path = Path(location).expanduser()
            if not path.is_absolute():
                raise ValueError("The score folder must be an absolute path.")
            spelling = data.get("spelling", "sharps")
            if spelling not in ("sharps", "flats"):
                raise ValueError("Unknown note spelling preference.")
            return Settings(path, spelling), None
        except (OSError, ValueError) as error:
            return default, f"Could not read {self.path}:\n{error}\n\nDefault settings are being used."

    def save(self, settings: Settings) -> None:
        ensure_writable_directory(settings.scores_directory)
        atomic_write_json(self.path, {"schema_version": 1,
                                     "scores_directory": str(settings.scores_directory),
                                     "spelling": settings.spelling})


class ScoreStore:
    def __init__(self, directory: Path):
        self.directory = directory

    def save(self, session: Session) -> Path:
        # UUID filenames prevent collisions between simultaneous matches/app instances.
        path = self.directory / f"{session.id}.json"
        atomic_write_json(path, session.to_dict())
        return path
