# -*- coding: utf-8 -*-
"""
adapters.py —— 四类采集源的列表解析 + 详情解析

每种适配器负责两件事：
    parse_list(html, page_url) -> [ListItem]       解析列表页，拿到条目骨架
    parse_detail(html, url)    -> dict             解析详情页，补全正文/来源/时间/封面

四类源（2026-10 实测确认）：
    1. wuhu_kjj_list   芜湖市科技局列表页（服务端直出 HTML，分页是 JS 渲染，只抓第 1 页）
    2. wuhu_gov_rss    芜湖市政府 RSS 2.0（description 自带摘要，可作正文兜底）
    3. wuhu_gov_list   芜湖市政府新闻中心列表（列表日期只有 "10-04"，需补年份）
    4. wuhunews_list   芜湖新闻网列表（支持 ?pp=N 翻页，每页 10 条）
"""

from __future__ import annotations

import random
import re
import time
from dataclasses import dataclass
from urllib.parse import urlparse, urlunparse

import requests
from bs4 import BeautifulSoup, Tag
from tenacity import (RetryError, retry, retry_if_exception_type,
                      stop_after_attempt, wait_exponential)

import config
from extract import (clean_content, clean_text, decode_response, extract_content,
                     make_soup, normalize_image, normalize_time, normalize_url,
                     parse_publish_meta, pick_cover_image, same_section,
                     strip_html_fragment)


# ==========================================================================
# 一、数据结构
# ==========================================================================

@dataclass
class ListItem:
    """列表页解析出来的条目骨架（正文还没抓）。"""
    title: str = ""
    source_url: str = ""
    publish_time: str = ""      # 已归一化为 YYYY-MM-DD HH:MM:SS
    summary: str = ""           # 列表页/RSS 自带的摘要，正文抽取失败时兜底
    photo_url: str = ""         # 列表页缩略图（可选）
    origin: str = ""            # 列表页能看出来源时填


@dataclass
class NewsItem:
    """一条完整的待推送新闻，字段与 POST /api/ingest/news 契约一一对应。"""
    title: str
    source_url: str
    content: str
    photo_url: str = ""
    origin: str = ""
    publish_time: str = ""
    category_code: str = ""

    def to_payload(self) -> dict:
        """转成后端要求的 JSON 结构（字段名严格按 docs/api.md）。"""
        return {
            "title": self.title,
            "source_url": self.source_url,
            "content": self.content,
            "photo_url": self.photo_url,
            "origin": self.origin,
            "publish_time": self.publish_time,
            "category_code": self.category_code,
        }


# ==========================================================================
# 二、HTTP 客户端（限速 + 重试 + 编码处理）
# ==========================================================================

class FetchError(Exception):
    """网络层最终失败（重试耗尽）。"""


