# -*- coding: utf-8 -*-
"""
extract.py —— 页面解码、正文抽取、文本清洗、时间归一化

政府站点页面的编码非常混乱（HTTP 头常谎报 ISO-8859-1，实际是 UTF-8），
所以本模块把"取回字节 → 判定编码 → 解出 Unicode"这一段独立封装，
保证进入解析器的永远是正确的中文，落库前再统一清洗为 UTF-8 纯文本。
"""

from __future__ import annotations

import html as html_lib
import re
import unicodedata
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup, NavigableString, Tag

# --------------------------------------------------------------------------
# 一、编码处理
# --------------------------------------------------------------------------

# 这些编码名是"占位值"，浏览器/服务器常见地拿它们当默认值，
# 但如果 HTML 里写了 <meta charset>，一定以 meta 为准。
_PLACEHOLDER_ENCODINGS = {"iso-8859-1", "latin-1", "latin1", "ascii", "cp1252", "iso8859-1"}

_META_CHARSET_RE = re.compile(
    rb"""<meta[^>]+charset\s*=\s*["']?\s*([a-zA-Z0-9_\-]+)""", re.I
)
# 兼容 <meta http-equiv="Content-Type" content="text/html; charset=gb2312"> 这种老写法
_META_HTTPEQUIV_RE = re.compile(
    rb"""<meta[^>]+content\s*=\s*["'][^"']*charset\s*=\s*([a-zA-Z0-9_\-]+)""", re.I
)
_XML_DECL_RE = re.compile(rb"""<\?xml[^>]+encoding\s*=\s*["']([a-zA-Z0-9_\-]+)["']""", re.I)

# 这些"相关推荐 / 分享 / 二维码"之类的内容块不会进正文
_NOISE_SELECTORS = [
    "script", "style", "noscript", "iframe", "svg", "canvas", "form", "button",
    "nav", "header", "footer", "aside",
    ".share", ".bshare", ".share_box", ".sharebox", ".fenxiang",
    ".scan_code", ".scan_code_box", ".qrcode", ".j-qrcode", ".ewm",
    ".print_btn", ".wzbot", ".wzbot_btn", ".comment", ".comment_box",
    ".related", ".related_news", ".tuijian", ".recommend", ".xiangguan",
    ".ad", ".ads", ".advert", ".gg", ".banner", ".focus",
    ".crumbs", ".breadcrumb", ".position", ".dangqian", ".location",
    ".keyword", ".tags", ".tag_list", ".editor", ".zrbj",
    ".prev", ".next", ".pagination", ".page", ".fy",
    ".sidebar", ".side", ".left", ".right",
    ".wzfbxx", ".newsinfo", ".xxgk", ".fujian", ".annex", ".download",
]

_NOISE_TEXT_PATTERNS = [
    re.compile(r"^扫一扫在手机打开当前页$"),
    re.compile(r"^打印本页$"),
    re.compile(r"^字体[:：]?$"),
    re.compile(r"^【\s*大\s*中\s*小\s*】$"),
    re.compile(r"^阅读次数[:：]"),
    re.compile(r"^字号[:：]"),
    re.compile(r"^背景颜色[:：]?$"),
    re.compile(r"^分享到[:：]?$"),
    re.compile(r"^责任编辑[:：]"),
    re.compile(r"^上一篇[:：]|^下一篇[:：]"),
    re.compile(r"^(上一篇|下一篇)$"),
    re.compile(r"^关闭窗口$"),
    re.compile(r"^返回顶部$"),
]


