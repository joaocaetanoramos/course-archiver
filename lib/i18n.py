"""Lightweight UI localization.

Single-file message catalog without dependency on gettext/.po tooling.
English is the default language; any language falls back to English for
missing keys, so adding a new locale only requires:
  1. a new dict in MESSAGES,
  2. an entry in LANGUAGES,
  3. an entry in PLURAL_FORM_COUNT.
"""

import locale
import os

DEFAULT_LANG = "en"

LANGUAGES = {
    "en": "English",
    "pt": "Português",
}

# Number of grammatical plural forms per language (0 = only one form).
# en/pt: one form for singular, one for everything else.
PLURAL_FORM_COUNT = {
    "en": 2,
    "pt": 2,
}

_state = {"lang": DEFAULT_LANG}


def _from_env():
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        val = os.environ.get(var)
        if not val:
            continue
        val = val.strip()
        if not val or val.lower() in ("c", "posix"):
            continue
        code = val.split(".")[0].split("_")[0].split("@")[0].lower()
        if code:
            return code
    try:
        code = (locale.getlocale()[0] or "").split("_")[0].lower()
        if code:
            return code
    except Exception:
        pass
    return None


def language_code(override=None):
    if override and override != "auto":
        return override if override in LANGUAGES else DEFAULT_LANG
    code = _from_env()
    return code if code in LANGUAGES else DEFAULT_LANG


def init(override=None):
    _state["lang"] = language_code(override)
    return current_lang()


def current_lang():
    return _state["lang"]


def decimal_sep():
    return "," if current_lang() == "pt" else "."


def _plural_index(lang, n):
    forms = PLURAL_FORM_COUNT.get(lang, 2)
    if forms <= 1:
        return 0
    if forms == 2:
        return 0 if n == 1 else 1
    # General fallback for languages with 3+ forms (Slavic, Arabic, …).
    if n % 10 == 1 and n % 100 != 11:
        return 0
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return 1
    return 2


def _lookup(key):
    lang = current_lang()
    table = MESSAGES.get(lang)
    if table is not None and key in table:
        return table[key]
    base = MESSAGES.get(DEFAULT_LANG, {})
    return base.get(key, key)


def t(key, **kwargs):
    tpl = _lookup(key)
    if isinstance(tpl, (tuple, list)):
        tpl = tpl[0]
    if isinstance(tpl, str):
        if kwargs:
            try:
                return tpl.format(**kwargs)
            except (KeyError, IndexError, ValueError):
                return tpl
        # No placeholders to fill: just collapse escaped braces ({{id}} -> {id}).
        return tpl.replace("{{", "{").replace("}}", "}")
    return tpl


def nt(key, n, **kwargs):
    tpl = _lookup(key)
    if isinstance(tpl, (tuple, list)):
        tpl = tpl[_plural_index(current_lang(), n)]
    try:
        return tpl.format(n=n, **kwargs)
    except (KeyError, IndexError, ValueError):
        return f"{n} {tpl}"