class HttpClient:
    """单线程、带礼貌间隔与指数退避重试的抓取客户端。

    - 固定 Chrome UA；
    - 每次请求之间随机 sleep DELAY_MIN~DELAY_MAX 秒（限速，避免给政府站点压力）；
    - 超时 REQUEST_TIMEOUT 秒；
    - 失败重试 RETRY_TIMES 次，指数退避；
    - 只发 GET，不抓附件 PDF。
    """

    def __init__(self, session: requests.Session | None = None, min_delay: float | None = None,
                 max_delay: float | None = None, timeout: float | None = None):
        self.session = session or requests.Session()
        self.session.headers.update(config.DEFAULT_HEADERS)
        self.min_delay = config.DELAY_MIN if min_delay is None else min_delay
        self.max_delay = config.DELAY_MAX if max_delay is None else max_delay
        self.timeout = config.REQUEST_TIMEOUT if timeout is None else timeout
        self._last_request_at = 0.0
        self.request_count = 0

    # ---- 内部工具 ----

    def _polite_wait(self) -> None:
        """确保两次请求之间有随机间隔。"""
        if self.min_delay <= 0 and self.max_delay <= 0:
            return
        gap = random.uniform(self.min_delay, max(self.min_delay, self.max_delay))
        elapsed = time.monotonic() - self._last_request_at
        if self._last_request_at > 0 and elapsed < gap:
            time.sleep(gap - elapsed)

    def _get_with_retry(self, url: str) -> requests.Response:
        """带指数退避重试的 GET；重试次数与退避基数来自 config。"""

        @retry(
            stop=stop_after_attempt(max(1, config.RETRY_TIMES)),
            wait=wait_exponential(multiplier=config.RETRY_BACKOFF, min=1, max=30),
            retry=retry_if_exception_type((requests.RequestException, FetchError)),
            reraise=True,
        )
        def _do_request() -> requests.Response:
            self._polite_wait()
            try:
                response = self.session.get(url, timeout=self.timeout)
            finally:
                self._last_request_at = time.monotonic()
                self.request_count += 1
            # 5xx / 429 当作可重试错误
            if response.status_code >= 500 or response.status_code == 429:
                raise FetchError("HTTP %s" % response.status_code)
            return response

        try:
            return _do_request()
        except RetryError as exc:                      # pragma: no cover - 兜底
            raise FetchError("重试耗尽: %s" % exc) from exc

    # ---- 对外接口 ----

    def get_html(self, url: str, is_xml: bool = False) -> tuple[str, Tag]:
        """抓一页并解码，返回 (HTML 文本, BeautifulSoup)。

        编码判定统一交给 extract.decode_response，这里不做任何默认解码，
        否则政府站点（HTTP 头谎报 ISO-8859-1）会直接变成乱码。
        """
        response = self._get_with_retry(url)
        if response.status_code >= 400:
            raise FetchError("HTTP %s: %s" % (response.status_code, url))
        html = decode_response(response)
        return html, make_soup(html, is_xml=is_xml)

    def get_soup(self, url: str, is_xml: bool = False) -> BeautifulSoup:
        """只关心解析结果时的便捷方法。"""
        return self.get_html(url, is_xml=is_xml)[1]


# ==========================================================================
# 三、详情页通用解析工具
# ==========================================================================

# 详情页里"发布时间"这类字段的标签写法
_TIME_LABEL_RE = re.compile(r"发布日期|发布时间|发布于|时间\s*[:：]")
_SOURCE_LABEL_RE = re.compile(r"信息来源|来源|稿源|发布机构")
# 只有时间的短文本（如 wuhunews 详情页的 <time>2026-10-01 02:03</time>）
_PLAIN_TIME_RE = re.compile(r"^\s*\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?(\s+\d{1,2}:\d{2}(:\d{2})?)?\s*$")


def meta_from_meta_tags(soup: BeautifulSoup) -> dict:
    """从 <meta> 里取标准的发布元信息。

    芜湖市科技局的页面把 ArticleTitle / PubDate / ContentSource / Author
    都写进了 meta，是最可靠的来源，优先使用。
    """
    result = {"title": "", "publish_time": "", "origin": "", "author": ""}
    mapping = {
        "pubdate": "publish_time", "publishdate": "publish_time", "pub_date": "publish_time",
        "contentsource": "origin", "source": "origin", "articleauthor": "author",
        "author": "author", "articletitle": "title", "og:title": "title",
    }
    for meta in soup.find_all("meta"):
        key = (meta.get("name") or meta.get("property") or "").strip().lower()
        if key not in mapping:
            continue
        value = clean_text(meta.get("content") or "")
        if not value:
            continue
        target = mapping[key]
        if target == "publish_time":
            value = normalize_time(value) or value
        if not result.get(target):
            result[target] = value
    return result


def meta_from_page_text(soup: BeautifulSoup, limit: int = 6) -> dict:
    """在页面里扫描"含发布信息的短文本块"，解析出时间/来源/作者。

    思路：取同时带"发布日期/发布时间"标签、且文本足够短的前几个节点，
    合并后再用正则抽字段。这样不依赖具体站点的 class 名。
    """
    candidates: list[str] = []
    seen: set[str] = set()
    for tag in soup.find_all(["div", "span", "p", "li", "td", "em", "small", "time"]):
        text = tag.get_text(" ", strip=True)
        if not text or len(text) > 500:
            continue
        if not (_TIME_LABEL_RE.search(text) or _PLAIN_TIME_RE.match(text)):
            continue
        if text in seen:
            continue
        seen.add(text)
        candidates.append(text)
        if len(candidates) >= limit:
            break

    merged = " ".join(candidates)
    result = parse_publish_meta(merged)
    if not result["publish_time"]:
        # 没有"发布日期："这种标签时，抓页面里的第一个裸日期
        for text in candidates:
            stamp = normalize_time(text)
            if stamp:
                result["publish_time"] = stamp
                break
    result["_raw"] = merged[:300]
    return result


