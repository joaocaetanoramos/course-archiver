import re


def resolve_stream(embed_url, session):
    if "mediadelivery.net" in embed_url or ".b-cdn.net" in embed_url:
        return resolve_bunny(embed_url, session)
    if "pandavideo" in embed_url and "player-vz-" in embed_url:
        return resolve_pandavideo(embed_url, session)
    if "scaleup.com.br" in embed_url:
        return resolve_scaleup(embed_url, session)
    if "play.hotmart.com" in embed_url or "cf-embed" in embed_url:
        return resolve_hotmart(embed_url, session)
    if "youtube.com" in embed_url or "youtu.be" in embed_url:
        return resolve_youtube(embed_url)
    return {"kind": "ytdlp", "url": embed_url}


def resolve_bunny(embed_url, session):
    html = session.get(embed_url, timeout=60).text
    m = re.search(r"https://vz-[^'\"]+\.b-cdn\.net/[^'\"]+/playlist\.m3u8", html)
    if not m:
        raise RuntimeError(f"Não encontrei playlist.m3u8 no embed Bunny {embed_url}")
    return {"kind": "ytdlp", "url": m.group(0)}


def resolve_pandavideo(embed_url, session):
    pullzone = re.search(r"player-(vz-[a-z0-9]+-[a-z0-9]+)", embed_url)
    video_id = re.search(r"[?&]v=([a-z0-9-]+)", embed_url)
    if not pullzone or not video_id:
        raise RuntimeError(f"Não consegui extrair pullzone/video_id do PandaVideo {embed_url}")
    master_url = f"https://b-{pullzone.group(1)}.tv.pandavideo.com.br/{video_id.group(1)}/playlist.m3u8"
    return {"kind": "ytdlp", "url": master_url}


def resolve_scaleup(embed_url, session):
    html = session.get(embed_url, timeout=60).text
    m = re.search(r'id="hls-prefetch-url"[^>]*content="([^"]+)"', html)
    if not m:
        m = re.search(r'name="hls-prefetch-url"[^>]*content="([^"]+)"', html)
    if not m:
        raise RuntimeError(f"Não encontrei hls-prefetch-url no embed Scaleup {embed_url}")
    master_url = m.group(1).replace("&amp;", "&")
    return {"kind": "ytdlp", "url": master_url}


def resolve_hotmart(embed_url, session):
    html = session.get(embed_url, timeout=60).text
    m = re.search(r"https://vod-akm\.play\.hotmart\.com/video/[^\"'\s]+\.m3u8[^\"'\s]*", html)
    if not m:
        raise RuntimeError(f"Não encontrei master.m3u8 no embed Hotmart {embed_url}")
    master_url = m.group(0).replace("\\u0026", "&").replace("\\/", "/")
    return {"kind": "ytdlp", "url": master_url}


def resolve_youtube(embed_url):
    m = re.search(r"youtube\.com/embed/([a-zA-Z0-9_-]+)", embed_url)
    if m:
        return {
            "kind": "ytdlp",
            "url": f"https://www.youtube.com/watch?v={m.group(1)}",
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        }
    return {"kind": "ytdlp", "url": embed_url, "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"}