MESSAGES = {
    "en": {
        # CLI / argparse
        "cli.description": "Download online course videos for offline viewing.",
        "cli.url_help": "Dashboard, course or lesson URL",
        "cli.cookies_help": "Cookies file (Netscape/JSON) or raw 'Cookie:' string (required)",
        "cli.output_help": "Output directory",
        "cli.parallel_help": "Number of parallel lesson downloads",
        "cli.concurrent_help": "HLS fragments downloaded in parallel per video",
        "cli.retries_help": "Attempts per lesson on transient network errors",
        "cli.ls_help": (
            "List without downloading. Levels: courses, chapters, lessons. "
            "With no value lists everything (courses + chapters + lessons). "
            "e.g.: --ls courses / --ls"
        ),
        "cli.lang_help": "UI language (auto uses the system language)",
        "cli.ffmpeg_help": "Path to the ffmpeg executable (optional)",
        "cli.course_help": "Filter by course slug or id (comma-separated)",
        "cli.lesson_help": "Filter by lesson id (comma-separated)",
        "cli.cookies_required": "provide --cookies <file>",
        "cli.ffmpeg_missing": "ffmpeg not found. Install it or set FFMPEG_PATH.",

        # Listing / errors
        "ui.list_lessons_rate_err": "  [yellow]Error listing lessons of {title}:[/yellow] {exc} (rate limit)",
        "ui.list_lessons_err": "  [red]Error listing lessons of {title}:[/red] {exc}",
        "ui.listing_desc": "Listing {title}…",
        "ui.rate_limit_hint_markup": "[yellow](rate limit…)[/yellow]",
        "ui.rate_after_cooldown": "HTTP 429 at {url} (after cooldown)",

        # Counts
        "ui.lesson_count": ("{n} lesson", "{n} lessons"),
        "ui.course_count": ("{n} course", "{n} courses"),
        "ui.attach_count": ("{n} attachment", "{n} attachments"),
        "ui.downloaded": ("{n} downloaded", "{n} downloaded"),
        "ui.no_video": ("{n} no video", "{n} no video"),
        "ui.err": ("{n} error", "{n} errors"),

        # Chapter/download flow
        "ui.chapter_summary": "  → {ok}, {no_video}, {errs}",
        "ui.attachments_with_error": "({n} with errors)",
        "ui.no_video_tag": "(no video)",
        "ui.error_tag": "ERROR",
        "ui.grand_total": "[bold underline]Total:[/bold underline] {totals} across {courses}.",
        "ui.platform_line": "Platform: [bold]{platform}[/bold] | {count}.",
        "ui.chapter_header": "[bold underline]== {chapter}[/bold underline]  [dim]({count})[/dim]",
        "ui.auth_error": "[red]Authentication error:[/red]",
        "ui.cookie_expired_hint": (
            "[yellow]Your cookie may have expired or may not have access to this URL. "
            "Re-export the cookie from your logged-in browser on the platform.[/yellow]"
        ),
        "ui.discover_error": "[red]Error discovering courses:[/red]",
        "ui.process_error": "  [red]Error processing {title}:[/red]",
        "ui.throttle_down": (
            "  [yellow]Unstable connection — reducing fragments per video "
            "from {old} to {new_val}.[/yellow]"
        ),
        "ui.network_retry": (
            "  [yellow]Network error ({attempt}/{retries}): {errtype} — "
            "retrying in {backoff:.1f}s[/yellow]"
        ),
        "ui.anexo_line": "  [dim]attachment: {name} ({size})[/dim]",
        "ui.anexo_rate_err": "  [dim][yellow]attachment: {name} — {exc} (rate limit)[/yellow][/dim]",
        "ui.anexo_err": "  [dim][red]attachment ERROR[/red] {name}: {exc}[/dim]",

        # lib/platforms.py
        "ui.auth_http_empty": (
            "HTTP {code} (empty response) at {url}. The API rejected the authentication.\n"
            "For Hotmart: the gateway requires the 'Authorization: Bearer <hmVlcIntegration>' "
            "header. Export the hmVlcIntegration cookie logged in at consumer.hotmart.com "
            "(F12 > Application > Cookies) and pass it with --cookies.\n"
            "For other platforms: re-export the browser cookies while logged in."
        ),
        "ui.auth_html_login": (
            "HTTP {code} — login HTML response at {url}. Your session expired. "
            "Log in again in the browser and re-export the cookies."
        ),
        "ui.auth_http": "HTTP {code} (authentication) at {url}",
        "ui.rate_limited": "HTTP 429 (rate limit) at {url}",
        "ui.http_error": "HTTP {code} at {url}: {body}",
        "ui.http_status": "HTTP {code} at {url}",
        "ui.hotmart_no_token": (
            "Hotmart: cookie 'hmVlcIntegration' not found in the loaded cookies.\n"
            "The Hotmart gateway authenticates via 'Authorization: Bearer <hmVlcIntegration>' "
            "(not via session cookies).\n"
            "Export the hmVlcIntegration cookie logged in at consumer.hotmart.com "
            "(F12 > Application > Cookies > https://consumer.hotmart.com) and pass it with --cookies.\n"
            "Export manually: Chrome 127+ encrypts this cookie (App-Bound Encryption) and a "
            "direct browser read may return it empty."
        ),
        "ui.hotmart_bad_url": (
            "Invalid Hotmart URL. Use the product URL: .../club/{{slug}}/products/{{id}}"
        ),
        "ui.astron_not_auth": "Session not authenticated. Check your cookie.",
        "ui.kiwify_no_token": (
            "Kiwify: authentication token not found. Export the id_token/access_token "
            "(localStorage) or use the Chrome extension."
        ),
        "ui.curseduca_unsupported": (
            "Curseduca is not fully supported yet: lesson discovery depends on the "
            "clas.curseduca.pro API (menus/current + contents/{{id}}). Implementation pending."
        ),
        "ui.video_label": "Video",
        "ui.memberkit_rate": "HTTP 429 at {url}. Too many requests — the server asked us to slow down.",
        "ui.memberkit_auth": (
            "HTTP {code} at {url}. Memberkit session expired — log in again in the browser "
            "and re-export the cookies."
        ),

        # lib/streams.py
        "ui.stream_bunny": "Could not find playlist.m3u8 in Bunny embed {url}",
        "ui.stream_panda": "Could not extract pullzone/video_id from PandaVideo embed {url}",
        "ui.stream_scaleup": "Could not find hls-prefetch-url in Scaleup embed {url}",
        "ui.stream_hotmart": "Could not find master.m3u8 in Hotmart embed {url}",
        "ui.stream_vimeo_url": "Invalid Vimeo embed URL {url}",
        "ui.stream_vimeo_config": (
            "Could not find Vimeo player config in embed {url} — the lesson may be "
            "removed or restricted (player page returned no config)."
        ),
        "ui.stream_vimeo_config_http": "Vimeo config request for {url} returned HTTP {code}.",
        "ui.stream_vimeo_bad_json": (
            "Vimeo config for {url} was not valid JSON (empty/HTML response, {n} bytes)."
        ),
        "ui.stream_vimeo_hls": "Vimeo config has no HLS playlists in embed {url}",

        # lib/downloader.py
        "ui.dl_no_output": "yt-dlp did not produce an output file.",
        "ui.dl_ffmpeg_tags": "ffmpeg failed to write metadata: {err}",
        "ui.dl_ffmpeg_timeout": "ffmpeg timed out after {seconds}s while writing metadata.",

        # lib/cookies.py
        "ui.cookies_invalid": (
            "Invalid cookies file for yt-dlp: {path}\nError: {error}\nFirst line: {first}"
        ),
    },
    "pt": {
        # CLI / argparse
        "cli.description": "Extrai vídeos de cursos para assistir offline.",
        "cli.url_help": "URL do dashboard, do curso ou de um vídeo",
        "cli.cookies_help": "Arquivo de cookies (Netscape/JSON) ou string 'Cookie:' crua (obrigatório)",
        "cli.output_help": "Diretório de saída",
        "cli.parallel_help": "Número de downloads em paralelo",
        "cli.concurrent_help": "Segmentos baixados em paralelo por vídeo",
        "cli.retries_help": "Tentativas por aula em caso de erro de rede transitório",
        "cli.ls_help": (
            "Lista sem baixar. Níveis: courses, chapters, lessons. "
            "Sem valor lista tudo (courses + chapters + lessons). "
            "Ex.: --ls courses / --ls"
        ),
        "cli.lang_help": "Idioma da interface (auto usa o idioma do sistema)",
        "cli.ffmpeg_help": "Caminho do executável ffmpeg (opcional)",
        "cli.course_help": "Filtra por slug ou id de curso (separado por vírgula)",
        "cli.lesson_help": "Filtra por id de aula (separado por vírgula)",
        "cli.cookies_required": "informe --cookies arquivo.txt",
        "cli.ffmpeg_missing": "ffmpeg não encontrado. Instale ou defina FFMPEG_PATH.",

        # Listing / errors
        "ui.list_lessons_rate_err": "  [yellow]Erro ao listar aulas de {title}:[/yellow] {exc} (rate limit)",
        "ui.list_lessons_err": "  [red]Erro ao listar aulas de {title}:[/red] {exc}",
        "ui.listing_desc": "Listando {title}…",
        "ui.rate_limit_hint_markup": "[yellow](rate limit…)[/yellow]",
        "ui.rate_after_cooldown": "HTTP 429 em {url} (após cooldown)",

        # Counts
        "ui.lesson_count": ("{n} aula", "{n} aulas"),
        "ui.course_count": ("{n} curso", "{n} cursos"),
        "ui.attach_count": ("{n} anexo", "{n} anexos"),
        "ui.downloaded": ("{n} baixado", "{n} baixados"),
        "ui.no_video": ("{n} sem vídeo", "{n} sem vídeo"),
        "ui.err": ("{n} erro", "{n} erros"),

        # Chapter/download flow
        "ui.chapter_summary": "  → {ok}, {no_video}, {errs}",
        "ui.attachments_with_error": "({n} com erro)",
        "ui.no_video_tag": "(sem vídeo)",
        "ui.error_tag": "ERRO",
        "ui.grand_total": "[bold underline]Total:[/bold underline] {totals} em {courses}.",
        "ui.platform_line": "Plataforma: [bold]{platform}[/bold] | {count}.",
        "ui.chapter_header": "[bold underline]== {chapter}[/bold underline]  [dim]({count})[/dim]",
        "ui.auth_error": "[red]Erro de autenticação:[/red]",
        "ui.cookie_expired_hint": (
            "[yellow]Seu cookie pode ter expirado ou não ter permissão para esta URL. "
            "Reexporte o cookie do navegador logado na plataforma.[/yellow]"
        ),
        "ui.discover_error": "[red]Erro ao descobrir cursos:[/red]",
        "ui.process_error": "  [red]Erro ao processar {title}:[/red]",
        "ui.throttle_down": (
            "  [yellow]Conexão instável — reduzindo segmentos por vídeo de "
            "{old} para {new_val}.[/yellow]"
        ),
        "ui.network_retry": (
            "  [yellow]Erro de rede ({attempt}/{retries}): {errtype} — "
            "retentando em {backoff:.1f}s[/yellow]"
        ),
        "ui.anexo_line": "  [dim]anexo: {name} ({size})[/dim]",
        "ui.anexo_rate_err": "  [dim][yellow]anexo: {name} — {exc} (rate limit)[/yellow][/dim]",
        "ui.anexo_err": "  [dim][red]anexo ERRO[/red] {name}: {exc}[/dim]",

        # lib/platforms.py
        "ui.auth_http_empty": (
            "HTTP {code} (resposta vazia) em {url}. "
            "A API rejeitou a autenticação.\n"
            "Para Hotmart: o gateway exige o header 'Authorization: Bearer <hmVlcIntegration>'. "
            "Exporte o cookie hmVlcIntegration logado em consumer.hotmart.com "
            "(F12 > Application > Cookies) e use --cookies com ele.\n"
            "Para outras plataformas: reexporte os cookies do navegador logado."
        ),
        "ui.auth_html_login": (
            "HTTP {code} — resposta HTML de login em {url}. "
            "A sessão expirou. Faça login no navegador e reexporte os cookies."
        ),
        "ui.auth_http": "HTTP {code} (autenticação) em {url}",
        "ui.rate_limited": "HTTP 429 (rate limit) em {url}",
        "ui.http_error": "HTTP {code} em {url}: {body}",
        "ui.http_status": "HTTP {code} em {url}",
        "ui.hotmart_no_token": (
            "Hotmart: cookie 'hmVlcIntegration' não encontrado nos cookies carregados.\n"
            "O gateway do Hotmart autentica via 'Authorization: Bearer <hmVlcIntegration>' "
            "(não via cookies de sessão).\n"
            "Exporte o cookie hmVlcIntegration logado em consumer.hotmart.com "
            "(F12 > Application > Cookies > https://consumer.hotmart.com) e use --cookies.\n"
            "Exporte manualmente: o Chrome 127+ criptografa esse cookie "
            "(App-Bound Encryption) e a leitura direta do navegador pode retorná-lo vazio."
        ),
        "ui.hotmart_bad_url": (
            "URL Hotmart inválida. Informe a URL do produto: .../club/{{slug}}/products/{{id}}"
        ),
        "ui.astron_not_auth": "Sessão não autenticada. Verifique o cookie.",
        "ui.kiwify_no_token": (
            "Kiwify: token de autenticação não encontrado. Exporte o id_token/access_token "
            "(localStorage) ou use a extensão do Chrome."
        ),
        "ui.curseduca_unsupported": (
            "Curseduca ainda não totalmente suportado: a descoberta de aulas depende da API "
            "clas.curseduca.pro (menus/current + contents/{{id}}). Implementação pendente."
        ),
        "ui.video_label": "Vídeo",
        "ui.memberkit_rate": "HTTP 429 em {url}. Muitas requisições — o servidor pediu para reduzir o ritmo.",
        "ui.memberkit_auth": (
            "HTTP {code} em {url}. Sessão do Memberkit expirada — "
            "faça login no navegador e reexporte os cookies."
        ),

        # lib/streams.py
        "ui.stream_bunny": "Não encontrei playlist.m3u8 no embed Bunny {url}",
        "ui.stream_panda": "Não consegui extrair pullzone/video_id do PandaVideo {url}",
        "ui.stream_scaleup": "Não encontrei hls-prefetch-url no embed Scaleup {url}",
        "ui.stream_hotmart": "Não encontrei master.m3u8 no embed Hotmart {url}",
        "ui.stream_vimeo_url": "URL de embed Vimeo inválida {url}",
        "ui.stream_vimeo_config": (
            "Não encontrei config do player Vimeo no embed {url} — a aula pode ter sido "
            "removida ou estar restrita (a página do player não expôs a config)."
        ),
        "ui.stream_vimeo_config_http": "Requisição de config do Vimeo para {url} retornou HTTP {code}.",
        "ui.stream_vimeo_bad_json": (
            "A config do Vimeo para {url} não era JSON válido (resposta vazia/HTML, {n} bytes)."
        ),
        "ui.stream_vimeo_hls": "Config Vimeo sem playlists HLS no embed {url}",

        # lib/downloader.py
        "ui.dl_no_output": "yt-dlp não produziu arquivo de saída.",
        "ui.dl_ffmpeg_tags": "ffmpeg falhou ao gravar metadados: {err}",
        "ui.dl_ffmpeg_timeout": "ffmpeg estourou o tempo (>{seconds}s) ao gravar os metadados.",

        # lib/cookies.py
        "ui.cookies_invalid": (
            "Arquivo de cookies inválido para o yt-dlp: {path}\n"
            "Erro: {error}\n"
            "Primeira linha: {first}"
        ),
    },
}


__all__ = [
    "DEFAULT_LANG",
    "LANGUAGES",
    "PLURAL_FORM_COUNT",
    "decimal_sep",
    "init",
    "current_lang",
    "language_code",
    "nt",
    "t",
]