def parse_detail_page(html: str, page_url: str, content_selectors: list[str] | None = None,
                      default_origin: str = "", fallback_time: str = "",
                      fallback_summary: str = "") -> dict:
    """详情页通用解析：标题、正文、来源、时间、封面。

    这是四个适配器共用的主干逻辑，各适配器只需要给出自己的正文选择器，
    以及"来源/时间取不到时的默认值"。
    """
    soup = make_soup(html)

    # --- 标题：优先 meta，其次 h1，最后 <title> 去站点后缀 ---
    meta = meta_from_meta_tags(soup)
    title = meta.get("title", "")
    if not title and soup.h1 is not None:
        title = clean_text(soup.h1.get_text(" ", strip=True))
    if not title and soup.title is not None:
        title = clean_text(re.split(r"[_|\-—]", soup.title.get_text(strip=True))[0])

    # --- 正文 ---
    content, content_node = extract_content(html, content_selectors)

    # --- 发布信息：meta → 页面文本块 → 列表页兜底 ---
    page_meta = meta_from_page_text(soup)
    publish_time = meta.get("publish_time") or page_meta.get("publish_time") or fallback_time
    origin = meta.get("origin") or page_meta.get("origin") or default_origin

    # --- 封面图 ---
    photo_url = pick_cover_image(soup, page_url, content_node)

    # --- 正文太短则用摘要兜底 ---
    final_content = content
    if len(content) < config.MIN_CONTENT_LENGTH and fallback_summary:
        final_content = clean_content(fallback_summary)

    return {
        "title": title,
        "content": final_content,
        "raw_content_length": len(content),
        "photo_url": photo_url,
        "origin": origin,
        "publish_time": publish_time,
        "meta": meta,
        "page_meta": page_meta,
    }


def is_probably_non_chinese(title: str) -> bool:
    """判断标题是否是外文稿件（RSS 里混有英文版新闻，课程项目只收中文）。"""
    if not title:
        return True
    chinese = len(re.findall(r"[\u4e00-\u9fa5]", title))
    return chinese < max(2, len(title) * 0.15)


# ==========================================================================
# 四、适配器 1：芜湖市科技局列表页
# ==========================================================================

KJJ_CONTENT_SELECTORS = [
    "div.newscontnet",           # 实测正文容器
    "div.j-fontContent",
    "div.article-content",
    "div#zoom",
    "div.zoom",
    "div.article",
    "div.content",
]

# 列表页里明显不是新闻的固定链接
_KJJ_SKIP_TITLE_RE = re.compile(r"^(网站地图|联系我们|加入收藏|设为首页|无障碍|长辈版)$")


