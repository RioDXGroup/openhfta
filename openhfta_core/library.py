import ctypes
import ctypes.util
import os
from pathlib import Path
from typing import Optional
from .exceptions import LibraryError

class FortranInt16(ctypes.c_int16):
    pass
class FortranInt32(ctypes.c_int32):
    pass
class FortranReal(ctypes.c_float):
    pass

def find_ytw_core_library() -> Optional[str]:
    env_path = os.environ.get("OPENHFTA_LIB")
    if env_path:
        path = Path(env_path).expanduser()
        return str(path if path.is_absolute() else Path.cwd() / path)
    script_dir = Path(__file__).resolve().parent.parent
    names = ("libopenytwcore.so", "OpenYTWCore.dll", "libOpenYTWCore.dylib")
    for directory in (script_dir, script_dir.parent / "lib"):
        for name in names:
            candidate = directory / name
            if candidate.exists():
                return str(candidate)
    return ctypes.util.find_library("openytwcore")

def load_ytw_core(lib_path: Optional[str] = None) -> ctypes.CDLL:
    path = lib_path or find_ytw_core_library()
    if path is None:
        raise LibraryError("Cannot find OpenYTWCore library. Use --lib or OPENHFTA_LIB to specify path.")
    try:
        lib = ctypes.CDLL(path)
    except OSError as exc:
        raise LibraryError(f"Failed to load {path}: {exc}") from exc
    try:
        func = lib.ytwcore1_
    except AttributeError as exc:
        raise LibraryError("Symbol ytwcore1_ not found in library. Check library version.") from exc
    func.argtypes = [ctypes.POINTER(FortranReal), ctypes.POINTER(FortranReal),
        ctypes.POINTER(FortranReal), ctypes.POINTER(FortranReal), ctypes.POINTER(FortranReal),
        ctypes.POINTER(FortranReal), ctypes.POINTER(FortranInt16), ctypes.POINTER(FortranInt16), ctypes.POINTER(FortranInt16),
        ctypes.POINTER(FortranInt16), ctypes.POINTER(FortranReal), ctypes.POINTER(FortranReal),
        ctypes.POINTER(FortranInt16)]
    func.restype = None
    trace_func = getattr(lib, "ytwcore1_gettrace_", None)
    if trace_func is not None:
        trace_func.argtypes = [ctypes.POINTER(FortranInt32), ctypes.POINTER(FortranInt16),
            ctypes.POINTER(FortranInt16), ctypes.POINTER(FortranReal),
            ctypes.POINTER(FortranReal), ctypes.POINTER(FortranReal)]
        trace_func.restype = None
    return lib
