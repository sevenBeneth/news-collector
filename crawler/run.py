# -*- coding: utf-8 -*-
"""
run.py —— 多源新闻采集主流程 + 命令行入口

用法示例：
    python run.py                                  # 抓所有启用源
    python run.py --source-id 1                    # 只抓 1 号源
    python run.py --source-id 1,5                  # 抓 1 号和 5 号源
    python run.py --limit 5 --dry-run              # 每源最多 5 条，只抓不入库
    python run.py --list-sources                   # 打印后端配置的采集源
    python run.py --max-pages 2                    # 覆盖源的 max_pages
    python run.py --no-content                     # 只抓标题，不入正文详情页

流程（单个源）：
    列表页 → 条目去重 → 关键词过滤 → 详情页抽正文 → 组装 NewsItem →
    （非 dry-run）批量推送入库 + 回写日志 + touch 源

设计原则：单源异常绝不影响其它源；后端未启动时 --dry-run 仍可独立工作。
"""

from __future__ import annotations

import argparse
import io
import logging
import os
import sys
import time
import traceback
from datetime import datetime

import config
from adapters import (ADAPTERS, FetchError, HttpClient, ListItem, NewsItem,
                      create_adapter, is_probably_non_chinese)
from extract import clean_content, clean_text
from store import BackendError, IngestStore

# --------------------------------------------------------------------------
# 一、日志与控制台输出
# --------------------------------------------------------------------------

# ANSI 颜色：Windows Terminal / PowerShell 7 都支持；旧控制台会退化成纯文本
COLOR = {
    "reset": "\033[0m", "bold": "\033[1m", "dim": "\033[2m",
    "red": "\033[31m", "green": "\033[32m", "yellow": "\033[33m",
    "blue": "\033[34m", "magenta": "\033[35m", "cyan": "\033[36m", "gray": "\033[90m",
}
_USE_COLOR = True


def _c(text: str, color: str) -> str:
    """按开关给文本上色。"""
    if not _USE_COLOR or color not in COLOR:
        return text
    return COLOR[color] + text + COLOR["reset"]


def setup_console_encoding() -> None:
    """把标准输出切成 UTF-8：Windows 控制台默认 GBK，直接打中文会 UnicodeEncodeError。"""
    global _USE_COLOR
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            buffer = getattr(stream, "buffer", None)
            if buffer is not None:
                try:
                    setattr(sys, stream_name,
                            io.TextIOWrapper(buffer, encoding="utf-8", errors="replace"))
                except Exception:
                    pass
    if os.getenv("NO_COLOR"):
        _USE_COLOR = False
    if not sys.stdout.isatty() and os.getenv("WUHU_FORCE_COLOR") != "1":
        # 输出被重定向到文件时不需要颜色
        _USE_COLOR = False


def setup_logging() -> tuple[logging.Logger, str]:
    """同时输出到控制台和 crawler/logs/run-YYYYmmdd-HHMMSS.log。"""
    os.makedirs(config.LOG_DIR, exist_ok=True)
    log_path = os.path.join(config.LOG_DIR, "run-%s.log" % datetime.now().strftime("%Y%m%d-%H%M%S"))

    logger = logging.getLogger("wuhu-crawler")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.propagate = False

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(console_handler)

    return logger, log_path


# --------------------------------------------------------------------------
# 二、采集统计
# --------------------------------------------------------------------------