def decode_response(resp, fallback: str = "utf-8") -> str:
    """把 requests 的响应字节解成正确的 Unicode 字符串。

    判定顺序（这是本项目踩坑最多的地方）：
      1. HTML/XML 里声明的编码（meta charset / xml declaration）—— 最权威；
      2. Unicode 系编码（utf-8 / utf-16）会用 BOM 或"能否严格解码"来佐证；
      3. HTTP 头里的 charset —— 但政府站点常谎报 ISO-8859-1，需降级为参考；
      4. requests 的 apparent_encoding（基于 charset_normalizer 的统计猜测）；
      5. 兜底 utf-8 + errors='replace'。
    """
    raw = resp.content or b""
    if not raw:
        return ""

    header_enc = (resp.encoding or "").strip()

    # --- 1. 文档内部声明 ---
    declared = None
    head = raw[:6000]
    for pattern in (_META_CHARSET_RE, _META_HTTPEQUIV_RE, _XML_DECL_RE):
        match = pattern.search(head)
        if match:
            declared = match.group(1).decode("ascii", "ignore")
            break

    # --- 2. BOM 优先 ---
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig", errors="replace")
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16", errors="replace")

    # --- 3. 依次尝试候选编码 ---
    candidates = []
    if declared:
        candidates.append(declared)
    if header_enc and header_enc.lower() not in _PLACEHOLDER_ENCODINGS:
        candidates.append(header_enc)
    if header_enc:
        candidates.append(header_enc)  # 占位编码也兜一下，放最后
    candidates.append("utf-8")
    apparent = getattr(resp, "apparent_encoding", None)
    if apparent:
        candidates.append(apparent)
    candidates.append(fallback)

    tried = set()
    for enc in candidates:
        key = (enc or "").lower()
        if not key or key in tried:
            continue
        tried.add(key)
        try:
            text = raw.decode(enc)
        except (LookupError, UnicodeDecodeError):
            continue
        # 解出来的中文如果几乎全是替换符，说明选错了
        if "\ufffd" not in text:
            return text
        # 记录一下，继续试下一个
        last = text
        break
    else:
        last = None

    if last is not None:
        return last
    return raw.decode(fallback, errors="replace")


def _looks_like_mojibake(text: str) -> bool:
    """粗判是否出现典型的 UTF-8 被当作 latin-1 解读后的乱码（如 "æ–°é—»"）。"""
    if not text:
        return False
    sample = text[:4000]
    weird = sum(1 for ch in sample if "\u00c0" <= ch <= "\u00ff")
    return weird / max(len(sample), 1) > 0.08


def repair_mojibake(text: str) -> str:
    """尽力把"UTF-8 字节被 latin-1 解码"造成的乱码还原回中文。"""
    if not _looks_like_mojibake(text):
        return text
    try:
        return text.encode("latin-1", errors="strict").decode("utf-8", errors="strict")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


# --------------------------------------------------------------------------
# 二、文本清洗
# --------------------------------------------------------------------------

# 零宽字符、BOM、软连字符等不可见字符
_ZERO_WIDTH_RE = re.compile("[\u200b\u200c\u200d\u200e\u200f\u2060\ufeff\u00ad\u180e]")
# 不间断空格、全角空格等统一成普通空格
_SPACE_MAP = {
    "\u00a0": " ", "\u3000": " ", "\u2002": " ", "\u2003": " ",
    "\u2009": " ", "\u2028": " ", "\u2029": " ", "\u000b": " ", "\u000c": " ",
}
_MULTI_SPACE_RE = re.compile(r"[ \t]{2,}")
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")


def clean_text(text: str) -> str:
    """单行清洗：去零宽字符、统一空白、去首尾空格。"""
    if not text:
        return ""
    text = _ZERO_WIDTH_RE.sub("", text)
    for src, dst in _SPACE_MAP.items():
        text = text.replace(src, dst)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _MULTI_SPACE_RE.sub(" ", text)
    return text.strip()


