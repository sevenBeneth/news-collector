# -*- coding: utf-8 -*-
"""临时探测脚本 2：RSS 结构 + 列表/详情结构确认（输出写文件，避免控制台 GBK 干扰）"""
import io
import re
import sys
import requests
from bs4 import BeautifulSoup

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
OUT = open("_probe_out.txt", "w", encoding="utf-8")


def p(*a):
    print(*a)
    print(*a, file=OUT)


UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def get(url):
    r = requests.get(url, headers={"User-Agent": UA}, timeout=20)
    p("=" * 90)
    p("URL:", url, "| HTTP:", r.status_code, "| hdr:", r.encoding, "| apparent:", r.apparent_encoding)
    m = re.search(rb'charset=["\']?([\w-]+)', r.content[:4000], re.I)
    p("meta charset:", m.group(1) if m else None, "| len:", len(r.content))
    return r


# ---------- 1. RSS ----------
r = get("https://www.wuhu.gov.cn/rss/rss.xml?siteId=6787231")
raw = r.content.decode("utf-8", errors="replace")
p("---- RSS 前 1500 字符 ----")
p(raw[:1500])
p("---- RSS 用 lxml-xml 解析 ----")
soup = BeautifulSoup(raw, "lxml-xml")
items = soup.find_all("item")
p("items:", len(items))
for it in items[:3]:
    for tag in ("title", "link", "pubDate", "description", "author", "source"):
        el = it.find(tag)
        p("   ", tag, "=>", (el.get_text(strip=True)[:150] if el else None))
    p("    ---")

# ---------- 2. 科技局列表 ----------
r = get("https://kjj.wuhu.gov.cn/gg/tzgg/index.html")
soup = BeautifulSoup(r.content.decode("utf-8"), "lxml")
p("---- kjj 列表 li 结构 ----")
for li in soup.select("li")[:4]:
    a = li.find("a", href=True)
    if not a:
        continue
    p("  li.class=", li.get("class"), "| a.href=", a["href"], "| a.title=", a.get("title"))
    p("  li.text=", li.get_text(" ", strip=True)[:160])
    p("  li.html=", str(li)[:600])

# ---------- 3. 科技局详情 ----------
r = get("https://kjj.wuhu.gov.cn/gg/tzgg/8959644.html")
soup = BeautifulSoup(r.content.decode("utf-8"), "lxml")
p("---- kjj 详情 ----")
p("h1:", soup.h1.get_text(strip=True) if soup.h1 else None)
for tag in soup.find_all(["div", "span", "p"]):
    t = tag.get_text(" ", strip=True)
    if "发布日期" in t and len(t) < 300:
        p("  含发布日期节点:", tag.name, tag.get("class"), tag.get("id"), "=>", t[:250])
p("候选正文容器:")
for sel in ["div.content", "div#content", "div.article", "div.TRS_Editor",
            "div.zoom", "div.news_content", "div#zoom", "div.artical", "div.detail"]:
    el = soup.select_one(sel)
    if el:
        p("  HIT", sel, "len=", len(el.get_text(" ", strip=True)))
p("所有 class 含 content/artical/zoom/editor 的 div:")
seen = set()
for d in soup.find_all("div"):
    cls = " ".join(d.get("class") or [])
    if re.search(r"content|artical|article|zoom|editor|detail|txt|text", cls, re.I):
        key = (d.name, cls)
        if key in seen:
            continue
        seen.add(key)
        p("  div.class=", cls, "id=", d.get("id"),
          "textlen=", len(d.get_text(" ", strip=True)),
          "p_count=", len(d.find_all("p")),
          "sample=", d.get_text(" ", strip=True)[:100])

OUT.close()