class WuhuKjjListAdapter:
    """芜湖市科技局列表页适配器。

    列表页特征（实测 kjj.wuhu.gov.cn/gg/tzgg/index.html）：
        <li class="odd">
          <a class="left" href="https://kjj.wuhu.gov.cn/gg/tzgg/8959644.html"
             title="关于转发……的通知"><span>……</span></a>
          <span class="right date">2026-09-29</span>
        </li>
    注意：分页由 JS 渲染，index_1.html 返回 404，因此 max_pages 对该适配器无效，只抓第 1 页。
    """

    name = "wuhu_kjj_list"
    # 分页是否有效：False 表示无论如何只抓第 1 页
    supports_paging = False

    def __init__(self, source: dict, client: HttpClient):
        self.source = source
        self.client = client
        self.list_url = source.get("list_url", "")
        self.default_origin = "芜湖市科技局"

    # ---- 列表 ----

    def list_page_urls(self, max_pages: int) -> list[str]:
        """科技局分页是 JS 渲染的（index_1.html → 404），所以永远只返回第 1 页。"""
        return [self.list_url] if self.list_url else []

    def parse_list(self, html: str, page_url: str) -> list[ListItem]:
        soup = make_soup(html)
        items: list[ListItem] = []
        for link in soup.find_all("a", href=True):
            href = link.get("href") or ""
            if not re.search(r"/\d{6,}\.html$", href.split("?")[0]):
                continue
            url = normalize_url(href, page_url)
            if not url or not same_section(url, self.list_url):
                continue
            # 标题：优先 title 属性（不受内部 span 影响），其次 a 的文本
            title = clean_text(link.get("title") or link.get_text(" ", strip=True))
            if not title or _KJJ_SKIP_TITLE_RE.match(title):
                continue
            # 日期：同级 <span class="right date">2026-09-29</span>
            row = link.find_parent(["li", "dd", "tr"]) or link.parent
            date_text = ""
            if row is not None:
                date_node = row.select_one("span.right.date, span.date, .right")
                if date_node is not None:
                    date_text = date_node.get_text(" ", strip=True)
            items.append(ListItem(
                title=title,
                source_url=url,
                publish_time=normalize_time(date_text or (row.get_text(" ", strip=True) if row else "")),
                origin=self.default_origin,
            ))
        return items

    # ---- 详情 ----

    def parse_detail(self, html: str, url: str, item: ListItem | None = None) -> dict:
        return parse_detail_page(
            html, url,
            content_selectors=KJJ_CONTENT_SELECTORS,
            default_origin=self.default_origin,
            fallback_time=(item.publish_time if item else ""),
            fallback_summary=(item.summary if item else ""),
        )


# ==========================================================================
# 五、适配器 2：芜湖市政府 RSS
# ==========================================================================

_GOV_CONTENT_SELECTORS = [
    "div.wzcon",                    # 实测正文容器（政府站新版模板）
    "div.wenzhang .wzcon",
    "div.j-fontContent",
    "div.newscontnet",
    "div#zoom",
    "div.zoom",
    "div.article-content",
    "div.content",
    "div.TRS_Editor",
]


class WuhuGovRssAdapter:
    """芜湖市政府 RSS 适配器（标准 RSS 2.0）。

    条目结构（实测 https://www.wuhu.gov.cn/rss/rss.xml?siteId=6787231）：
        <item>
          <title><![CDATA[ 陈东调研数字经济发展工作 ]]></title>
          <link>https://www.wuhu.gov.cn/xwzx/zwyw/41350150.html</link>
          <pubDate>2026-10-04 01:39:11.0</pubDate>
          <description><![CDATA[ 摘要…… ]]></description>
        </item>
    description 自带摘要，可直接作为 content 兜底；详情页能抓到正文时以正文为准。
    """

    name = "wuhu_gov_rss"
    supports_paging = False

    def __init__(self, source: dict, client: HttpClient):
        self.source = source
        self.client = client
        self.list_url = source.get("list_url", "")
        self.default_origin = "芜湖市人民政府"

    def list_page_urls(self, max_pages: int) -> list[str]:
        """RSS 一次返回全部条目，没有分页概念。"""
        return [self.list_url] if self.list_url else []

    def parse_list(self, html: str, page_url: str) -> list[ListItem]:
        # RSS 必须用 XML 解析器，否则 lxml 的 HTML 解析器会把 <item> 当未知标签
        soup = make_soup(html, is_xml=True)
        items: list[ListItem] = []
        for node in soup.find_all("item"):
            title_node = node.find("title")
            link_node = node.find("link")
            date_node = node.find("pubDate")
            desc_node = node.find("description")

            title = clean_text(title_node.get_text(strip=True)) if title_node else ""
            url = normalize_url(link_node.get_text(strip=True) if link_node else "", page_url)
            if not title or not url:
                continue
            # 过滤外文稿件（RSS 里混有英文版新闻）
            if is_probably_non_chinese(title):
                continue

            summary = strip_html_fragment(desc_node.get_text() if desc_node else "")
            items.append(ListItem(
                title=title,
                source_url=url,
                publish_time=normalize_time(date_node.get_text(strip=True) if date_node else ""),
                summary=summary,
                origin=self.default_origin,
            ))
        return items

    def parse_detail(self, html: str, url: str, item: ListItem | None = None) -> dict:
        result = parse_detail_page(
            html, url,
            content_selectors=_GOV_CONTENT_SELECTORS,
            default_origin=self.default_origin,
            fallback_time=(item.publish_time if item else ""),
            fallback_summary=(item.summary if item else ""),
        )
        return result


