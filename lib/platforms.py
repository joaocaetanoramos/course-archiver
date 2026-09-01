import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup


def get_json(session, url, headers=None, timeout=20):
    resp = session.get(url, headers=headers, timeout=timeout)
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code} em {url}: {resp.text[:200]}")
    return resp.json()


class Platform:
    name = "generic"

    def detect(self, url) -> bool:
        return False

    def discover(self, url, session):
        raise NotImplementedError

    def list_lessons(self, course, session):
        raise NotImplementedError

    def extract_video(self, lesson, session):
        raise NotImplementedError


class GenericPlatform(Platform):
    name = "generic"

    def discover(self, url, session):
        return [{"platform": self.name, "id": url, "title": "", "group": "", "url": url}]

    def list_lessons(self, course, session):
        name = urlparse(course["url"]).path.rstrip("/").rsplit("/", 1)[-1] or "Vídeo"
        return [{"id": course["url"], "title": name, "url": course["url"], "group": "", "chapter": ""}]

    def extract_video(self, lesson, session):
        return lesson["url"]


class AstronPlatform(Platform):
    name = "astron"

    def detect(self, url):
        return "astronmembers.com" in urlparse(url).netloc

    def _base(self, url):
        p = urlparse(url)
        return f"{p.scheme}://{p.netloc}"

    def discover(self, url, session):
        base = self._base(url)
        html = session.get(base + "/dashboard", timeout=20).text
        if "IS_LOGGED_IN = true" not in html:
            raise SystemExit("Sessão não autenticada. Verifique o cookie.")
        soup = BeautifulSoup(html, "html.parser")

        courses = []
        seen = set()
        for group in soup.select('[id^="dashGrupo_"]'):
            h5 = group.select_one("h5")
            group_title = h5.get_text(strip=True) if h5 else ""
            for a in group.select('a[href^="curso/"]'):
                href = str(a.get("href", ""))
                m = re.match(r"curso/([^/]+)/(\d+)", href)
                if not m:
                    continue
                slug, course_id = m.group(1), m.group(2)
                if course_id in seen:
                    continue
                seen.add(course_id)
                courses.append({
                    "platform": self.name,
                    "group": group_title,
                    "slug": slug,
                    "course_id": course_id,
                    "title": slug,
                    "url": f"{base}/curso/{slug}/{course_id}",
                })

        m = re.search(r"/curso/([^/]+)/(\d+)(?:/(\d+))?", urlparse(url).path)
        if m:
            slug, course_id, lesson_id = m.group(1), m.group(2), m.group(3)
            chosen = [c for c in courses if c["course_id"] == course_id or c["slug"] == slug]
            if not chosen:
                chosen = [{
                    "platform": self.name,
                    "group": "",
                    "slug": slug,
                    "course_id": course_id,
                    "title": slug,
                    "url": f"{base}/curso/{slug}/{course_id}",
                }]
            courses = chosen
            if lesson_id:
                for c in courses:
                    c["only_lesson"] = lesson_id

        return courses

    def list_lessons(self, course, session):
        html = session.get(course["url"], timeout=20).text
        soup = BeautifulSoup(html, "html.parser")
        h2 = soup.select_one(".modulo-head h2")
        course_title = h2.get_text(strip=True) if h2 else course["title"]

        lessons = []
        seen = set()
        pattern = re.compile(rf"^curso/{re.escape(course['slug'])}/{course['course_id']}/(\d+)$")
        for a in soup.find_all("a", href=True):
            href = str(a.get("href", "")).strip()
            m = pattern.match(href)
            if not m:
                continue
            lesson_id = m.group(1)
            if lesson_id in seen:
                continue
            if course.get("only_lesson") and lesson_id != course["only_lesson"]:
                continue
            seen.add(lesson_id)
            h6 = a.select_one("h6")
            title = h6.get_text(strip=True) if h6 else lesson_id
            lessons.append({
                "id": lesson_id,
                "title": title,
                "url": f"{course['url']}/{lesson_id}",
                "group": course["group"],
                "chapter": course_title,
            })
        return lessons

    def extract_video(self, lesson, session):
        html = session.get(lesson["url"], timeout=20).text
        m = re.search(r'data-streaming-video="([^"]+)"', html)
        if not m:
            m = re.search(r'data-original-url="(https?://[^"]+)"', html)
        return m.group(1) if m else None


