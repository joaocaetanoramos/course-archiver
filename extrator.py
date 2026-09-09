#!/usr/bin/env python3
"""Extrai vídeos de cursos para assistir offline."""

import argparse
import os
import random
import re
import requests
import shutil
import threading
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse

from lib import downloader, streams
from lib.cookies import TolerantSession, load_cookies, validate_cookie_file, write_netscape_cookie_file
from lib.platforms import AuthError, detect_platform
from lib.progress import ProgressBar, print_line


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def find_ffmpeg():
    override = os.environ.get("FFMPEG_PATH")
    if override and os.path.isfile(override):
        return override
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import static_ffmpeg

        static_ffmpeg.add_paths()
        return shutil.which("ffmpeg")
    except Exception:
        return None


def sanitize_filename(name):
    name = unicodedata.normalize("NFC", name)
    name = INVALID_FILENAME_CHARS.sub("-", name)
    name = re.sub(r"\s+", " ", name).strip(" .")
    return name or "sem-titulo"


class App:
    LS_LEVELS = ("courses", "chapters", "lessons")

    def __init__(self, url, cookies, output, parallel, ls, ffmpeg, only_courses, only_lessons, concurrent, retries):
        self.url = url
        self.host = urlparse(url).netloc
        self.cookie_jar = load_cookies(cookies, self.host) if cookies else requests.cookies.RequestsCookieJar()
        self.cookie_file = None
        if ls is None and cookies:
            self.cookie_file = write_netscape_cookie_file(self.cookie_jar, self.host)
            validate_cookie_file(self.cookie_file)
        self.output_dir = Path(output)
        self.parallel = max(1, int(parallel))
        self.concurrent = max(1, int(concurrent))
        self.retries = max(1, int(retries))
        self.ls = ls
        self.ffmpeg = ffmpeg or find_ffmpeg()
        self.only_courses = set(filter(None, (only_courses or "").split(",")))
        self.only_lessons = set(filter(None, (only_lessons or "").split(",")))
        self._tls = threading.local()
        self._concurrent_lock = threading.Lock()

    def session(self):
        s = getattr(self._tls, "session", None)
        if s is None:
            s = TolerantSession()
            s.cookies.update(self.cookie_jar)
            s.headers.update({"User-Agent": USER_AGENT, "Referer": self.url})
            self._tls.session = s
        return s

    def _select_courses(self, courses):
        for course in courses:
            if self.only_courses:
                cid = course.get("course_id", course.get("id", ""))
                if cid not in self.only_courses and course.get("slug", "") not in self.only_courses:
                    continue
            yield course

    def _load_lessons(self, platform, course):
        try:
            lessons = platform.list_lessons(course, self.session())
        except Exception as exc:
            title = course.get("title") or course.get("id") or "?"
            print_line(f"  [red]Erro ao listar aulas de {title}:[/red] {exc}")
            return None
        return [
            (idx, lesson)
            for idx, lesson in enumerate(lessons, start=1)
            if not self.only_lessons or lesson["id"] in self.only_lessons
        ]

    def _list(self, platform, courses):
        for course in self._select_courses(courses):
            cid = course.get("course_id", course.get("id", ""))
            slug = course.get("slug") or course.get("url") or ""
            print_line()
            print_line(f"[bold]{course.get('title') or cid}[/bold]  [dim]id={cid} | {slug}[/dim]")

            if self.ls not in ("chapters", "lessons"):
                continue

            lessons = self._load_lessons(platform, course)
            if not lessons:
                continue

            chapters = {}
            for idx, lesson in lessons:
                chapters.setdefault(lesson.get("chapter") or course.get("title") or cid, []).append((idx, lesson))

            for chapter, items in chapters.items():
                print_line(f"  [bold underline]{chapter}[/bold underline]  [dim]({len(items)} aula(s))[/dim]")
                if self.ls == "lessons":
                    for idx, lesson in items:
                        print_line(f"    [dim]{lesson['id']:<12}[/dim] {lesson['title']}")

    def run(self):
        try:
            try:
                platform = detect_platform(self.url)
                courses = platform.discover(self.url, self.session())
            except AuthError as exc:
                print_line(f"[red]Erro de autenticação:[/red] {exc}")
                print_line(
                    "[yellow]Seu cookie pode ter expirado ou não ter permissão para esta URL. "
                    "Reexporte o cookie do navegador logado na plataforma.[/yellow]"
                )
                return
            except Exception as exc:
                print_line(f"[red]Erro ao descobrir cursos:[/red] {exc}")
                return
            print_line(f"Plataforma: [bold]{platform.name}[/bold] | {len(courses)} curso(s).")

            if self.ls:
                self._list(platform, courses)
                return

            for course in self._select_courses(courses):
                lessons = self._load_lessons(platform, course)
                if not lessons:
                    continue

                chapter = (lessons[0][1].get("chapter") or course.get("title") or course.get("id")) if lessons else (course.get("title") or course.get("id"))
                print_line()
                print_line(f"[bold underline]== {chapter}[/bold underline]  [dim]({len(lessons)} aula(s))[/dim]")
                try:
                    self._process_chapter(platform, course, lessons)
                except Exception as exc:
                    title = course.get("title") or course.get("id") or "?"
                    print_line(f"  [red]Erro ao processar {title}:[/red] {exc}")
        finally:
            if self.cookie_file:
                try:
                    os.unlink(self.cookie_file)
                except OSError:
                    pass

    def _process_chapter(self, platform, course, lessons):
        total = len(lessons)

        results = []
        counter = {"n": 0}
        lock = threading.Lock()

        def finish(res):
            with lock:
                counter["n"] += 1
                k = counter["n"]
            status = res.get("status")
            title = res["lesson"]["title"]
            if status in ("baixado", "ja-baixado"):
                print_line(f"[green]{k}/{total}[/green] [bold]{title}[/bold]")
            elif status == "sem-video":
                print_line(f"[dim]{k}/{total} — {title} (sem vídeo)[/dim]")
            else:
                print_line(f"[red]{k}/{total} ERRO[/red] {title}: {res.get('error')}")
            results.append(res)

        if self.parallel == 1:
            for idx, lesson in lessons:
                res = self._process_lesson(platform, course, lesson, idx)
                finish(res)
        else:
            with ThreadPoolExecutor(max_workers=self.parallel) as pool:
                futures = {}
                for idx, lesson in lessons:
                    fut = pool.submit(self._process_lesson, platform, course, lesson, idx)
                    futures[fut] = lesson
                for fut in as_completed(futures):
                    try:
                        res = fut.result()
                    except Exception as exc:
                        res = {"lesson": futures[fut], "status": "erro", "error": str(exc)}
                    finish(res)

        ok = sum(1 for r in results if r.get("status") in ("baixado", "ja-baixado"))
        errs = sum(1 for r in results if r.get("status") == "erro")
        skipped = sum(1 for r in results if r.get("status") == "sem-video")
        print_line(f"  → {ok} baixado(s), {skipped} sem vídeo, {errs} erro(s).")

    def _throttle_down(self):
        with self._concurrent_lock:
            if self.concurrent > 1:
                new_val = max(1, self.concurrent // 2)
                print_line(
                    f"  [yellow]Conexão instável — reduzindo segmentos por vídeo de "
                    f"{self.concurrent} para {new_val}.[/yellow]"
                )
                self.concurrent = new_val

    def _process_lesson(self, platform, course, lesson, idx):
        session = self.session()
        group = lesson.get("group") or ""
        chapter = lesson.get("chapter") or course.get("title") or ""

        parts = [str(self.output_dir)]
        if group:
            parts.append(sanitize_filename(group))
        if chapter:
            parts.append(sanitize_filename(chapter))
        lesson_dir = Path(*parts)
        base_name = f"{idx:02d} - {sanitize_filename(lesson['title'])}"
        dest_mp4 = lesson_dir / (base_name + ".mp4")

        if dest_mp4.exists():
            return {"lesson": lesson, "status": "ja-baixado"}

        embed = platform.extract_video(lesson, session)
        if not embed:
            return {"lesson": lesson, "status": "sem-video"}
        stream = streams.resolve_stream(embed, session)

        desc = self._shorten(lesson["title"])
        bar = ProgressBar(total=None, desc=desc)

        def on_progress(value, total):
            if total:
                bar.set_total(total)
            bar.update_to(value)

        metadata = {
            "title": lesson["title"],
            "album": chapter,
            "artist": group,
            "comment": lesson["url"],
        }

        def _do_download():
            downloader.download_ytdlp(
                stream["url"], dest_mp4, metadata, self.cookie_file, self.ffmpeg,
                on_progress, stream.get("format", "bestvideo+bestaudio/best"), self.concurrent,
                stream.get("http_headers"),
            )

        def _is_connection_error(exc):
            msg = repr(exc) + str(exc)
            return (
                "Connection reset" in msg
                or "Connection aborted" in msg
                or "Read timed out" in msg
                or "timed out" in msg.lower()
            )

        try:
            lesson_dir.mkdir(parents=True, exist_ok=True)
            last_exc = None
            cookie_regenerated = False
            for attempt in range(self.retries):
                try:
                    _do_download()
                    return {"lesson": lesson, "status": "baixado"}
                except Exception as exc:
                    err = str(exc)
                    last_exc = exc
                    is_conn = _is_connection_error(exc)
                    is_cookie = "Netscape format" in err

                    if is_cookie and self.cookie_jar is not None and not cookie_regenerated:
                        old_cookie = self.cookie_file
                        if old_cookie:
                            try:
                                os.unlink(old_cookie)
                            except OSError:
                                pass
                        self.cookie_file = write_netscape_cookie_file(self.cookie_jar, self.host)
                        cookie_regenerated = True
                        continue

                    if is_conn:
                        self._throttle_down()

                    is_last = attempt + 1 >= self.retries
                    if is_last:
                        break

                    backoff = min(30.0, 2.0 * (2 ** attempt)) + random.uniform(0, 1.0)
                    print_line(
                        f"  [yellow]Erro de rede ({attempt + 1}/{self.retries}): "
                        f"{type(exc).__name__} — retentando em {backoff:.1f}s[/yellow]"
                    )
                    time.sleep(backoff)

            return {
                "lesson": lesson,
                "status": "erro",
                "error": f"{type(last_exc).__name__}: {last_exc}",
            }
        finally:
            bar.close()

    @staticmethod
    def _shorten(text, limit=42):
        text = text.strip()
        return text if len(text) <= limit else text[: limit - 1] + "…"


def main():
    parser = argparse.ArgumentParser(description="Extrai vídeos de cursos para assistir offline.")
    parser.add_argument("url", help="URL do dashboard, do curso ou de um vídeo")
    parser.add_argument("--cookies", help="Arquivo de cookies (Netscape/JSON) ou string 'Cookie:' crua (obrigatório)")
    parser.add_argument("--output", default="./downloads", help="Diretório de saída")
    parser.add_argument("--parallel", type=int, default=1, help="Número de downloads em paralelo")
    parser.add_argument("--concurrent", type=int, default=8, help="Segmentos baixados em paralelo por vídeo")
    parser.add_argument("--retries", type=int, default=3, help="Tentativas por aula em caso de erro de rede transitório")
    parser.add_argument("--ls", nargs="?", const="lessons", choices=App.LS_LEVELS,
                        help="Lista sem baixar. Níveis: courses, chapters, lessons. "
                             "Sem valor lista tudo (courses + chapters + lessons). "
                             "Ex.: --ls courses / --ls")
    parser.add_argument("--ffmpeg", help="Caminho do executável ffmpeg (opcional)")
    parser.add_argument("--course", help="Filtra por slug ou id de curso (separado por vírgula)")
    parser.add_argument("--lesson", help="Filtra por id de aula (separado por vírgula)")

    args = parser.parse_args()
    if not args.cookies:
        parser.error("informe --cookies arquivo.txt")

    ls = args.ls

    app = App(
        url=args.url,
        cookies=args.cookies,
        output=args.output,
        parallel=args.parallel,
        ls=ls,
        ffmpeg=args.ffmpeg,
        only_courses=args.course,
        only_lessons=args.lesson,
        concurrent=args.concurrent,
        retries=args.retries,
    )
    if app.ls is None and not app.ffmpeg:
        raise SystemExit("ffmpeg não encontrado. Instale ou defina FFMPEG_PATH.")
    app.run()


if __name__ == "__main__":
    main()
