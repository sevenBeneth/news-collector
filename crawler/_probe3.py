# -*- coding: utf-8 -*-
"""临时探测脚本 3：列表 HTML / 详情容器 HTML 原样导出"""
import io
import sys
import re
import requests
from bs4 import BeautifulSoup

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
OUT = open("_probe_out3.txt", "w", encoding="utf-8")


def p(*a):
    print(*a, file=OUT)


UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def fetch(url):
    r = requests.get(url, headers={"User-Agent": UA}, timeout=20)
    html = r.content.decode("utf-8", errors="replace")
    p("#" * 100)
    p("URL:", url, "| HTTP:", r.status_code, "| hdr:", r.encoding)
    return html, BeautifulSoup(html, "lxml")


def dump_list(url, label):
    p("\n>>>>>>>>>> 列表 %s %s" % (label, url))
    html, soup = fetch(url)
    links = [a for a in soup.find_all("a", href=True) if re.search(r"/\d{6,}\.html", a["href"])]
    p("候选链接数:", len(links))
    for a in links[:3]:
        li = a.find_parent("li") or a.parent
        p("---- li/title 原文 ----")
        p(str(li)[:900])


def dump_detail(url, label, sels):
    p("\n>>>>>>>>>> 详情 %s %s" % (label, url))
    html, soup = fetch(url)
    p("h1:", soup.h1.get_text(strip=True) if soup.h1 else None)
    for sel in sels:
        el = soup.select_one(sel)
        if el:
            p("---- HIT %s | textlen=%d | p_count=%d ----" % (sel, len(el.get_text(" ", strip=True)), len(el.find_all("p"))))
            p(str(el)[:2600])
            break


# 1) 科技局列表
dump_list("https://kjj.wuhu.gov.cn/gg/tzgg/index.html", "kjj")
# 2) 科技局详情（正文容器原样）
dump_detail("https://kjj.wuhu.gov.cn/gg/tzgg/8959644.html", "kjj",
            ["div.newscontnet", "div.j-fontContent"])
# 3) 政府列表
dump_list("https://www.wuhu.gov.cn/xwzx/zwyw/index.html", "gov")
# 4) 政府详情
dump_detail("https://www.wuhu.gov.cn/xwzx/zwyw/41350150.html", "gov",
            ["div.newscontnet", "div#zoom", "div.zoom", "div.content", "div.article",
             "div.wenzhang", "div.j-fontContent", "div.TRS_Editor"])
# 5) 芜湖新闻网列表
dump_list("https://www.wuhunews.cn/yaowen/", "wuhunews")
# 6) 芜湖新闻网详情
dump_detail("https://www.wuhunews.cn/yaowen/2026-10-01/669171.html", "wuhunews",
            ["div.content", "div.article", "div.news_content", "div#content",
             "div.article-content", "div.text", "div.detail_content", "div.zw"])
# 7) 翻页
p("\n>>>>>>>>>> 翻页 pp=10")
html2, soup2 = fetch("https://www.wuhunews.cn/yaowen/?pp=10")
links2 = [a["href"] for a in soup2.find_all("a", href=True) if re.search(r"/\d{6,}\.html", a["href"])]
p("第二页链接数:", len(links2))
p(links2[:6])

OUT.close()
