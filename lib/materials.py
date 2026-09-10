import re
from pathlib import Path


EXT_STRIP = re.compile(r"[^.\w\-\u00C0-\uFFFF ]+")


def sanitize_material_name(name):
    name = EXT_STRIP.sub("", name).strip(" .")
    return name or "arquivo"


def unique_path(dirpath, name, size=None):
    dirpath = Path(dirpath)
    dirpath.mkdir(parents=True, exist_ok=True)
    dest = dirpath / name
    base, ext = dest.stem, dest.suffix
    n = 1
    while dest.exists():
        if size is not None:
            try:
                if dest.stat().st_size == size:
                    return dest, True
            except OSError:
                pass
        n += 1
        dest = dirpath / f"{base} ({n}){ext}"
    return dest, False


def write_url_shortcut(path, url):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"[InternetShortcut]\nURL={url}\n", encoding="utf-8")


def download_file(session, url, dest, size=None, extra_headers=None, chunk=1 << 16):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    if extra_headers:
        headers.update(extra_headers)
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    got = 0
    with session.get(url, headers=headers, timeout=60, stream=True) as resp:
        resp.raise_for_status()
        with open(tmp, "wb") as fh:
            for blk in resp.iter_content(chunk_size=chunk):
                if blk:
                    fh.write(blk)
                    got += len(blk)
    tmp.replace(dest)
    return got