class SourceStat:
    """单个源的采集统计，字段与 POST /api/ingest/log 对应。"""

    def __init__(self, source: dict):
        self.source = source
        self.source_id = source.get("id")
        self.source_name = source.get("name") or source.get("list_url") or "-"
        self.list_total = 0      # 列表页拿到的条目数
        self.filtered = 0        # 被关键词/去重/无效内容过滤掉的条数
        self.fetched = 0         # 尝试抓详情的条数
        self.failed = 0          # 详情抓取失败的条数
        self.items: list[NewsItem] = []
        self.inserted = 0
        self.duplicated = 0
        self.status = 1
        self.message = "ok"
        self.started_at = time.time()

    @property
    def total(self) -> int:
        """上报给后端的 total：列表页实际处理的条目数。"""
        return self.list_total

    @property
    def duration_ms(self) -> int:
        return int((time.time() - self.started_at) * 1000)

    def to_log(self) -> dict:
        return {
            "source_id": self.source_id,
            "source_name": self.source_name,
            "total": self.total,
            "inserted": self.inserted,
            "duplicated": self.duplicated,
            "filtered": self.filtered,
            "status": self.status,
            "message": self.message,
            "duration_ms": self.duration_ms,
        }


# --------------------------------------------------------------------------
# 三、关键词过滤
# --------------------------------------------------------------------------

def parse_keywords(keyword_filter) -> list[str]:
    """源上的 keyword_filter 是逗号分隔字符串（也兼容数组/中文逗号）。"""
    if not keyword_filter:
        return []
    if isinstance(keyword_filter, (list, tuple)):
        raw = list(keyword_filter)
    else:
        raw = str(keyword_filter).replace("，", ",").split(",")
    return [clean_text(word) for word in raw if clean_text(word)]


def match_keywords(title: str, content: str, keywords: list[str]) -> bool:
    """标题或正文命中任一关键词即通过；未配置关键词则一律通过。"""
    if not keywords:
        return True
    haystack = (title or "") + "\n" + (content or "")
    return any(word in haystack for word in keywords)


# --------------------------------------------------------------------------
# 四、单源采集
# --------------------------------------------------------------------------