# 中文排版里不该出现空格的场景：
#   1) 两个汉字之间 —— "各 有关单位 ："
#   2) 汉字与中文标点之间 —— "有关单位 ："
#   3) 中文标点之后紧跟汉字 —— "。 各"
#   4) 汉字与数字之间 —— "进一步 2026 年"
# 这些空格多半是源站富文本编辑器的 <span> 切分留下的，去掉更利于正文阅读。
_CJK = r"\u4e00-\u9fa5\u3000-\u303f\uff00-\uffef"
_CJK_SPACE_RULES = [
    (re.compile(r"(?<=[%s])\s+(?=[%s])" % (_CJK, _CJK)), ""),
    (re.compile(r"(?<=[%s])\s+(?=[0-9A-Za-z])" % _CJK), ""),
    (re.compile(r"(?<=[0-9A-Za-z])\s+(?=[%s])" % _CJK), ""),
    # 阿拉伯数字内部被切开的空格："2026年9月1 8日" / "12 3 号"
    (re.compile(r"(?<=\d)\s+(?=\d)"), ""),
]


def tighten_cjk(text: str) -> str:
    """收紧中文排版：去掉汉字/中文标点/数字之间被富文本切分出来的多余空格。"""
    if not text:
        return ""
    previous = None
    while previous != text:
        previous = text
        for pattern, repl in _CJK_SPACE_RULES:
            text = pattern.sub(repl, text)
    return text


def clean_content(text: str) -> str:
    """正文清洗：按空行分段，段内合并空白，段落之间固定用 \\n\\n 分隔。"""
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    text = _ZERO_WIDTH_RE.sub("", text)
    for src, dst in _SPACE_MAP.items():
        text = text.replace(src, dst)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _MULTI_SPACE_RE.sub(" ", text)

    paragraphs = []
    for line in text.split("\n"):
        line = tighten_cjk(line.strip())
        if not line:
            continue
        paragraphs.append(line)
    return _MULTI_NEWLINE_RE.sub("\n\n", "\n\n".join(paragraphs)).strip()


def strip_html_fragment(raw_html: str) -> str:
    """把一段 HTML 片段转成纯文本（用于 RSS description）。"""
    if not raw_html:
        return ""
    text = html_lib.unescape(raw_html)
    if "<" in text and ">" in text:
        text = BeautifulSoup(text, "lxml").get_text("\n")
    return clean_content(text)


def is_noise_line(line: str) -> bool:
    """判断一行是不是导航/工具条/分享按钮之类的噪声。"""
    line = line.strip()
    if not line:
        return True
    if len(line) <= 2 and not re.search(r"[\u4e00-\u9fa5]{2}", line):
        return True
    for pattern in _NOISE_TEXT_PATTERNS:
        if pattern.search(line):
            return True
    # "大 中 小" 这类字号按钮
    if re.fullmatch(r"[大中小\s]{3,}", line):
        return True
    return False


# --------------------------------------------------------------------------
# 三、正文抽取
# --------------------------------------------------------------------------

def make_soup(html: str, is_xml: bool = False) -> BeautifulSoup:
    """统一用 lxml 解析；RSS 走 lxml-xml，页面走 lxml（容错更强）。"""
    parser = "lxml-xml" if is_xml else "lxml"
    try:
        return BeautifulSoup(html, parser)
    except Exception:
        return BeautifulSoup(html, "html.parser")


def prune_noise(soup: BeautifulSoup) -> None:
    """原地删除噪声节点。"""
    for selector in _NOISE_SELECTORS:
        try:
            for node in soup.select(selector):
                node.decompose()
        except Exception:
            continue
    # HTML 注释
    for node in soup.find_all(string=lambda s: isinstance(s, NavigableString) and "<!--" in str(s)):
        node.extract()


