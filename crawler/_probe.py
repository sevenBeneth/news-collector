# -*- coding: utf-8 -*-
"""临时探测脚本：确认 4 类源的真实 HTML 结构（交付前删除）"""
import re
import requests
from bs4 import BeautifulSoup

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def get(url):
    r = requests.get(url, headers={"User-Agent": UA}, timeout=20)
    print("=" * 90)
    print("URL:", url)
    print("HTTP:", r.status_code, "| header charset:", r.encoding,
          "| apparent:", r.apparent_encoding, "| len:", len(r.content))
    m = re.search(rb'charset=["\']?([\w-]+)', r.content[:3000], re.I)
    print("meta charset:", m.group(1) if m else None)
    html = r.content.decode(r.apparent_encoding or "utf-8", errors="replace")
    soup = BeautifulSoup(html, "lxml")
    print("TITLE:", soup.title.get_text(strip=True) if soup.title else None)
    return r, soup, html


targets = [
    ("kjj_list", "https://kjj.wuhu.gov.cn/gg/tzgg/index.html"),
    ("gov_rss", "https://www.wuhu.gov.cn/rss/rss.xml?siteId=6787231"),
    ("gov_list", "https://www.wuhu.gov.cn/xwzx/zwyw/index.html"),
    ("wuhunews", "https://www.wuhunews.cn/yaowen/"),
]

for name, url in targets:
    try:
        r, soup, html = get(url)
        if name == "gov_rss":
            items = soup.find_all("item")[:3]
            print("item count:", len(soup.find_all("item")))
            for it in items:
                print("  ---")
                for tag in ("title", "link", "pubDate", "description"):
                    el = it.find(tag)
                    print("   ", tag, "=", (el.get_text(strip=True)[:120] if el else None))
        else:
            # 打印所有 a 标签里含 html 数字链接的
            links = [a for a in soup.find_all("a", href=True)
                     if re.search(r"/\d{6,}\.html", a["href"])]
            print("candidate links:", len(links))
            for a in links[:5]:
                print("  href=", a["href"])
                print("    title_attr=", a.get("title"))
                print("    text=", a.get_text(" ", strip=True)[:80])
                parent = a.find_parent(["li", "dd", "div", "tr"])
                if parent:
                    print("    parent_tag=", parent.name, "class=", parent.get("class"))
                    print("    parent_text=", parent.get_text(" ", strip=True)[:160])
        open("_probe_%s.html" % name, "w", encoding="utf-8").write(html)
    except Exception as exc:
        print("!! FAIL", name, type(exc).__name__, exc)
