# -*- coding: utf-8 -*-
"""
config.py —— 全局配置

改这里就能调整：后端地址、采集令牌、UA、超时、限速、重试次数。
所有可调项都支持用环境变量覆盖，方便在不同机器/答辩现场切换。
部署或演示时不需要改代码，只要设环境变量即可。
"""

from __future__ import annotations

import os

# --------------------------------------------------------------------------
# 一、后端接口
# --------------------------------------------------------------------------

# 后端服务地址（Spring Boot，端口 9533，无上下文前缀）
BACKEND_BASE_URL = os.getenv("WUHU_BACKEND", "http://127.0.0.1:9533").rstrip("/")

# 采集端鉴权令牌，对应 docs/api.md 的 Header: X-Ingest-Token
INGEST_TOKEN = os.getenv("WUHU_INGEST_TOKEN", "wuhu-ingest-2026")
INGEST_HEADER = "X-Ingest-Token"

# 各接口路径（集中管理，避免散落在业务代码里）
API_SOURCES = "/api/ingest/sources"          # GET  采集源列表
API_NEWS = "/api/ingest/news"                # POST 批量入库
API_LOG = "/api/ingest/log"                  # POST 采集日志
API_TOUCH = "/api/ingest/source/{id}/touch"  # POST 更新 last_crawl_time

# 单次批量推送的最大条数。后端是 Java 服务，一次塞太多容易超时，
# 所以推送时按 30 条一批切片。
BATCH_SIZE = int(os.getenv("WUHU_BATCH_SIZE", "30"))

# 后端请求超时（秒）。批量入库比拉列表慢，单独给一个更宽松的值。
API_TIMEOUT = float(os.getenv("WUHU_API_TIMEOUT", "30"))


# --------------------------------------------------------------------------
# 二、抓取行为
# --------------------------------------------------------------------------

# 固定 Chrome UA：这些站点对空 UA / 脚本 UA 不友好
USER_AGENT = os.getenv(
    "WUHU_UA",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
)

# 每次请求的额外请求头，模拟浏览器访问
DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
}

# 单次请求超时（秒）
REQUEST_TIMEOUT = float(os.getenv("WUHU_TIMEOUT", "20"))

# 礼貌限速：每次 HTTP 请求之间的随机间隔（秒），单线程顺序抓取
DELAY_MIN = float(os.getenv("WUHU_DELAY_MIN", "0.8"))
DELAY_MAX = float(os.getenv("WUHU_DELAY_MAX", "1.8"))

# 失败重试
RETRY_TIMES = int(os.getenv("WUHU_RETRY", "3"))       # 总尝试次数
RETRY_BACKOFF = 1.5                                    # 指数退避基数：1.5s, 3s, 6s...

# 单个源最多抓取的列表页数（会被源的 max_pages 或 --max-pages 覆盖）
DEFAULT_MAX_PAGES = int(os.getenv("WUHU_MAX_PAGES", "1"))

# 正文长度低于这个值视为抽取失败，改用列表摘要兜底
MIN_CONTENT_LENGTH = 80


# --------------------------------------------------------------------------
# 三、目录
# --------------------------------------------------------------------------

# 以本文件所在目录为基准，保证在任何工作目录下执行都能找到日志目录
CRAWLER_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(CRAWLER_DIR, "logs")


# --------------------------------------------------------------------------
# 四、后端不可用时的离线兜底源（让 --dry-run 在没启动后端时也能跑）
# --------------------------------------------------------------------------
# 正常流程下源列表来自 GET /api/ingest/sources；这里只是"后端未启动"时的
# 应急名单，id 与 sql/init.sql 里的采集源保持一致。
FALLBACK_SOURCES = [
    {
        "id": 1, "name": "芜湖市科技局-通知公告", "adapter": "wuhu_kjj_list",
        "list_url": "https://kjj.wuhu.gov.cn/gg/tzgg/index.html",
        "default_category_code": "notice", "keyword_filter": "科技,创新,科创,研发,高新技术",
        "max_pages": 1,
    },
    {
        "id": 2, "name": "芜湖市科技局-工作动态", "adapter": "wuhu_kjj_list",
        "list_url": "https://kjj.wuhu.gov.cn/gg/gzdt/index.html",
        "default_category_code": "news", "keyword_filter": "科技,创新,科创,研发,高新技术",
        "max_pages": 1,
    },
    {
        "id": 3, "name": "芜湖市科技局-科技要闻", "adapter": "wuhu_kjj_list",
        "list_url": "https://kjj.wuhu.gov.cn/gg/kjyw/index.html",
        "default_category_code": "news", "keyword_filter": "科技,创新,科创,研发,高新技术",
        "max_pages": 1,
    },
    {
        "id": 4, "name": "芜湖市科技局-县区科技", "adapter": "wuhu_kjj_list",
        "list_url": "https://kjj.wuhu.gov.cn/gg/xqkj/index.html",
        "default_category_code": "news", "keyword_filter": "科技,创新,科创,研发,高新技术",
        "max_pages": 1,
    },
    {
        "id": 5, "name": "芜湖市人民政府-RSS", "adapter": "wuhu_gov_rss",
        "list_url": "https://www.wuhu.gov.cn/rss/rss.xml?siteId=6787231",
        "default_category_code": "news", "keyword_filter": "科技,创新,科创,研发,数字经济,智算",
        "max_pages": 1,
    },
    {
        "id": 6, "name": "芜湖市政府-政务要闻", "adapter": "wuhu_gov_list",
        "list_url": "https://www.wuhu.gov.cn/xwzx/zwyw/index.html",
        "default_category_code": "news", "keyword_filter": "科技,创新,科创,研发,数字经济,智算",
        "max_pages": 1,
    },
    {
        "id": 7, "name": "芜湖市政府-部门动态", "adapter": "wuhu_gov_list",
        "list_url": "https://www.wuhu.gov.cn/xwzx/bmdt/index.html",
        "default_category_code": "news", "keyword_filter": "科技,创新,科创,研发,数字经济,智算",
        "max_pages": 1,
    },
    {
        "id": 8, "name": "芜湖新闻网-要闻", "adapter": "wuhunews_list",
        "list_url": "https://www.wuhunews.cn/yaowen/",
        "default_category_code": "news", "keyword_filter": "科技,创新,科创,研发,智算,数字经济",
        "max_pages": 2,
    },
    {
        "id": 9, "name": "芜湖新闻网-党建中心", "adapter": "wuhunews_list",
        "list_url": "https://www.wuhunews.cn/djzx/",
        "default_category_code": "news", "keyword_filter": "科技,创新,科创,研发,智算,数字经济",
        "max_pages": 1,
    },
]
