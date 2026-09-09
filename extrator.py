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

from lib import downloader, estimate, streams
from lib.cookies import TolerantSession, load_cookies, validate_cookie_file, write_netscape_cookie_file
from lib.platforms import AuthError, RateLimitedError, detect_platform
from lib.progress import ProgressBar, listing_progress, print_line
from lib.request import RequestPacer


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
        self.pacer = RequestPacer()
        self._throttle_lock = threading.Lock()
        self._throttle_hits = {}
        self._bail_hosts = set()

    def session(self):
        s = getattr(self._tls, "session", None)
        if s is None:
            s = TolerantSession()
            s.cookies.update(self.cookie_jar)
            s.headers.update({"User-Agent": USER_AGENT, "Referer": self.url})
            self._gate_session(s)
            self._tls.session = s
        return s

    def _gate_session(self, s):
        def gated(method):
            def inner(url, *args, **kwargs):
                host = urlparse(url).netloc
                self.pacer.wait(host)
                resp = method(url, *args, **kwargs)
                if getattr(resp, "status_code", None) == 429:
                    self.pacer.note_throttle(host)
                    self.pacer.wait(host)
                    resp = method(url, *args, **kwargs)
                    if getattr(resp, "status_code", None) == 429:
                        exc = RateLimitedError(f"HTTP 429 em {url} (após cooldown)")
                        exc.host = host
                        raise exc
                return resp
            return inner

        s.get = gated(s.get)
        s.post = gated(s.post)

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
        except RateLimitedError as exc:
            title = course.get("title") or course.get("id") or "?"
            print_line(f"  [yellow]Erro ao listar aulas de {title}:[/yellow] {exc} (rate limit)")
            return None
        except Exception as exc:
            title = course.get("title") or course.get("id") or "?"
            print_line(f"  [red]Erro ao listar aulas de {title}:[/red] {exc}")
            return None
        return [
            (idx, lesson)
            for idx, lesson in enumerate(lessons, start=1)
            if not self.only_lessons or lesson["id"] in self.only_lessons
        ]

    def _note_probe_throttle(self, host):
        with self._throttle_lock:
            self._throttle_hits[host] = self._throttle_hits.get(host, 0) + 1
            if self._throttle_hits[host] >= 3:
                self._bail_hosts.add(host)

    def _note_probe_success(self, host):
        with self._throttle_lock:
            self._throttle_hits[host] = 0

    def _should_bail(self, host):
        with self._throttle_lock:
            return host in self._bail_hosts

    def _lesson_estimate(self, platform, course, lesson, idx):
        host = urlparse(lesson.get("url") or "").netloc
        try:
            session = self.session()
            embed = platform.extract_video(lesson, session)
            if not embed:
                return (None, None)
            stream = streams.resolve_stream(embed, session)
            est = estimate.probe_stream(stream, session)
            self._note_probe_success(host)
            return est
        except RateLimitedError as exc:
            self._note_probe_throttle(getattr(exc, "host", None) or host)
            return (None, None)
        except Exception:
            return (None, None)

    def _probe_lessons(self, platform, course, lessons):
        est_by_idx = {}
        with self._throttle_lock:
            self._bail_hosts.clear()
            self._throttle_hits.clear()

        def run(idx, lesson):
            host = urlparse(lesson.get("url") or "").netloc
            if self._should_bail(host):
                est = (None, None)
            else:
                est = self._lesson_estimate(platform, course, lesson, idx)
            time.sleep(random.uniform(0.02, 0.08))
            return idx, est

        def do_probe():
            workers = min(6, len(lessons)) if lessons else 1
            if workers <= 1:
                for pos, (idx, lesson) in enumerate(lessons, start=1):
                    i, est = run(idx, lesson)
                    est_by_idx[i] = est
                    yield pos
            else:
                with ThreadPoolExecutor(max_workers=workers) as pool:
                    futures = [pool.submit(run, idx, lesson) for idx, lesson in lessons]
                    done = 0
                    for fut in as_completed(futures):
                        i, est = fut.result()
                        est_by_idx[i] = est
                        done += 1
                        yield done

        title = self._shorten(course.get("title") or course.get("id") or "?", 40)
        host = urlparse(course.get("url") or course.get("id") or "").netloc
        base_desc = f"Listando {title}…"

        with listing_progress(len(lessons), base_desc) as (update, set_desc, _progress, _task_id):
            for done in do_probe():
                update(done)
                if self.pacer.throttled(host):
                    set_desc(base_desc + " [yellow](rate limit…)[/yellow]")
                else:
                    set_desc(base_desc)
        return est_by_idx

    @staticmethod
    def _est_str(size, duration):
        parts = []
        d = estimate.format_duration(duration)
        s = estimate.format_bytes(size)
        if d:
            parts.append(d)
        if s != "n/d":
            parts.append(s)
        return " · ".join(parts) if parts else "n/d"

    @staticmethod
    def _sum_est(items):
        size = 0
        dur = 0.0
        for _, _, (s, d) in items:
            if s:
                size += s
            if d:
                dur += d
        return size, dur

    @staticmethod
    def _totals_str(n, size, duration):
        parts = [f"{n} aula(s)"]
        s = estimate.format_bytes(size)
        if s != "n/d":
            parts.append(s)
        d = estimate.format_duration(duration)
        if d:
            parts.append(d)
        return " · ".join(parts)

    def _list(self, platform, courses):
        grand_size = 0
        grand_dur = 0.0
        grand_lessons = 0
        grand_courses = 0

        for course in self._select_courses(courses):
            cid = course.get("course_id", course.get("id", ""))
            slug = course.get("slug") or course.get("url") or ""
            print_line()
            print_line(f"[bold]{course.get('title') or cid}[/bold]  [dim]id={cid} | {slug}[/dim]")

            lessons = self._load_lessons(platform, course)
            if not lessons:
                continue

            est_by_idx = self._probe_lessons(platform, course, lessons)

            chapters = {}
            for idx, lesson in lessons:
                key = lesson.get("chapter") or course.get("title") or cid
                chapters.setdefault(key, []).append((idx, lesson))

            if self.ls in ("chapters", "lessons"):
                for chapter, items in chapters.items():
                    c_items = [(idx, lesson, est_by_idx.get(idx, (None, None))) for idx, lesson in items]
                    ch_size, ch_dur = self._sum_est(c_items)
                    print_line(
                        f"  [bold underline]{chapter}[/bold underline]  "
                        f"[dim]({self._totals_str(len(items), ch_size, ch_dur)})[/dim]"
                    )
                    if self.ls == "lessons":
                        for idx, lesson in items:
                            size, duration = est_by_idx.get(idx, (None, None))
                            print_line(
                                f"    [dim]{lesson['id']:<12}[/dim] {lesson['title']}  "
                                f"[dim]({self._est_str(size, duration)})[/dim]"
                            )

            c_items = [(idx, lesson, est_by_idx.get(idx, (None, None))) for idx, lesson in lessons]
            c_size, c_dur = self._sum_est(c_items)
            print_line(f"  [dim]{self._totals_str(len(lessons), c_size, c_dur)}[/dim]")

            grand_size += c_size
            grand_dur += c_dur
            grand_lessons += len(lessons)
            grand_courses += 1

        print_line()
        print_line(
            f"[bold underline]Total:[/bold underline] "
            f"{self._totals_str(grand_lessons, grand_size, grand_dur)} "
            f"em {grand_courses} curso(s)."
        )

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
                suffix = f"  [dim]({estimate.format_bytes(res.get('size'))})[/dim]" if res.get("size") else ""
                print_line(f"[green]{k}/{total}[/green] [bold]{title}[/bold]{suffix}")
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
        totale = sum(r.get("size") or 0 for r in results)
        summary = f"  → {ok} baixado(s), {skipped} sem vídeo, {errs} erro(s)."
        if totale:
            summary = summary[:-1] + f" · {estimate.format_bytes(totale)}."
        print_line(summary)

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
            try:
                size = dest_mp4.stat().st_size
            except OSError:
                size = None
            return {"lesson": lesson, "status": "ja-baixado", "size": size}

        embed = platform.extract_video(lesson, session)
        if not embed:
            return {"lesson": lesson, "status": "sem-video"}
        stream = streams.resolve_stream(embed, session)
        probe_size, _ = estimate.probe_stream(stream, session)

        desc = self._shorten(lesson["title"])
        bar = ProgressBar(total=probe_size, desc=desc)
        stats = {"value": 0, "total": probe_size, "t0": time.monotonic()}

        def on_progress(value, total):
            if total and stats["total"] != total:
                stats["total"] = total
                bar.set_total(total)
            stats["value"] = max(stats["value"], value)
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
                    try:
                        size = dest_mp4.stat().st_size
                    except OSError:
                        size = stats["value"] or stats["total"]
                    return {
                        "lesson": lesson,
                        "status": "baixado",
                        "size": size,
                        "elapsed": time.monotonic() - stats["t0"],
                    }
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
