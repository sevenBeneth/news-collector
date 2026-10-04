# -*- coding: utf-8 -*-
"""临时脚本：列日期与解析结果对照（交付前删除）"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from adapters import HttpClient, create_adapter

client = HttpClient(min_delay=0.3, max_delay=0.5)

cases = [
    ("kjj_xqkj", {"adapter": "wuhu_kjj_list", "list_url": "https://kjj.wuhu.gov.cn/gg/xqkj/index.html"}),
    ("kjj_gzdt", {"adapter": "wuhu_kjj_list", "list_url": "https://kjj.wuhu.gov.cn/gg/gzdt/index.html"}),
    ("gov_zwyw", {"adapter": "wuhu_gov_list", "list_url": "https://www.wuhu.gov.cn/xwzx/zwyw/index.html"}),
    ("wuhunews_p2", {"adapter": "wuhunews_list", "list_url": "https://www.wuhunews.cn/yaowen/"}),
    ("wuhunews_djzx", {"adapter": "wuhunews_list", "list_url": "https://www.wuhunews.cn/djzx/"}),
]

for label, source in cases:
    print("=" * 100)
    print(label, source["list_url"])
    adapter = create_adapter(source, client)
    pages = adapter.list_page_urls(2)
    for page_index, page_url in enumerate(pages):
        try:
            html, _ = client.get_html(page_url, is_xml=(source["adapter"] == "wuhu_gov_rss"))
        except Exception as exc:
            print("  !! 抓取失败", page_url, exc)
            continue
        items = adapter.parse_list(html, page_url)
        print("  第%d页 %s -> %d 条" % (page_index + 1, page_url, len(items)))
        for item in items:
            print("     %-19s | %s" % (item.publish_time or "无时间", item.title[:52]))