def _score_candidate(node: Tag) -> float:
    """给候选正文容器打分：段落文字越多分越高，链接密度越高分越低。"""
    paragraphs = [p for p in node.find_all("p") if isinstance(p, Tag)]
    para_text_len = 0
    for p in paragraphs:
        text = p.get_text(" ", strip=True)
        if len(text) >= 10:
            para_text_len += len(text)
    total_len = len(node.get_text(" ", strip=True))
    if total_len == 0:
        return 0.0

    link_len = sum(len(a.get_text(" ", strip=True)) for a in node.find_all("a"))
    link_density = link_len / total_len
    if link_density > 0.5:
        return 0.0

    score = para_text_len * 1.0 + total_len * 0.25 - link_len * 1.0
    class_id = " ".join(node.get("class") or []) + " " + (node.get("id") or "")
    if re.search(r"content|con|zoom|article|artical|wenzhang|detail|txt|text|editor|news", class_id, re.I):
        score += 250
    if re.search(r"nav|menu|crumb|foot|share|side|list|tj|ad|banner", class_id, re.I):
        score -= 400
    return score


def _paragraphs_from(node: Tag) -> list[str]:
    """从容器里按自然段取文字；没有 <p> 时按 <br> 切分。"""
    paragraphs: list[str] = []

    if node.find("p"):
        for p in node.find_all("p"):
            line = clean_text(p.get_text(" ", strip=True))
            if line and not is_noise_line(line):
                paragraphs.append(line)
    else:
        # 有些正文是一整块纯文本 + <br> 换行
        chunks = re.split(r"(?i)<br\s*/?>", node.decode_contents())
        for chunk in chunks:
            line = clean_text(BeautifulSoup(chunk, "lxml").get_text(" ", strip=True))
            if line and not is_noise_line(line):
                paragraphs.append(line)

    # 合并"孤立的标题行"造成的碎片：过短且不以标点结尾的行与前一行拼接
    merged: list[str] = []
    for line in paragraphs:
        if merged and len(line) <= 8 and not re.search(r"[。！？；：.!?;:]$", merged[-1]):
            merged[-1] = merged[-1] + line
        else:
            merged.append(line)
    return merged


def extract_content(html: str, prefer_selectors=None) -> tuple[str, Tag | None]:
    """从详情页 HTML 里抽正文。

    返回 (正文纯文本, 命中的容器节点)。正文自然段之间用 \\n\\n 分隔。
    抽取优先级：站点指定选择器 → 通用打分。
    """
    if not html:
        return "", None
    soup = make_soup(html)
    body = soup.body or soup
    prune_noise(body if isinstance(body, Tag) else soup)

    # 1) 站点指定选择器
    for selector in (prefer_selectors or []):
        try:
            node = soup.select_one(selector)
        except Exception:
            node = None
        if node is None:
            continue
        paragraphs = _paragraphs_from(node)
        text = clean_content("\n".join(paragraphs))
        if len(text) >= 80:
            return text, node

    # 2) 通用打分
    best_node, best_score = None, 0.0
    for node in soup.find_all(["div", "article", "section", "td"]):
        if not isinstance(node, Tag):
            continue
        # 跳过明显是外壳的大容器（正文不会把整个 body 包进去还能得高分）
        score = _score_candidate(node)
        if score > best_score:
            best_node, best_score = node, score

    if best_node is not None:
        paragraphs = _paragraphs_from(best_node)
        text = clean_content("\n".join(paragraphs))
        if text:
            return text, best_node

    # 3) 实在抽不出来就把全文当正文（下游会因长度不足而判定失败）
    fallback = clean_content((soup.body or soup).get_text("\n"))
    return fallback, None


# --------------------------------------------------------------------------
# 四、时间 / 字段解析
# --------------------------------------------------------------------------

_DATE_PATTERNS = [
    # 2026-10-04 01:39:11.0 / 2026-10-04 01:39:11 / 2026-10-04 01:39
    (re.compile(r"(\d{4})[-/年.](\d{1,2})[-/月.](\d{1,2})日?\s*(\d{1,2}):(\d{2})(?::(\d{2}))?"),
     "ymdhms"),
    # 2026-10-04
    (re.compile(r"(\d{4})[-/年.](\d{1,2})[-/月.](\d{1,2})日?"), "ymd"),
    # 10-04（无年份）
    (re.compile(r"(?<!\d)(\d{1,2})[-/月.](\d{1,2})日?(?!\d)"), "md"),
]


