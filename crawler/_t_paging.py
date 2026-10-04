# -*- coding: utf-8 -*-
"""临时脚本：验证 kjj/gov 列表页分页地址是否真的 404（交付前删除）"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from adapters import HttpClient

client = HttpClient(min_delay=0.2, max_delay=0.4)
urls = [
    "https://kjj.wuhu.gov.cn/gg/tzgg/index_1.html",
    "https://kjj.wuhu.gov.cn/gg/tzgg/index_2.html",
    "https://www.wuhu.gov.cn/xwzx/zwyw/index_1.html",
    "https://www.wuhu.gov.cn/xwzx/zwyw/index_2.html",
    # 政府站常见的另一种分页写法
    "https://www.wuhu.gov.cn/xwzx/zwyw/index_1.shtml",
    "https://kjj.wuhu.gov.cn/gg/tzgg/index_1.shtml",
]
for url in urls:
    try:
        response = client.session.get(url, timeout=20)
        client._last_request_at = 0
        body = response.content[:200].decode("utf-8", "replace").replace("\n", " ")
        print("%-58s -> HTTP %s | len=%d | %s" % (url, response.status_code, len(response.content), body[:80]))
    except Exception as exc:
        print("%-58s -> FAIL %s" % (url, exc))
