import json, os, re, time, requests
from urllib.parse import urljoin, urlparse, urlunparse, parse_qsl, urlencode
from bs4 import BeautifulSoup

LIST_URL = (
    "https://www.fss.or.kr/fss/bbs/B0000188/list.do"
    "?menuNo=200218&bbsId=&cl1Cd=&pageIndex={page}"
    "&sdate=&edate=&searchCnd=1&searchWrd="
)
KEYWORDS = ["보험", "손해보험", "생명보험", "K-ICS", "지급여력"]
MAX_PAGES = int(os.environ.get("MAX_PAGES", "30"))
DATA_FILE = "data/press.json"
HEADERS = {"User-Agent": "Mozilla/5.0"}
DATE_RE = re.compile(r"(\d{2,4})[-./]\s*(\d{1,2})[-./]\s*(\d{1,2})")


def clean_link(url):
    """링크에서 pageIndex 파라미터를 제거해 같은 글은 항상 같은 링크가 되게 함"""
    p = urlparse(url)
    q = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
         if k != "pageIndex"]
    return urlunparse(p._replace(query=urlencode(q)))


def parse_date(text):
    m = DATE_RE.search(text)
    if not m:
        return ""
    y, mo, d = (int(x) for x in m.groups())
    if y < 100:
        y += 2000
    return f"{y:04d}-{mo:02d}-{d:02d}"


def fetch_page(page):
    url = LIST_URL.format(page=page)
    res = requests.get(url, headers=HEADERS, timeout=20)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")
    items = []
    for row in soup.select("table tbody tr"):
        a = row.select_one("a")
        if not a or not a.get("href"):
            continue
        items.append({
            "title": a.get_text(strip=True),
            "date": parse_date(row.get_text(" ", strip=True)),
            "link": clean_link(urljoin(url, a["href"])),
        })
    return items


def load_old():
    try:
        with open(DATA_FILE, encoding="utf-8") as f:
            old = json.load(f)
    except FileNotFoundError:
        return []
    for i in old:
        i["link"] = clean_link(i["link"])
    return old


def main():
    old = load_old()
    collected, prev_links = [], None

    for page in range(1, MAX_PAGES + 1):
        try:
            items = fetch_page(page)
        except Exception as e:
            if page == 1:
                raise   # 1페이지 실패는 Actions 실패로 처리
            print(f"{page}페이지 오류, 수집 중단: {e}")
            break
        if not items:
            print(f"{page}페이지에 글이 없어 종료")
            break
        links = [i["link"] for i in items]
        if links == prev_links:
            print(f"{page}페이지가 이전과 동일해 종료(페이지 파라미터 확인 필요)")
            break
        prev_links = links
        print(f"{page}페이지: {len(items)}건, 첫 글: {items[0]['date']} {items[0]['title'][:30]}")
        collected += items
        time.sleep(1.5)

    filtered = [i for i in collected if any(k in i["title"] for k in KEYWORDS)]
    merged = {i["link"]: i for i in old + filtered}
    result = sorted(merged.values(), key=lambda x: x["date"], reverse=True)

    os.makedirs("data", exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"읽은 글 {len(collected)}건 / 키워드 일치 {len(filtered)}건 / 저장 전체 {len(result)}건")


if __name__ == "__main__":
    main()