def crawl_source(source: dict, client: HttpClient, logger: logging.Logger,
                 limit: int | None, with_content: bool, max_pages_override: int | None,
                 dry_run: bool) -> SourceStat:
    """采集单个源；任何异常都记录到 stat 里，不向外抛。"""
    stat = SourceStat(source)
    adapter_name = source.get("adapter")
    category_code = source.get("default_category_code") or ""
    keywords = parse_keywords(source.get("keyword_filter"))

    logger.info("")
    logger.info(_c("▶ 源 #%s %s" % (stat.source_id, stat.source_name), "bold"))
    logger.info("  适配器: %s | 分类: %s" % (adapter_name, category_code or "-"))
    logger.info("  列表页: %s" % source.get("list_url"))
    logger.info("  关键词: %s" % ("、".join(keywords) if keywords else "（未配置，不过滤）"))

    try:
        adapter = create_adapter(source, client)
    except ValueError as exc:
        stat.status = 0
        stat.message = str(exc)
        logger.error(_c("  ✗ %s" % exc, "red"))
        return stat

    # ---- 1. 列表页 ----
    max_pages = max_pages_override if max_pages_override else int(source.get("max_pages") or 1)
    if not getattr(adapter, "supports_paging", False) and max_pages > 1:
        logger.info(_c("  提示: 该适配器分页由 JS 渲染，max_pages=%d 不生效，只抓第 1 页" % max_pages, "yellow"))
    page_urls = adapter.list_page_urls(max_pages)

    list_items: list[ListItem] = []
    seen_urls: set[str] = set()          # 本次运行内按 source_url 去重
    for page_url in page_urls:
        try:
            html, _ = client.get_html(page_url, is_xml=(adapter_name == "wuhu_gov_rss"))
        except (FetchError, Exception) as exc:
            stat.status = 0
            stat.message = "列表页抓取失败: %s" % exc
            logger.error(_c("  ✗ 列表页抓取失败 %s -> %s" % (page_url, exc), "red"))
            return stat

        page_items = adapter.parse_list(html, page_url)
        fresh = 0
        for item in page_items:
            if not item.source_url or item.source_url in seen_urls:
                continue
            if is_probably_non_chinese(item.title):
                continue
            seen_urls.add(item.source_url)
            list_items.append(item)
            fresh += 1
        logger.info("  列表 %s → 解析 %d 条（新增 %d 条）" % (page_url, len(page_items), fresh))
        # 翻页返回的是完全重复的内容（部分栏目的 ?pp= 参数实际无效）时提前结束，
        # 避免对同一页重复发请求，也避免把同一批稿件算两次。
        if fresh == 0 and len(page_urls) > 1 and page_url != page_urls[0]:
            logger.info(_c("  该页与前页内容完全重复，停止翻页", "yellow"))
            break
        if limit and len(list_items) >= limit:
            list_items = list_items[:limit]
            break

    if limit:
        list_items = list_items[:limit]
    stat.list_total = len(list_items)
    logger.info("  合计待处理: %d 条" % stat.list_total)

    if not list_items:
        stat.status = 0
        stat.message = "列表页未解析到任何条目（站点结构可能变化）"
        logger.warning(_c("  ⚠ 未解析到条目", "yellow"))
        return stat

    # ---- 2. 逐条处理详情 ----
    # 注意：关键词过滤必须在"抓到正文之后"再做，因为规则是"标题或正文命中任一关键词"。
    # 如果只看标题就过滤，会漏掉"标题平淡但正文讲科技创新"的稿件。
    for index, item in enumerate(list_items, 1):
        prefix = "  [%d/%d]" % (index, stat.list_total)

        # --no-content 模式下没有正文，只能拿列表摘要参与判断
        if not with_content and not match_keywords(item.title, item.summary, keywords):
            stat.filtered += 1
            logger.info("%s %s %s" % (prefix, _c("跳过", "yellow"),
                                      clean_text(item.title)[:48] + "（关键词未命中）"))
            continue

        detail = {"title": "", "content": "", "origin": "", "publish_time": "", "photo_url": ""}
        if with_content:
            try:
                html, _ = client.get_html(item.source_url, is_xml=False)
                detail = adapter.parse_detail(html, item.source_url, item)
                stat.fetched += 1
            except Exception as exc:
                stat.failed += 1
                logger.warning("%s %s 详情抓取失败: %s" % (prefix, _c("✗", "red"), exc))

        title = clean_text(detail.get("title") or item.title)
        content = clean_content(detail.get("content") or "")
        if not content and with_content:
            content = clean_content(item.summary)
        origin = clean_text(detail.get("origin") or item.origin or "")
        publish_time = detail.get("publish_time") or item.publish_time or ""
        photo_url = detail.get("photo_url") or item.photo_url or ""

        # 关键词过滤：标题或正文命中任一关键词
        if not match_keywords(title, content, keywords):
            stat.filtered += 1
            logger.info("%s %s %s" % (prefix, _c("跳过", "yellow"),
                                      title[:48] + "（关键词未命中）"))
            continue

        # 正文长度不足则视为抽取失败
        if with_content and len(content) < config.MIN_CONTENT_LENGTH:
            if content:
                stat.filtered += 1
                logger.info("%s %s %s" % (prefix, _c("跳过", "yellow"),
                                          title[:48] + "（正文仅 %d 字，抽取失败）" % len(content)))
            else:
                stat.filtered += 1
                logger.info("%s %s %s" % (prefix, _c("跳过", "yellow"), title[:48] + "（无正文）"))
            continue

        news = NewsItem(
            title=title,
            source_url=item.source_url,
            content=content,
            photo_url=photo_url,
            origin=origin or stat.source_name,
            publish_time=publish_time,
            category_code=category_code,
        )
        stat.items.append(news)
        logger.info("%s %s 正文 %d 字 | %s | %s | %s"
                    % (prefix, _c("✓", "green"), len(content), publish_time or "时间未知",
                       news.origin, title[:40]))
        if dry_run:
            print_item_detail(news, logger)

    return stat


