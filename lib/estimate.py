import re
import threading
from urllib.parse import urljoin


_EXTINF_RE = re.compile(r"#EXTINF:\s*([0-9]+(?:\.[0-9]+)?)")
_STREAM_INF_RE = re.compile(r"#EXT-X-STREAM-INF:[^\n]*BANDWIDTH=(\d+)")
_DIRECT_MEDIA = ("video/", "audio/", "application/octet-stream", "application/mp4", "binary/octet-stream")

_CACHE = {}
_CACHE_LOCK = threading.Lock()


def format_bytes(n):
    if not n or n <= 0:
        return "n/d"
    n = float(n)
    units = ["B", "KB", "MB", "GB", "TB"]
    for unit in units:
        if n < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(n)} {unit}"
            return f"{n:.1f}".replace(".", ",") + f" {unit}"
        n /= 1024


def format_duration(seconds):
    if not seconds or seconds <= 0:
        return None
    seconds = int(round(float(seconds)))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def probe_stream(stream, session, timeout=30):
    """Estimates (size_bytes, duration_seconds) for a resolved stream.

    Fully generic, best-effort: returns (None, None) instead of raising.
    Works on any HTTP(S) URL the session can authenticate against.
    """
    if not stream:
        return (None, None)
    url = stream.get("url")
    if not url:
        return (None, None)
    if "youtube.com" in url or "youtu.be" in url:
        return (None, None)
    with _CACHE_LOCK:
        if url in _CACHE:
            return _CACHE[url]
    headers = dict(stream.get("http_headers") or {})
    headers.setdefault(
        "User-Agent",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/151.0.0.0 Safari/537.36",
    )
    try:
        if "m3u8" in url.lower():
            result = _probe_hls(url, headers, session, timeout)
        else:
            result = _probe_direct(url, headers, session, timeout)
    except Exception:
        result = (None, None)
    with _CACHE_LOCK:
        _CACHE[url] = result
    return result


def _probe_hls(url, headers, session, timeout):
    resp = session.get(url, headers=headers, timeout=timeout)
    if resp.status_code not in (200, 206):
        return (None, None)
    text = resp.text

    if "#EXT-X-STREAM-INF" not in text:
        duration = sum(float(m) for m in _EXTINF_RE.findall(text))
        return (None, duration) if duration else (None, None)

    variants = []
    bandwidth = None
    for line in text.splitlines():
        line = line.strip()
        m = _STREAM_INF_RE.search(line)
        if m:
            bandwidth = int(m.group(1))
        elif line and not line.startswith("#") and bandwidth is not None:
            variants.append((bandwidth, urljoin(url, line)))
            bandwidth = None
    if not variants:
        return (None, None)

    variants.sort(key=lambda v: v[0], reverse=True)
    best_bandwidth, best_url = variants[0]
    media = session.get(best_url, headers=headers, timeout=timeout)
    if media.status_code not in (200, 206):
        return (None, None)
    duration = sum(float(m) for m in _EXTINF_RE.findall(media.text))
    if not duration:
        return (None, None)
    size = int(duration * best_bandwidth / 8.0)
    return (size, duration)


def _probe_direct(url, headers, session, timeout):
    resp = session.get(url, headers={**headers, "Range": "bytes=0-0"}, stream=True, timeout=timeout)
    try:
        content_type = resp.headers.get("content-type", "").lower()
        if resp.status_code == 206:
            m = re.search(r"/(\d+)\s*$", resp.headers.get("content-range", ""))
            return (int(m.group(1)), None) if m else (None, None)
        if resp.status_code != 200:
            return (None, None)
        total = resp.headers.get("content-length")
        if not (total and total.isdigit()):
            return (None, None)
        if not any(p in content_type for p in _DIRECT_MEDIA):
            return (None, None)
        return (int(total), None)
    finally:
        try:
            resp.close()
        except Exception:
            pass