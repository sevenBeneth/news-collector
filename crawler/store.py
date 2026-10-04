# -*- coding: utf-8 -*-
"""
store.py —— 后端 HTTP API 调用层

严格对应 docs/api.md"二、采集端"：
    GET  /api/ingest/sources              采集源列表
    POST /api/ingest/news                 批量入库（JSON 数组，按 source_url 幂等）
    POST /api/ingest/log                  回写单次采集日志
    POST /api/ingest/source/{id}/touch    更新 last_crawl_time

鉴权：Header  X-Ingest-Token: wuhu-ingest-2026

设计要点：后端未启动时不让整个程序崩掉 —— 所有方法失败都返回 None / 空列表，
由 run.py 决定是"降级用本地兜底源继续抓"还是"跳过入库只打日志"。
"""

from __future__ import annotations

import json

import requests

import config
from adapters import NewsItem


class BackendError(Exception):
    """后端接口返回业务错误或网络不可达。"""


def _brief_error(exc: Exception) -> str:
    """把 requests 冗长的异常链压成一句人话，便于控制台/日志阅读。"""
    text = str(exc)
    # ConnectionError 的原文本形如：
    #   HTTPConnectionPool(host=..., port=...): Max retries exceeded with url: ...
    #   (Caused by NewConnectionError('<...>: Failed to establish a new connection: [WinError 10061] ...'))
    # 只保留 "Max retries exceeded" 之前的部分和最后一条根因，信息足够定位问题。
    marker = text.find(": Max retries exceeded")
    if marker > 0:
        root = text.rsplit(":", 1)[-1].strip()
        text = text[:marker] + "；根因: " + root
    if len(text) > 140:
        text = text[:140] + "…"
    return "%s: %s" % (type(exc).__name__, text)


class IngestStore:
    """采集端 API 客户端（单例式使用，内部维护一个 requests.Session）。"""

    def __init__(self, base_url: str | None = None, token: str | None = None,
                 timeout: float | None = None):
        self.base_url = (base_url or config.BACKEND_BASE_URL).rstrip("/")
        self.token = token or config.INGEST_TOKEN
        self.timeout = timeout or config.API_TIMEOUT
        self.session = requests.Session()
        self.session.headers.update({
            "X-Ingest-Token": self.token,
            "Accept": "application/json",
            "User-Agent": config.USER_AGENT,
        })
        # 后端探活状态：只作为提示信息，不会阻止后续请求 ——
        # 后端重启或暂时抽风后，下一次请求仍会正常发出（可用性由 retry/异常处理保证）。
        self.available = True

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------

    def _url(self, path: str) -> str:
        return self.base_url + path

    def _request(self, method: str, path: str, **kwargs):
        """统一请求包装：捕获网络异常，转成 BackendError。"""
        try:
            response = self.session.request(method, self._url(path), timeout=self.timeout, **kwargs)
        except requests.RequestException as exc:
            self.available = False
            raise BackendError("无法连接后端 %s（%s）" % (self.base_url, _brief_error(exc))) from exc

        if response.status_code >= 400:
            raise BackendError("后端返回 HTTP %s: %s" % (response.status_code, path))
        try:
            payload = response.json()
        except ValueError as exc:
            raise BackendError("后端返回的不是 JSON（%s）: %s" % (path, response.text[:200])) from exc

        # 统一响应体 {"code":0,"msg":"SUCCESS!","data":{...}}
        code = payload.get("code")
        if code not in (0, None):
            raise BackendError("后端业务错误 code=%s msg=%s" % (code, payload.get("msg")))
        return payload.get("data")

    # ------------------------------------------------------------------
    # 1. 采集源列表
    # ------------------------------------------------------------------

    def fetch_sources(self) -> list[dict]:
        """GET /api/ingest/sources → 启用中的源列表。失败抛 BackendError。"""
        data = self._request("GET", config.API_SOURCES)
        if data is None:
            return []
        if isinstance(data, dict):
            # 兼容 {list:[...]} / {records:[...]} 之类分页包装
            data = data.get("list") or data.get("records") or data.get("rows") or []
        if not isinstance(data, list):
            raise BackendError("采集源接口返回结构异常: %s" % type(data).__name__)
        return [item for item in data if isinstance(item, dict)]

    # ------------------------------------------------------------------
    # 2. 批量入库
    # ------------------------------------------------------------------

    def push_news(self, items: list[NewsItem]) -> dict:
        """POST /api/ingest/news，按 BATCH_SIZE 切片推送。

        返回累计统计 {"total":n,"inserted":n,"duplicated":n,"filtered":n}。
        inserted / duplicated 由后端按 source_url 唯一键判定，这里只做累加打印。
        """
        summary = {"total": 0, "inserted": 0, "duplicated": 0, "filtered": 0}
        if not items:
            return summary

        batch_size = max(1, config.BATCH_SIZE)
        for start in range(0, len(items), batch_size):
            batch = items[start:start + batch_size]
            payload = [item.to_payload() for item in batch]
            data = self._request(
                "POST", config.API_NEWS,
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json; charset=utf-8"},
            ) or {}
            summary["total"] += int(data.get("total", len(batch)) or 0)
            summary["inserted"] += int(data.get("inserted", 0) or 0)
            summary["duplicated"] += int(data.get("duplicated", 0) or 0)
            summary["filtered"] += int(data.get("filtered", 0) or 0)
        return summary

    # ------------------------------------------------------------------
    # 3. 采集日志
    # ------------------------------------------------------------------

    def push_log(self, log: dict) -> bool:
        """POST /api/ingest/log 回写单次采集日志，失败不影响主流程。"""
        payload = {
            "source_id": log.get("source_id"),
            "source_name": log.get("source_name") or "",
            "total": int(log.get("total", 0) or 0),
            "inserted": int(log.get("inserted", 0) or 0),
            "duplicated": int(log.get("duplicated", 0) or 0),
            "filtered": int(log.get("filtered", 0) or 0),
            "status": int(log.get("status", 1) or 0),
            "message": (log.get("message") or "")[:900],
            "duration_ms": int(log.get("duration_ms", 0) or 0),
        }
        try:
            self._request(
                "POST", config.API_LOG,
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json; charset=utf-8"},
            )
            return True
        except BackendError:
            return False

    # ------------------------------------------------------------------
    # 4. 更新源的 last_crawl_time
    # ------------------------------------------------------------------

    def touch_source(self, source_id) -> bool:
        """POST /api/ingest/source/{id}/touch。"""
        if source_id in (None, ""):
            return False
        path = config.API_TOUCH.format(id=source_id)
        try:
            self._request("POST", path)
            return True
        except BackendError:
            return False

    # ------------------------------------------------------------------
    # 5. 健康检查
    # ------------------------------------------------------------------

    def ping(self) -> bool:
        """探测后端是否可用（用采集源接口做探活）。"""
        try:
            self.fetch_sources()
            return True
        except BackendError:
            return False