class HotmartPlatform(Platform):
    name = "hotmart"
    GATEWAY = "https://api-club-course-consumption-gateway-ga.cb.hotmart.com"

    def detect(self, url):
        return "hotmart.com" in urlparse(url).netloc

    def _headers(self, slug, product_id):
        return {
            "slug": slug,
            "x-product-id": product_id,
            "x-app-name": "@hotmart/app-club-consumer_v1.364.2",
            "x-hot-club-http": "APP_CLUB_CONSUMER_API_COURSE_CONSUMPTION_GATEWAY_INSTANCE",
            "accept": "application/json",
            "origin": "https://hotmart.com",
            "referer": "https://hotmart.com/",
        }

    def _parse_url(self, url):
        path = urlparse(url).path
        slug = re.search(r"/club/([^/]+)", path)
        product_id = re.search(r"/products/(\d+)", path)
        content_hash = re.search(r"/content/([a-zA-Z0-9]+)", path)
        return (
            slug.group(1) if slug else None,
            product_id.group(1) if product_id else None,
            content_hash.group(1) if content_hash else None,
        )

    def discover(self, url, session):
        slug, product_id, content_hash = self._parse_url(url)
        if not slug or not product_id:
            raise SystemExit("URL Hotmart inválida. Informe a URL do produto: .../club/{slug}/products/{id}")
        headers = self._headers(slug, product_id)
        data = get_json(session, f"{self.GATEWAY}/v2/product/basic", headers=headers)
        name = data.get("name") or slug
        return [{
            "platform": self.name,
            "id": product_id,
            "title": name,
            "group": "",
            "slug": slug,
            "product_id": product_id,
            "url": url,
            "_content_hash": content_hash,
        }]

    def list_lessons(self, course, session):
        headers = self._headers(course["slug"], course["product_id"])
        data = get_json(session, f"{self.GATEWAY}/v1/navigation", headers=headers)
        lessons = []
        for module in data.get("modules", []):
            module_name = module.get("name") or ""
            for page in module.get("pages", []):
                if page.get("type") != "CONTENT":
                    continue
                lessons.append({
                    "id": page.get("hash"),
                    "title": page.get("name"),
                    "url": f"https://consumer.hotmart.com/pt-br/club/{course['slug']}/products/{course['product_id']}/content/{page.get('hash')}",
                    "group": course["group"],
                    "chapter": module_name,
                    "_hash": page.get("hash"),
                    "_slug": course["slug"],
                    "_product_id": course["product_id"],
                })
        if course.get("_content_hash"):
            lessons = [l for l in lessons if l["_hash"] == course["_content_hash"]]
        return lessons

    def extract_video(self, lesson, session):
        headers = self._headers(lesson["_slug"], lesson["_product_id"])
        data = get_json(session, f"{self.GATEWAY}/v2/web/lessons/{lesson['_hash']}", headers=headers)
        for media in data.get("medias", []):
            if media.get("type") == "VIDEO" and media.get("url"):
                return media["url"]
        return None


class KiwifyPlatform(Platform):
    name = "kiwify"
    API = "https://admin-api.kiwify.com.br"

    def detect(self, url):
        return "kiwify.com" in urlparse(url).netloc

    def _token(self, session):
        for name in ("id_token", "access_token"):
            cookie = session.cookies.get(name)
            if cookie:
                return cookie
        refresh = session.cookies.get("refresh_token")
        if refresh:
            resp = session.post(
                f"{self.API}/v1/handleAuth/getIdToken",
                json={"grant_type": "refresh_token", "refresh_token": refresh},
                timeout=20,
            )
            data = resp.json()
            return data.get("id_token") or data.get("access_token")
        return None

    def _headers(self, session):
        token = self._token(session)
        if not token:
            raise SystemExit(
                "Kiwify: token de autenticação não encontrado. Exporte o id_token/access_token "
                "(localStorage) ou use a extensão do Chrome."
            )
        return {
            "Authorization": f"Bearer {token}",
            "accept": "application/json",
            "origin": "https://dashboard.kiwify.com",
        }

    def discover(self, url, session):
        m = re.search(r"course_premium/([a-z0-9-]+)", urlparse(url).path)
        if not m:
            m = re.search(r"/course/premium/([a-z0-9-]+)", urlparse(url).path)
        if not m:
            headers = self._headers(session)
            data = get_json(session, f"{self.API}/v1/viewer/schools/courses?page=1&archived=false", headers=headers)
            courses = []
            for item in data.get("courses", data.get("data", [])):
                cid = item.get("id") or item.get("course_id")
                courses.append({
                    "platform": self.name,
                    "id": cid,
                    "title": item.get("name") or item.get("title") or cid,
                    "group": "",
                    "url": f"https://dashboard.kiwify.com/course_premium/{cid}",
                    "_course_id": cid,
                })
            return courses
        cid = m.group(1)
        return [{
            "platform": self.name,
            "id": cid,
            "title": cid,
            "group": "",
            "url": url,
            "_course_id": cid,
        }]

    def list_lessons(self, course, session):
        headers = self._headers(session)
        cid = course["_course_id"]
        data = get_json(session, f"{self.API}/v1/viewer/courses/{cid}/sections", headers=headers)
        sections = (data.get("course") or {}).get("sections") or []
        lessons = []
        for section in sections:
            section_name = section.get("name") or ""
            for module in section.get("modules", []):
                module_name = module.get("name") or section_name
                for lesson in module.get("lessons", []):
                    lessons.append({
                        "id": lesson.get("id"),
                        "title": lesson.get("title") or lesson.get("id"),
                        "url": f"https://dashboard.kiwify.com/course_premium/{cid}",
                        "group": course["group"],
                        "chapter": module_name,
                        "_course_id": cid,
                    })
        return lessons

    def extract_video(self, lesson, session):
        headers = self._headers(session)
        cid = lesson["_course_id"]
        data = get_json(session, f"{self.API}/v1/viewer/courses/{cid}/lesson/{lesson['id']}", headers=headers)
        video = (data.get("lesson") or {}).get("video") or {}
        return video.get("download_link") or video.get("stream_link")


class CurseducaPlatform(Platform):
    name = "curseduca"
    API = "https://clas.curseduca.pro"

    def detect(self, url):
        host = urlparse(url).netloc
        return "curseduca.pro" in host or "curseduca.com" in host

    def discover(self, url, session):
        raise SystemExit(
            "Curseduca ainda não totalmente suportado: a descoberta de aulas depende da API "
            "clas.curseduca.pro (menus/current + contents/{id}). Implementação pendente."
        )

    def list_lessons(self, course, session):
        raise NotImplementedError

    def extract_video(self, lesson, session):
        raise NotImplementedError


PLATFORMS = [AstronPlatform(), HotmartPlatform(), KiwifyPlatform(), CurseducaPlatform()]


def detect_platform(url):
    for p in PLATFORMS:
        if p.detect(url):
            return p
    return GenericPlatform()