def print_item_detail(news: NewsItem, logger: logging.Logger) -> None:
    """--dry-run 时打印解析结果，便于人工核对中文是否正确。"""
    preview = news.content[:120].replace("\n", " ")
    logger.info(_c("       标题: %s" % news.title, "cyan"))
    logger.info(_c("       来源: %s | 时间: %s | 正文长度: %d"
                   % (news.origin or "-", news.publish_time or "-", len(news.content)), "cyan"))
    logger.info(_c("       链接: %s" % news.source_url, "gray"))
    if news.photo_url:
        logger.info(_c("       封面: %s" % news.photo_url, "gray"))
    logger.info(_c("       前120字: %s" % preview, "cyan"))


# --------------------------------------------------------------------------
# 五、源列表获取 / 打印
# --------------------------------------------------------------------------

def load_sources(store: IngestStore, logger: logging.Logger, source_ids: list[str]) -> list[dict]:
    """优先从后端取源；后端不可用时用本地兜底源（保证 --dry-run 可用）。"""
    try:
        sources = store.fetch_sources()
        logger.info(_c("✔ 已从后端获取 %d 个启用中的采集源" % len(sources), "green"))
    except BackendError as exc:
        logger.warning(_c("⚠ 后端不可用：%s" % exc, "yellow"))
        logger.warning(_c("  改用 crawler/config.py 里的本地兜底源定义（仅用于 --dry-run 验证）", "yellow"))
        sources = list(config.FALLBACK_SOURCES)

    if source_ids:
        wanted = set(source_ids)
        selected = [s for s in sources if str(s.get("id")) in wanted]
        missing = wanted - {str(s.get("id")) for s in selected}
        if missing:
            logger.warning(_c("⚠ 源 id %s 不在源列表中" % ",".join(sorted(missing)), "yellow"))
        sources = selected

    # 只处理适配器已知且地址非空的源
    valid, invalid = [], []
    for source in sources:
        adapter_name = source.get("adapter")
        if adapter_name not in ADAPTERS and adapter_name not in ("kjj", "rss", "gov_list", "wuhunews"):
            invalid.append(source)
            continue
        if not source.get("list_url"):
            invalid.append(source)
            continue
        valid.append(source)
    for source in invalid:
        logger.warning(_c("⚠ 跳过源 #%s %s：适配器 %r 未实现或缺少 list_url"
                          % (source.get("id"), source.get("name"), source.get("adapter")), "yellow"))
    return valid


def print_sources(sources: list[dict], logger: logging.Logger) -> None:
    """--list-sources 的表格输出。"""
    logger.info("")
    logger.info(_c("采集源列表（%d 个）" % len(sources), "bold"))
    logger.info("-" * 108)
    logger.info("%-4s %-22s %-16s %-6s %s" % ("ID", "名称", "适配器", "页数", "列表地址"))
    logger.info("-" * 108)
    for source in sources:
        logger.info("%-4s %-22s %-16s %-6s %s" % (
            source.get("id"), (source.get("name") or "")[:20],
            source.get("adapter") or "", source.get("max_pages") or 1,
            source.get("list_url") or ""))
    logger.info("-" * 108)