# ==========================================================================
# 六、适配器 3：芜湖市政府新闻中心列表
# ==========================================================================

class WuhuGovListAdapter:
    """芜湖市政府新闻中心列表适配器。

    列表页特征（实测 www.wuhu.gov.cn/xwzx/zwyw/index.html）：
        <li class="odd">
          <a class="left" href="https://www.wuhu.gov.cn/xwzx/zwyw/41350150.html"
             title="陈东调研数字经济发展工作"><span>……</span></a>
          <span class="right date">10-04</span>       <-- 只有月-日，没有年份
        </li>
    列表日期只有 "10-04"，按"不超过今天"规则补全年份（见 extract.normalize_time）。
    """

    name = "wuhu_gov_list"
    supports_paging = False   # 实测该模板的 index_1.html 同样是 404

    def __init__(self, source: dict, client: HttpClient):
        self.source = source
        self.client = client
        self.list_url = source.get("list_url", "")
        self.default_origin = "芜湖市人民政府"

    def list_page_urls(self, max_pages: int) -> list[str]:
        return [self.list_url] if self.list_url else []

    def parse_list(self, html: str, page_url: str) -> list[ListItem]:
        soup = make_soup(html)
        items: list[ListItem] = []
        for link in soup.find_all("a", href=True):
            href = link.get("href") or ""
            if not re.search(r"/\d{6,}\.html$", href.split("?")[0]):
                continue
            url = normalize_url(href, page_url)
            if not url or not same_section(url, self.list_url):
                continue
            title = clean_text(link.get("title") or link.get_text(" ", strip=True))
            if not title:
                continue
            row = link.find_parent(["li", "dd", "tr"]) or link.parent
            date_text = ""
            if row is not None:
                date_node = row.select_one("span.right.date, span.date, .right")
                if date_node is not None:
                    date_text = date_node.get_text(" ", strip=True)
            # 列表页同时提供了"列表日期"（如 2026-10-04，实测该站 meta 里也有年份）
            items.append(ListItem(
                title=title,
                source_url=url,
                publish_time=normalize_time(date_text or (row.get_text(" ", strip=True) if row else "")),
                origin=self.default_origin,
            ))
        return items

    def parse_detail(self, html: str, url: str, item: ListItem | None = None) -> dict:
        return parse_detail_page(
            html, url,
            content_selectors=_GOV_CONTENT_SELECTORS,
            default_origin=self.default_origin,
            fallback_time=(item.publish_time if item else ""),
            fallback_summary=(item.summary if item else ""),
        )


# ==========================================================================
# 七、适配器 4：芜湖新闻网列表
# ==========================================================================

_WUHUNEWS_CONTENT_SELECTORS = [
    "div.article-content",          # 实测正文容器
    "div.news_content",
    "div.article",
    "div.content",
]


