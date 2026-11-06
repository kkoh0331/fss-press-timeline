import json, requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup

URL = "https://www.fss.or.kr/fss/bbs/B0000188/list.do?menuNo=200218"
KEYWORDS = ["보험", "손해보험", "생명보험", "K-ICS", "지급여력"]

def fetch():
    res = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")
    items = []
    for row in soup.select("table tbody tr"):   # 실제 구조에 맞게 수정
        a = row.select_one("a")
        if not a:
            continue
        items.append({
            "title": a.get_text(strip=True),
            "date": row.select("td")[-1].get_text(strip=True),  # 수정 필요
            "link": urljoin(URL, a["href"]),
        })
    return [i for i in items if any(k in i["title"] for k in KEYWORDS)]

if __name__ == "__main__":
    new = fetch()
    try:
        old = json.load(open("data/press.json", encoding="utf-8"))
    except FileNotFoundError:
        old = []
        for i in old:
            i["link"] = urljoin(URL, i["link"])
    merged = {i["link"]: i for i in old + new}.values()
    merged = sorted(merged, key=lambda x: x["date"], reverse=True)
    json.dump(list(merged), open("data/press.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
