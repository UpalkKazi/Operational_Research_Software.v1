"""MIPLIB 2017 download, file cache, and solution cache with progress and cancellation."""

from __future__ import annotations

import os
import re
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from src.ingestion.mps_reader import MAX_COMPRESSED_BYTES, read_mps_bytes
from src.modeling.model_spec import ModelSpec

BASE_URL = "https://miplib.zib.de"
INSTANCE_URL = f"{BASE_URL}/WebData/instances/{{name}}.mps.gz"
EASY_LIST_URL = f"{BASE_URL}/downloads/easy-v18.test"
DATA_DIR = Path(os.environ.get("ORSTUDIO_DATA_DIR", "data"))
MIPLIB_DIR = DATA_DIR / "miplib"
EASY_CACHE = DATA_DIR / "miplib_easy.txt"
EASY_MAX_AGE = 7 * 24 * 3600
_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]{0,80}$")

# Verified to exist in the MIPLIB 2017 collection (HEAD 200, gzip payload).
RECOMMENDED: List[Dict[str, str]] = [
    {"name": "flugpl", "desc": "Flight planning · tiny general-integer model"},
    {"name": "gen-ip054", "desc": "General integer programming"},
    {"name": "pk1", "desc": "Packing problem · 86 vars"},
    {"name": "gt2", "desc": "Truck routing · general integers"},
    {"name": "markshare_4_0", "desc": "Market share · small but hard"},
    {"name": "stein9inf", "desc": "Steiner triple · infeasible test case"},
    {"name": "neos5", "desc": "NEOS benchmark · binary + continuous"},
    {"name": "eil33-2", "desc": "Vehicle routing · 4,516 binaries"},
    {"name": "air04", "desc": "Airline crew scheduling · 8,904 binaries"},
    {"name": "cap6000", "desc": "Capacity planning · 6,000 binaries"},
    {"name": "neos-1067731", "desc": "Production planning"},
    {"name": "pb-grow22", "desc": "Blending problem"},
]


class MiplibError(RuntimeError):
    pass


class DownloadCancelled(MiplibError):
    pass


def validate_name(name: str) -> str:
    name = (name or "").strip()
    if name.lower().endswith(".mps.gz"):
        name = name[:-7]
    if not _NAME_RE.match(name):
        raise MiplibError("Instance names may contain only letters, digits, '-', '_' and '.'.")
    return name


def local_path(name: str) -> Path:
    return MIPLIB_DIR / f"{validate_name(name)}.mps.gz"


def is_downloaded(name: str) -> bool:
    try:
        path = local_path(name)
    except MiplibError:
        return False
    return path.exists() and path.stat().st_size > 0


def downloaded_files() -> List[Dict[str, object]]:
    if not MIPLIB_DIR.exists():
        return []
    files = []
    for path in sorted(MIPLIB_DIR.glob("*.mps.gz")):
        files.append({
            "name": path.name[:-7],
            "size_kb": round(path.stat().st_size / 1024, 1),
            "modified": time.strftime("%Y-%m-%d %H:%M", time.localtime(path.stat().st_mtime)),
        })
    return files


