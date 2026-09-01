import glob
import os
import subprocess


def download_ytdlp(url, dest_mp4, metadata, cookie_file, ffmpeg, on_progress, fmt="bestvideo+bestaudio/best", concurrent=8):
    import yt_dlp

    prefix = str(dest_mp4.with_suffix("")) + ".dl"
    tmp = dest_mp4.with_suffix(".mp4.part")

    def hook(d):
        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            on_progress(d.get("downloaded_bytes", 0), total)

    opts = {
        "outtmpl": prefix + ".%(ext)s",
        "format": fmt,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "progress_hooks": [hook],
        "concurrent_fragment_downloads": int(concurrent),
        "merge_output_format": "mp4",
    }
    if ffmpeg:
        opts["ffmpeg_location"] = ffmpeg
    if cookie_file:
        opts["cookiefile"] = cookie_file

    downloaded_path = None
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)

        for d in (info.get("requested_downloads") or []):
            downloaded_path = d.get("filepath")
            break
        if not downloaded_path:
            candidates = glob.glob(prefix + ".*")
            if not candidates:
                raise RuntimeError("yt-dlp não produziu arquivo de saída.")
            downloaded_path = candidates[0]

        tag_with_ffmpeg(downloaded_path, tmp, metadata, ffmpeg)
        tmp.rename(dest_mp4)
    finally:
        for cand in glob.glob(prefix + ".*"):
            try:
                os.remove(cand)
            except OSError:
                pass
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def tag_with_ffmpeg(src, tmp, metadata, ffmpeg):
    cmd = [
        ffmpeg, "-y", "-loglevel", "error",
        "-i", src,
        "-c", "copy", "-movflags", "+faststart", "-f", "mp4",
        "-metadata", f"title={metadata['title']}",
        "-metadata", f"album={metadata['album']}",
        "-metadata", f"artist={metadata['artist']}",
        "-metadata", f"comment={metadata['comment']}",
        str(tmp),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        if tmp.exists():
            tmp.unlink()
        raise RuntimeError(f"ffmpeg falhou ao gravar metadados: {proc.stderr.strip()[:500]}")
