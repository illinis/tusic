"""Bundle the host's standard PortAudio library, without unused platform DLLs."""

from pathlib import Path

from PyInstaller.depend.utils import _resolveCtypesImports
from PyInstaller.utils.hooks import get_module_attribute


library_name = get_module_attribute("sounddevice", "_libname")
library = Path(library_name)
if library.is_absolute() and library.is_file():
    # Windows uses the standard MME/DirectSound/WASAPI build, without ASIO.
    if library.suffix.lower() == ".dll":
        library = library.with_name(library.name.replace("-asio", ""))
    destination = "_sounddevice_data/portaudio-binaries" if library.parent.name == "portaudio-binaries" else "."
    binaries = [(str(library), destination)]
else:
    # Resolve a system-provided shared library on Linux.
    resolved = _resolveCtypesImports([library_name])
    if not resolved:
        raise RuntimeError("PortAudio was not found. Install it before building Tusic.")
    binaries = [(filename, ".") for _, filename, _ in resolved]