def download(
    name: str,
    progress: Optional[Callable[[int, Optional[int]], None]] = None,
    cancel: Optional[threading.Event] = None,
    timeout: float = 60.0,
) -> Tuple[Path, bool]:
    """Download an instance. Returns ``(path, from_cache)``."""
    name = validate_name(name)
    path = local_path(name)
    if path.exists() and path.stat().st_size > 0:
        with open(path, "rb") as handle:
            if handle.read(2) == b"\x1f\x8b":
                return path, True
        path.unlink()

    import requests

    url = INSTANCE_URL.format(name=name)
    try:
        response = requests.get(url, stream=True, timeout=timeout, allow_redirects=True)
    except requests.RequestException as exc:
        raise MiplibError(f"Network error while contacting miplib.zib.de: {exc}") from exc
    if response.status_code == 404 or "text/html" in response.headers.get("content-type", ""):
        response.close()
        raise MiplibError(f"'{name}' is not in the MIPLIB 2017 collection (check the spelling).")
    if response.status_code != 200:
        response.close()
        raise MiplibError(f"miplib.zib.de answered HTTP {response.status_code} for '{name}'.")
    total = response.headers.get("content-length")
    total_bytes = int(total) if total and total.isdigit() else None
    if total_bytes and total_bytes > MAX_COMPRESSED_BYTES:
        response.close()
        raise MiplibError(f"'{name}' is {total_bytes // (1024 * 1024)} MB; the limit is {MAX_COMPRESSED_BYTES // (1024 * 1024)} MB.")

    MIPLIB_DIR.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(".part")
    received = 0
    first = b""
    try:
        with open(partial, "wb") as handle:
            for chunk in response.iter_content(chunk_size=1 << 15):
                if cancel is not None and cancel.is_set():
                    raise DownloadCancelled("Download cancelled.")
                if not chunk:
                    continue
                if not first:
                    first = chunk[:2]
                    if first != b"\x1f\x8b":
                        raise MiplibError(f"The server did not return a gzip MPS file for '{name}'.")
                handle.write(chunk)
                received += len(chunk)
                if received > MAX_COMPRESSED_BYTES:
                    raise MiplibError("Download exceeded the size limit.")
                if progress:
                    progress(received, total_bytes)
        os.replace(partial, path)
    except BaseException:
        response.close()
        if partial.exists():
            partial.unlink()
        raise
    response.close()
    return path, False


def load_spec(name: str) -> ModelSpec:
    path = local_path(name)
    data = path.read_bytes()
    spec = read_mps_bytes(data, filename=path.name, name_hint=validate_name(name))
    spec.metadata = dict(spec.metadata, miplib_instance=validate_name(name), mps_path=str(path))
    return spec.validate()


def easy_instances(force: bool = False) -> Tuple[List[str], bool]:
    """Return ``(names, from_cache)``."""
    if not force and EASY_CACHE.exists() and time.time() - EASY_CACHE.stat().st_mtime < EASY_MAX_AGE:
        names = [l.strip() for l in EASY_CACHE.read_text(encoding="utf-8").splitlines() if l.strip()]
        if names:
            return names, True
    import requests

    try:
        response = requests.get(EASY_LIST_URL, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        if EASY_CACHE.exists():
            names = [l.strip() for l in EASY_CACHE.read_text(encoding="utf-8").splitlines() if l.strip()]
            return names, True
        raise MiplibError(f"Could not fetch the MIPLIB easy list: {exc}") from exc
    names = [l.strip() for l in response.text.splitlines() if l.strip() and not l.startswith("#")]
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    EASY_CACHE.write_text("\n".join(names), encoding="utf-8")
    return names, False


# ---------------------------------------------------------------------------
#  Solution cache (stored in the existing data/miplib_cache.db table)
# ---------------------------------------------------------------------------

def _cache():
    from src.storage.miplib_cache import MIPLIBCache

    return MIPLIBCache(str(DATA_DIR / "miplib_cache.db"))


def cache_key(name: str, solver_key: str) -> str:
    return f"{validate_name(name)}::{solver_key}"


def cached_solution(name: str, solver_key: str) -> Optional[dict]:
    entry = _cache().get(cache_key(name, solver_key))
    if entry is None:
        return None
    entry["status"] = entry.get("status", "").replace(" (from cache)", "")
    return entry


def store_solution(name: str, solver_key: str, result: dict) -> None:
    payload = {k: v for k, v in result.items() if k not in ("log", "library_check")}
    payload.setdefault("objective_value", result.get("objective"))
    payload.setdefault("solver_name", result.get("backend"))
    _cache().set(cache_key(name, solver_key), payload)


def list_cached_solutions() -> List[dict]:
    rows = []
    for row in _cache().list_cached():
        instance, _, solver = row["instance_name"].partition("::")
        rows.append({**row, "instance": instance, "solver_key": solver or "(legacy)"})
    return rows


def clear_solution_cache() -> None:
    _cache().clear()


def clear_file_cache() -> int:
    count = 0
    for path in MIPLIB_DIR.glob("*.mps.gz"):
        path.unlink()
        count += 1
    return count
