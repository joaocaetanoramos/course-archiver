import re


def resolve_stream(embed_url, session):
    if "player.vimeo.com/video" in embed_url:
        return resolve_memberkit_vimeo(embed_url, session)
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
    html = session.get(embed_url, headers={"Referer": "https://hotmart.com/"}, timeout=60).text
    m = re.search(r"https://vod-akm\.play\.hotmart\.com/video/[^\"'\s]+\.m3u8[^\"'\s]*", html)
    if not m:
        raise RuntimeError(f"Não encontrei master.m3u8 no embed Hotmart {embed_url}")
    master_url = m.group(0).replace("\\u0026", "&").replace("\\/", "/")
    return {
        "kind": "ytdlp",
        "url": master_url,
        "http_headers": {
            "Referer": "https://cf-embed.play.hotmart.com/",
            "Origin": "https://cf-embed.play.hotmart.com",
        },
    }


def resolve_memberkit_vimeo(embed_url, session):
    uid = re.search(r"player\.vimeo\.com/video/(\d+)", embed_url)
    ref = re.search(r"[?&]memberkit_ref=([^&]+)", embed_url)
    if not uid:
        raise RuntimeError(f"URL de embed Vimeo inválida {embed_url}")
    player_url = f"https://player.vimeo.com/video/{uid.group(1)}?title=0&byline=0&portrait=0&speed=1&transparent=0&app_id=122963"
    referer = player_url
    import urllib.parse as up
    lesson_ref = up.unquote(ref.group(1)) if ref else "https://vimeo.com/"
    headers = {"User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
    )}

    html = session.get(player_url, headers={**headers, "Referer": lesson_ref}, timeout=30).text
    m = re.search(r'[^"\s]*config/request[^"]*', html)
    if not m:
        raise RuntimeError(f"Não encontrei config do player Vimeo no embed {embed_url}")
    config_url = m.group(0).replace("\\u0026", "&").replace("&amp;", "&")
    config = session.get(
        config_url,
        headers={**headers, "Referer": referer},
        timeout=30,
    ).json()

    hls = (config.get("files", {}) or {}).get("hls", {})
    cdns = hls.get("cdns", {})
    default_cdn = hls.get("default_cdn") or "akfire_interconnect_quic"
    if default_cdn not in cdns:
        default_cdn = next(iter(cdns), None)
    if not default_cdn:
        raise RuntimeError(f"Config Vimeo sem playlists HLS no embed {embed_url}")
    return {
        "kind": "ytdlp",
        "url": cdns[default_cdn]["url"],
        "http_headers": {"Referer": referer},
    }


def resolve_youtube(embed_url):
    m = re.search(r"youtube\.com/embed/([a-zA-Z0-9_-]+)", embed_url)
    if m:
        return {
            "kind": "ytdlp",
            "url": f"https://www.youtube.com/watch?v={m.group(1)}",
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        }
    return {"kind": "ytdlp", "url": embed_url, "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"}
