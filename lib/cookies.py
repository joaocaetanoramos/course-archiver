import json
import os
import re
import tempfile
from pathlib import Path

import requests


class TolerantSession(requests.Session):
    def get_redirect_target(self, resp):
        if resp.is_redirect:
            location = resp.headers.get("location")
            if isinstance(location, bytes):
                location = location.decode("latin-1", errors="replace")
            return location
        return None


def load_cookies(source, host):
    if os.path.isfile(source):
        raw = Path(source).read_text(encoding="utf-8-sig")
    else:
        raw = source
    raw = raw.strip()
    if not raw:
        raise SystemExit("Cookie vazio.")

    if raw.startswith("[") or raw.startswith("{"):
        jar = requests.cookies.RequestsCookieJar()
        data = json.loads(raw)
        if isinstance(data, dict):
            data = data.get("cookies", data.get("Cookies", []))
        for c in data:
            jar.set(
                c.get("name"),
                c.get("value"),
                domain=(c.get("domain") or "").lstrip("."),
                path=c.get("path") or "/",
                secure=bool(c.get("secure")),
            )
        return jar

    if "# Netscape HTTP Cookie File" in raw or re.search(r"(?m)^\S+\t(?:TRUE|FALSE)\t", raw):
        jar = requests.cookies.RequestsCookieJar()
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("#HttpOnly_"):
                line = line[len("#HttpOnly_"):]
            elif line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 7:
                continue
            domain, _, path, secure, _, name = parts[:6]
            value = "\t".join(parts[6:])
            jar.set(name, value, domain=domain, path=path or "/", secure=secure.lower() == "true")
        return jar

    jar = requests.cookies.RequestsCookieJar()
    for pair in raw.split(";"):
        if "=" in pair:
            key, value = pair.split("=", 1)
            jar.set(key.strip(), value.strip(), domain=host, path="/")
    return jar


def to_netscape(jar, host):
    lines = ["# Netscape HTTP Cookie File"]
    for cookie in jar:
        domain = cookie.domain if cookie.domain else host
        include_sub = "TRUE" if domain.startswith(".") else "FALSE"
        secure = "TRUE" if cookie.secure else "FALSE"
        expires = str(int(cookie.expires)) if cookie.expires else "0"
        lines.append(
            "\t".join([domain, include_sub, cookie.path, secure, expires, cookie.name, cookie.value])
        )
    return "\n".join(lines) + "\n"


def write_netscape_cookie_file(jar, host):
    fd, path = tempfile.mkstemp(prefix="cookies_", suffix=".txt")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(to_netscape(jar, host))
            fh.flush()
            os.fsync(fh.fileno())
    except Exception:
        try:
            os.unlink(path)
        except OSError:
            pass
        raise
    return path


def validate_cookie_file(path):
    """Valida que o arquivo de cookies é Netscape válido carregando-o com o yt-dlp.

    Lança SystemExit se o arquivo não pode ser carregado, com mensagem clara.
    """
    try:
        from yt_dlp.cookies import YoutubeDLCookieJar
        jar = YoutubeDLCookieJar(path)
        jar.load()
        return len(jar)
    except Exception as exc:
        raise SystemExit(
            f"Arquivo de cookies inválido para o yt-dlp: {path}\n"
            f"Erro: {exc}\n"
            f"Primeira linha: {Path(path).read_text(errors='replace').splitlines()[:1]!r}"
        )