def normalize_time(raw: str, now: datetime | None = None) -> str:
    """把各种写法的日期归一化成 'YYYY-MM-DD HH:MM:SS'。

    - 带年份的直接采用；
    - 只有 "10-04" 的（政府列表页常见）按"不超过今天"补全年份：
      若该月日 > 今天，则认为是去年的。
    """
    now = now or datetime.now()
    text = clean_text(raw or "")
    if not text:
        return ""

    # 先尝试标准解析（RSS 的 "2026-10-04 01:39:11.0" 也能被 fromisoformat 处理）
    candidate = text.replace("/", "-").replace("年", "-").replace("月", "-").replace("日", " ")
    candidate = re.sub(r"\.\d+$", "", candidate.strip())
    try:
        return datetime.fromisoformat(candidate).strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        pass

    for pattern, kind in _DATE_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        groups = match.groups()
        try:
            if kind == "ymdhms":
                year, month, day, hour, minute = (int(groups[i]) for i in range(5))
                second = int(groups[5]) if groups[5] else 0
            elif kind == "ymd":
                year, month, day = (int(groups[i]) for i in range(3))
                hour = minute = second = 0
            else:
                year = None
                month, day = int(groups[0]), int(groups[1])
                hour = minute = second = 0
        except (TypeError, ValueError):
            continue

        if not (1 <= month <= 12 and 1 <= day <= 31):
            continue
        if not (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
            hour = minute = second = 0

        if year is None:
            # "不超过今天"：先按今年算，若还没到就退一年
            year = now.year
            try:
                stamp = datetime(year, month, day, hour, minute, second)
            except ValueError:
                continue
            if stamp > now + timedelta(days=1):
                year -= 1
        try:
            return datetime(year, month, day, hour, minute, second).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    return ""


def parse_publish_meta(text: str) -> dict:
    """从详情页的 "发布日期：… 来源：… 作者：…" 一行里抽出三个字段。"""
    result = {"publish_time": "", "origin": "", "author": ""}
    if not text:
        return result
    flat = clean_text(text)

    time_match = re.search(
        r"(?:发布日期|发布时间|发布于|时间)\s*[:：]\s*([0-9]{4}[-/年][0-9]{1,2}[-/月][0-9]{1,2}日?"
        r"(?:\s*[0-9]{1,2}:[0-9]{2}(?::[0-9]{2})?)?)",
        flat,
    )
    if time_match:
        result["publish_time"] = normalize_time(time_match.group(1))

    origin_match = re.search(r"(?:信息来源|来源|稿源|发布机构)\s*[:：]\s*([^ \t　|｜]{1,40}?)(?=\s|$|作者|责任|浏览|阅读|字体|【|$)", flat)
    if origin_match:
        result["origin"] = clean_text(origin_match.group(1))

    author_match = re.search(r"(?:作者|责任编辑|编辑)\s*[:：]\s*([^ \t　|｜]{1,30}?)(?=\s|$|浏览|阅读|字体|来源|【|$)", flat)
    if author_match:
        result["author"] = clean_text(author_match.group(1))
    return result


# --------------------------------------------------------------------------
# 五、URL / 图片处理
# --------------------------------------------------------------------------

# 这些明显不是新闻详情页的路径
_JUNK_URL_RE = re.compile(
    r"(javascript:|mailto:|^#$|/search|/login|/register|/rss/|\.(?:pdf|doc|docx|xls|xlsx|zip|rar|mp4|mp3)$)",
    re.I,
)
_IMAGE_EXT_RE = re.compile(r"\.(?:jpg|jpeg|png|gif|webp|bmp)(?:\?|$)", re.I)
# 常见的站点 logo / 图标 / 占位图 / 附件图标，不能当封面
_BAD_IMAGE_RE = re.compile(
    r"(logo|icon|ico_|sprite|blank|placeholder|spacer|pixel|1x1|qrcode|weixin|weibo|share"
    r"|/assets/|/_res/|\.\./|/t/\d+/\d+/img/|/statics?/|/images?/(?:btn|nav|bg|sheng|print|pdf))",
    re.I,
)


def normalize_url(href: str, base: str) -> str:
    """相对链接转绝对，去掉 fragment 与无意义查询串（便于后端按 source_url 幂等去重）。"""
    if not href:
        return ""
    href = clean_text(href)
    if _JUNK_URL_RE.search(href):
        return ""
    absolute = urljoin(base, href)
    parts = urlparse(absolute)
    if parts.scheme not in ("http", "https"):
        return ""
    # 查询串一律丢弃：这些站点的详情页地址都是纯路径
    return urlunparse((parts.scheme, parts.netloc, parts.path, "", "", ""))


def normalize_image(src: str, base: str) -> str:
    """封面图地址归一化；过滤 logo/图标/占位图以及非图片资源。"""
    if not src:
        return ""
    src = clean_text(src)
    if src.startswith("data:") or _BAD_IMAGE_RE.search(src):
        return ""
    absolute = urljoin(base, src)
    parts = urlparse(absolute)
    if parts.scheme not in ("http", "https"):
        return ""
    if not _IMAGE_EXT_RE.search(parts.path):
        return ""
    return urlunparse((parts.scheme, parts.netloc, parts.path, "", parts.query, ""))


def same_section(url: str, list_url: str) -> bool:
    """判断详情链接是否和列表页在同一个栏目路径下。

    政府列表页里常混入"网络举报""媒体社会责任报告"之类的站内固定链接，
    以及完全不同的频道；用栏目前缀可以干净地过滤掉。
    """
    if not url or not list_url:
        return True
    target, base = urlparse(url), urlparse(list_url)
    if target.netloc != base.netloc:
        # 列表页允许指向兄弟站点（如 kjj 列表混入 cczx.wuhu.gov.cn），只要同属主域
        target_root = ".".join(target.netloc.split(".")[-3:])
        base_root = ".".join(base.netloc.split(".")[-3:])
        if not (target_root.endswith("wuhu.gov.cn") and base_root.endswith("wuhu.gov.cn")):
            return False
    prefix = base.path
    # /gg/tzgg/index.html -> /gg/tzgg/
    prefix = prefix[: prefix.rfind("/") + 1]
    if not prefix or prefix == "/":
        return True
    return target.path.startswith(prefix) or target.path.startswith(prefix.rstrip("/"))


def pick_cover_image(soup: BeautifulSoup, page_url: str, content_node: Tag | None = None) -> str:
    """挑封面图：og:image / 正文第一张图 → 站点容器都是页脚/附件时返回空。

    注意：正文之外的 img（站点 logo、附件 pdf 图标）必须排除，
    否则会出现"封面图是 pdf.gif"这种尴尬结果。
    """
    # 1) 页面 meta 里声明的分享图
    for selector, attr in (
        ('meta[property="og:image"]', "content"),
        ('meta[name="og:image"]', "content"),
        ('meta[name="twitter:image"]', "content"),
        ('meta[itemprop="image"]', "content"),
    ):
        node = soup.select_one(selector)
        if node and node.get(attr):
            image = normalize_image(node.get(attr), page_url)
            if image:
                return image

    # 2) 正文容器（优先）或页面主体里的第一张图
    scopes = []
    if content_node is not None:
        scopes.append(content_node)
    body = soup.body or soup
    scopes.append(body)
    for scope in scopes:
        for img in scope.find_all("img"):
            # 附件链接里的图标不是封面
            anchor = img.find_parent("a")
            if anchor is not None and re.search(r"\.(?:pdf|doc|docx|xls|xlsx|zip|rar)(?:\?|$)",
                                               anchor.get("href") or "", re.I):
                continue
            for attr in ("src", "data-src", "data-original", "data-echo"):
                image = normalize_image(img.get(attr) or "", page_url)
                if image:
                    return image
    return ""
