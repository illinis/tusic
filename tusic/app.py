"""Command-line entry point; importing core modules never needs a GUI."""

import argparse
from pathlib import Path
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="Tusic — offline music practice")
    parser.add_argument("--config-dir", type=Path, help="Use a separate settings directory")
    parser.add_argument("--data-dir", type=Path, help="Override the score folder for this run")
    args = parser.parse_args()
    try:
        from .ui import TusicApp
    except ImportError as error:
        if error.name not in ("tkinter", "_tkinter"):
            raise
        message = ("Tusic needs Python's Tkinter GUI support.\n"
                   "Windows: install Python with the Tcl/Tk option enabled.\n"
                   "Debian/Ubuntu: sudo apt install python3-tk\n"
                   "Fedora: sudo dnf install python3-tkinter")
        print(message, file=sys.stderr)
        raise SystemExit(1) from error
    app = TusicApp(config_directory=args.config_dir, data_directory=args.data_dir)
    app.mainloop()