# --------------------------------------------------------------------------
# 六、CLI
# --------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="芜湖市科技创新新闻多源采集器（课程作业项目）",
        epilog="示例：\n"
               "  python run.py --dry-run --source-id 1 --limit 3\n"
               "  python run.py --source-id 1,5 --limit 10\n"
               "  python run.py --list-sources\n",
    )
    parser.add_argument("--source-id", default="",
                        help="只采集指定源，多个用逗号分隔，如 1 或 1,5")
    parser.add_argument("--limit", type=int, default=0,
                        help="每个源最多处理的条目数（0 表示不限制）")
    parser.add_argument("--dry-run", action="store_true",
                        help="不访问后端，只抓取并打印解析结果")
    parser.add_argument("--no-content", action="store_true",
                        help="只抓列表标题，不进入详情页抓正文")
    parser.add_argument("--list-sources", action="store_true",
                        help="打印后端返回的采集源列表后退出")
    parser.add_argument("--max-pages", type=int, default=0,
                        help="覆盖每个源的 max_pages（0 表示用源自身配置）")
    parser.add_argument("--delay", type=float, default=None,
                        help="覆盖请求间隔下限（秒），便于快速演示")
    parser.add_argument("--verbose", action="store_true", help="打印更详细的异常堆栈")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    setup_console_encoding()
    logger, log_path = setup_logging()
    logger.info(_c("=" * 92, "gray"))
    logger.info(_c("芜湖市科技创新新闻采集器  |  %s" % datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "bold"))
    logger.info(_c("后端: %s  |  日志文件: %s" % (config.BACKEND_BASE_URL, log_path), "gray"))
    logger.info(_c("=" * 92, "gray"))

    source_ids = [token.strip() for token in (args.source_id or "").split(",") if token.strip()]
    limit = args.limit if args.limit and args.limit > 0 else None
    max_pages_override = args.max_pages if args.max_pages and args.max_pages > 0 else None

    if args.dry_run:
        logger.info(_c("模式: DRY-RUN（只抓取解析，不推送后端）", "magenta"))
    else:
        logger.info(_c("模式: 正式采集（抓取 + 推送后端）", "magenta"))

    # ---- 后端连接 ----
    store = IngestStore()
    backend_alive = False
    if not args.dry_run:
        backend_alive = store.ping()
        if backend_alive:
            logger.info(_c("✔ 后端连接正常", "green"))
        else:
            logger.error(_c("✗ 后端不可用（%s）：抓取会继续，但数据无法入库；"
                            "若只想验证抓取请加 --dry-run" % config.BACKEND_BASE_URL, "red"))
    else:
        backend_alive = store.ping()
    if args.dry_run and not backend_alive:
        logger.info(_c("提示: 后端未启动，本次使用本地兜底源定义（--dry-run 模式可独立工作）", "yellow"))

    # ---- 取源 ----
    source_scope = source_ids or None
    if args.list_sources:
        try:
            sources = store.fetch_sources()
            print_sources(sources, logger)
            logger.info(_c("✔ 以上 %d 个源来自后端 %s" % (len(sources), config.BACKEND_BASE_URL), "green"))
        except BackendError as exc:
            logger.error(_c("✗ 无法从后端获取采集源：%s" % exc, "red"))
            logger.error(_c("  请确认后端已启动（%s）后重试；"
                            "离线预览可执行 python run.py --list-sources 前先启动服务，"
                            "或查看 crawler/config.py 里的 FALLBACK_SOURCES" % config.BACKEND_BASE_URL, "yellow"))
            print_sources(config.FALLBACK_SOURCES, logger)
            logger.info(_c("  以上为 crawler/config.py 中的本地兜底源定义（离线参考）", "yellow"))
            return 0
        return 0

    sources = load_sources(store, logger, source_ids)
    if not sources:
        logger.error(_c("没有可执行的采集源，退出。", "red"))
        return 1

    if source_scope:
        logger.info(_c("范围: 仅源 %s" % ",".join(source_scope), "gray"))
    if limit:
        logger.info(_c("限制: 每源最多 %d 条" % limit, "gray"))
    if args.no_content:
        logger.info(_c("模式: --no-content（不抓正文）", "gray"))

    # ---- 逐源采集 ----
    client = HttpClient()
    # --delay 便于课堂演示时加快或放慢
    if args.delay is not None:
        client.min_delay = args.delay
        client.max_delay = max(args.delay, args.delay * 2)

    stats: list[SourceStat] = []
    overall_start = time.time()
    for source in sources:
        try:
            stat = crawl_source(source, client, logger, limit,
                                with_content=not args.no_content,
                                max_pages_override=max_pages_override,
                                dry_run=args.dry_run)
        except Exception as exc:      # 单源异常不能中断整体流程
            stat = SourceStat(source)
            stat.status = 0
            stat.message = "未捕获异常: %s: %s" % (type(exc).__name__, exc)
            logger.error(_c("✗ 源 #%s 采集异常: %s" % (source.get("id"), exc), "red"))
            if args.verbose:
                logger.error(traceback.format_exc())

        # ---- 入库 ----
        if not args.dry_run and stat.items and stat.status == 1:
            try:
                pushed = store.push_news(stat.items)
                stat.inserted = pushed.get("inserted", 0)
                stat.duplicated = pushed.get("duplicated", 0)
                if stat.message == "ok":
                    stat.message = "ok"
                logger.info(_c("  ⇪ 推送 %d 条 → 新增 %d，重复 %d，后端过滤 %d"
                               % (len(stat.items), stat.inserted, stat.duplicated,
                                  pushed.get("filtered", 0)), "green"))
            except BackendError as exc:
                stat.status = 0
                stat.message = "入库失败: %s" % exc
                logger.error(_c("  ✗ 入库失败: %s（已抓到的 %d 条本次丢弃，后端恢复后会重新抓到）"
                                % (exc, len(stat.items)), "red"))
        elif args.dry_run and stat.items:
            logger.info(_c("  (dry-run) 本应推送 %d 条" % len(stat.items), "magenta"))

        # ---- 日志回写 + touch ----
        if not args.dry_run:
            if store.push_log(stat.to_log()):
                logger.info(_c("  ⇪ 已回写采集日志 (status=%d, %dms)" % (stat.status, stat.duration_ms), "green"))
            if stat.status == 1 and store.touch_source(stat.source_id):
                logger.info(_c("  ⇪ 已更新 last_crawl_time", "green"))
        stats.append(stat)

    # ---- 汇总 ----
    print_summary(stats, logger, time.time() - overall_start, args.dry_run, client.request_count)
    logger.info(_c("日志已写入: %s" % log_path, "gray"))

    if args.dry_run:
        return 0
    failed = [s for s in stats if s.status != 1]
    return 1 if failed and len(failed) == len(stats) else 0


