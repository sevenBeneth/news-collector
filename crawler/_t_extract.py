# -*- coding: utf-8 -*-
"""临时测试：验证 extract.py 的编码 + 正文抽取 + 时间解析（交付前删除）"""
import io
import sys
import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from extract import (decode_response, extract_content, make_soup, normalize_time,
                     parse_publish_meta, pick_cover_image)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def check(label, url, sels):
    r = requests.get(url, headers={"User-Agent": UA}, timeout=20)
    print("=" * 88)
    print(label, url, "HTTP", r.status_code, "hdr:", r.encoding)
    html = decode_response(r)
    soup = make_soup(html)
    print("h1 =", soup.h1.get_text(strip=True) if soup.h1 else None)
    # 元信息
    meta_text = ""
    for tag in soup.find_all(["div", "span", "p"]):
        t = tag.get_text(" ", strip=True)
        if ("发布日期" in t or "发布时间" in t) and ("来源" in t or "信息来源" in t) and len(t) < 300:
            if not meta_text or len(t) < len(meta_text):
                meta_text = t
    print("meta_text =", meta_text[:200])
    print("parsed meta =", parse_publish_meta(meta_text))
    content, node = extract_content(html, sels)
    print("正文长度 =", len(content), "| 段落数 =", len([p for p in content.split("\n\n") if p]))
    print("前 300 字 =", content[:300].replace("\n", " / "))
    print("封面 =", pick_cover_image(soup, url, node))


check("kjj", "https://kjj.wuhu.gov.cn/gg/tzgg/8959644.html", ["div.newscontnet", "div.j-fontContent"])
check("gov", "https://www.wuhu.gov.cn/xwzx/zwyw/41350150.html",
      ["div.wzcon", "div.wenzhang .wzcon", "div.wenzhang"])
check("wuhunews", "https://www.wuhunews.cn/yaowen/2026-10-01/669171.html",
      ["div.article-content", "div.content"])

print("=" * 88)
print("时间归一化测试:")
for raw in ["2026-10-04 01:39:11.0", "2026-09-29 14:46", "10-04", "2026-09-29",
            "发布日期：2026-09-29 14:46 来源：芜湖市科技局 作者：芜湖市科技局", "12-31"]:
    print("  %-55s -> %s" % (raw, normalize_time(raw)))
