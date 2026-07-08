"""Load the vendored cubiomes shared library."""

from __future__ import annotations

import ctypes
import glob
import os
import sys


def load_native_lib() -> ctypes.CDLL:
    package_dir = os.path.dirname(os.path.abspath(__file__))
    lib_dir = os.path.join(package_dir, "lib")
    candidates: list[str] = []

    if sys.platform == "win32":
        candidates.append(os.path.join(lib_dir, "lib.dll"))
    elif sys.platform == "darwin":
        candidates.extend(
            [
                os.path.join(lib_dir, "lib.dylib"),
                os.path.join(lib_dir, "lib.so"),
            ]
        )
    else:
        candidates.append(os.path.join(lib_dir, "lib.so"))

    candidates.extend(glob.glob(os.path.join(package_dir, "lib_c.*")))

    for path in candidates:
        if os.path.isfile(path):
            return ctypes.CDLL(path)

    raise FileNotFoundError(
        "Compiled cubiomes library not found. Reinstall ezseedfinder so pip can build the native library."
    )