def print_summary(stats: list[SourceStat], logger: logging.Logger, elapsed: float,
                  dry_run: bool, request_count: int) -> None:
    """打印整体汇总表。"""
    logger.info("")
    logger.info(_c("=" * 92, "gray"))
    logger.info(_c("采集汇总", "bold"))
    logger.info("-" * 92)
    logger.info("%-4s %-24s %6s %6s %8s %8s %8s" %
                ("ID", "源名称", "条目", "解析", "过滤", "新增", "重复"))
    logger.info("-" * 92)
    total_items = total_filtered = total_inserted = total_duplicated = 0
    for stat in stats:
        total_items += stat.total
        total_filtered += stat.filtered
        total_inserted += stat.inserted
        total_duplicated += stat.duplicated
        name = stat.source_name[:22]
        logger.info("%-4s %-24s %6d %6d %8d %8d %8d%s" % (
            stat.source_id, name, stat.total, len(stat.items), stat.filtered,
            stat.inserted, stat.duplicated,
            "" if stat.status == 1 else _c("  ← 失败: %s" % stat.message, "red")))
    logger.info("-" * 92)
    logger.info("合计: 列表 %d 条 | 成功解析 %d 条 | 过滤 %d 条 | 新增 %d | 重复 %d"
                % (total_items, sum(len(s.items) for s in stats), total_filtered,
                   total_inserted, total_duplicated))
    logger.info("耗时 %.1fs | HTTP 请求 %d 次 | %s"
                % (elapsed, request_count, "DRY-RUN（未入库）" if dry_run else "已入库"))
    logger.info(_c("=" * 92, "gray"))


if __name__ == "__main__":
    sys.exit(main())
