# -*- coding: utf-8 -*-
"""临时测试2：wuhunews/gov 详情页元信息位置 + 图片噪声排查"""
import io
import sys
import re
import requests
from bs4 import BeautifulSoup

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from extract import decode_response

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def fetch(url):
    r = requests.get(url, headers={"User-Agent": UA}, timeout=20)
    return decode_response(r)


print("########## wuhunews 详情：含时间/来源的节点 ##########")
html = fetch("https://www.wuhunews.cn/yaowen/2026-10-01/669171.html")
soup = BeautifulSoup(html, "lxml")
for tag in soup.find_all(["div", "span", "p", "small", "time", "em"]):
    t = tag.get_text(" ", strip=True)
    if re.search(r"来源|时间|发布|作者|编辑|2026-10", t) and len(t) < 200:
        cls = " ".join(tag.get("class") or [])
        print("  <%s class='%s' id='%s'> %s" % (tag.name, cls, tag.get("id"), t[:150]))
print("--- 页面里所有 img ---")
for img in soup.find_all("img")[:10]:
    print("  ", img.get("src"), "| class=", img.get("class"))
print("--- meta 标签 ---")
for m in soup.find_all("meta"):
    print("  ", m.attrs)

print()
print("########## kjj 详情：所有 img ##########")
html2 = fetch("https://kjj.wuhu.gov.cn/gg/tzgg/8959644.html")
soup2 = BeautifulSoup(html2, "lxml")
for img in soup2.find_all("img")[:15]:
    parent = img.find_parent(["div", "p", "li"])
    pcls = " ".join((parent.get("class") or [])) if parent else ""
    print("  src=%s | parent=<%s class='%s'>" % (img.get("src"), parent.name if parent else "-", pcls))
    if parent is not None:
        print("      parent_text=", parent.get_text(" ", strip=True)[:120])
print("--- kjj meta ---")
for m in soup2.find_all("meta"):
    if m.get("property") or m.get("name"):
        print("  ", m.attrs)

print()
print("########## wuhunews 列表项时间结构 ##########")
html3 = fetch("https://www.wuhunews.cn/yaowen/")
soup3 = BeautifulSoup(html3, "lxml")
for li in soup3.select("li")[:14]:
    a = li.find("a", href=True)
    if not a:
        continue
    print("  a.class=%s href=%s" % (a.get("class"), a["href"]))
    print("     li_text=", li.get_text(" ", strip=True)[:100])
