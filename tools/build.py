"""Build a standalone executable on the current operating system."""

from pathlib import Path
import subprocess
import sys


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    from tusic import __version__

    # A versioned output can be built while an older executable is in use.
    destination = root / "dist" / f"v{__version__}"
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
                    "--onefile", "--windowed", "--name", "Tusic", "--collect-data", "tusic",
                    "--additional-hooks-dir", str(root / "tools" / "hooks"),
                    "--distpath", str(destination),
                    "main.py"], cwd=root, check=True)