class WuhuNewsListAdapter:
    """芜湖新闻网列表适配器。

    列表页特征（实测 www.wuhunews.cn/yaowen/）：
        <li>
          <a class="itb-title" href="https://www.wuhunews.cn/yaowen/2026-10-01/669171.html">
            <h3>“五新”二坝  智启新程</h3>
          </a>
          <small><time>2026-10-01 02:03</time></small>
        </li>
    翻页：https://www.wuhunews.cn/yaowen/?pp=10、?pp=20 ……（每页 10 条）
    """

    name = "wuhunews_list"
    supports_paging = True
    PAGE_SIZE = 10

    def __init__(self, source: dict, client: HttpClient):
        self.source = source
        self.client = client
        self.list_url = source.get("list_url", "")
        self.default_origin = "芜湖新闻网"

    # ---- 列表 ----

    def list_page_urls(self, max_pages: int) -> list[str]:
        """第 1 页是原始 URL，之后每页加 ?pp=<offset>。"""
        pages = [self.list_url]
        for index in range(1, max(1, max_pages)):
            pages.append(self._page_url(index))
        return pages

    def _page_url(self, page_index: int) -> str:
        parts = urlparse(self.list_url)
        query = "pp=%d" % (page_index * self.PAGE_SIZE)
        return urlunparse((parts.scheme, parts.netloc, parts.path, "", query, ""))

    def parse_list(self, html: str, page_url: str) -> list[ListItem]:
        soup = make_soup(html)
        items: list[ListItem] = []
        for link in soup.find_all("a", href=True):
            href = link.get("href") or ""
            # 详情链接形如 /yaowen/2026-10-01/669171.html
            if not re.search(r"/\d{4}-\d{2}-\d{2}/\d+\.html$", href.split("?")[0]):
                continue
            url = normalize_url(href, page_url)
            # 列表页混有"网络举报""媒体社会责任报告"等站内固定链接，用栏目前缀过滤
            if not url or not same_section(url, self.list_url):
                continue
            title = clean_text(link.get_text(" ", strip=True))
            if not title:
                continue
            # 时间：同级的 <time> 或 <small>
            row = link.find_parent(["li", "dd", "div"]) or link.parent
            date_text = ""
            if row is not None:
                time_node = row.find(["time", "small", "span"])
                if time_node is not None:
                    date_text = time_node.get_text(" ", strip=True)
            # URL 路径里自带日期，作为时间兜底：/yaowen/2026-10-01/669171.html
            path_date = re.search(r"/(\d{4}-\d{2}-\d{2})/", url)
            stamp = normalize_time(date_text) or (normalize_time(path_date.group(1)) if path_date else "")
            items.append(ListItem(
                title=title,
                source_url=url,
                publish_time=stamp,
                origin=self.default_origin,
            ))
        return items

    # ---- 详情 ----

    def parse_detail(self, html: str, url: str, item: ListItem | None = None) -> dict:
        result = parse_detail_page(
            html, url,
            content_selectors=_WUHUNEWS_CONTENT_SELECTORS,
            default_origin=self.default_origin,
            fallback_time=(item.publish_time if item else ""),
            fallback_summary=(item.summary if item else ""),
        )
        # 该站详情页没有"来源："标签，路径 /yaowen/2026-10-01/669171.html 里的日期可兜底
        if not result["publish_time"]:
            path_date = re.search(r"/(\d{4}-\d{2}-\d{2})/", url)
            if path_date:
                result["publish_time"] = normalize_time(path_date.group(1))
        return result


# ==========================================================================
# 八、适配器注册表
# ==========================================================================

ADAPTERS: dict[str, type] = {
    WuhuKjjListAdapter.name: WuhuKjjListAdapter,
    WuhuGovRssAdapter.name: WuhuGovRssAdapter,
    WuhuGovListAdapter.name: WuhuGovListAdapter,
    WuhuNewsListAdapter.name: WuhuNewsListAdapter,
}

# 适配器别名：后端配置里写了别的名字时也能跑
ADAPTER_ALIASES = {
    "kjj": WuhuKjjListAdapter.name,
    "wuhu_kjj": WuhuKjjListAdapter.name,
    "rss": WuhuGovRssAdapter.name,
    "wuhu_rss": WuhuGovRssAdapter.name,
    "gov_list": WuhuGovListAdapter.name,
    "wuhu_gov": WuhuGovListAdapter.name,
    "wuhunews": WuhuNewsListAdapter.name,
    "wuhu_news_list": WuhuNewsListAdapter.name,
}


def create_adapter(source: dict, client: HttpClient):
    """按源的 adapter 字段实例化适配器；未知名字抛出明确错误。"""
    adapter_name = clean_text(source.get("adapter") or "")
    adapter_name = ADAPTER_ALIASES.get(adapter_name, adapter_name)
    adapter_cls = ADAPTERS.get(adapter_name)
    if adapter_cls is None:
        raise ValueError("未知的适配器类型: %r（可用: %s）"
                         % (source.get("adapter"), ", ".join(sorted(ADAPTERS))))
    return adapter_cls(source, client)
