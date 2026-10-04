# 芜湖市科技创新新闻采集器（crawler）

课程作业项目 —— 多源新闻采集端。抓取"芜湖市科技创新"相关新闻的
**标题 + 正文 + 来源 + 发布时间 + 封面图**，通过 HTTP API 推送到后端入库。

- 后端接口契约：`../docs/api.md` 的「二、采集端」
- 后端地址：`http://127.0.0.1:9533`，鉴权 Header `X-Ingest-Token: wuhu-ingest-2026`
- 技术栈：`requests` + `BeautifulSoup(lxml)` + `tenacity`（**不使用 Selenium**）

---

## 一、快速开始

```bash
cd crawler
pip install -r requirements.txt

# 1) 只看抓取与解析结果，不访问后端（后端没启动也能跑）
python run.py --dry-run --source-id 1 --limit 3

# 2) 正式采集（抓取 + 推送入库 + 回写日志）
python run.py

# 3) 查看后端配置了哪些采集源
python run.py --list-sources
```

## 二、命令行参数

| 参数 | 说明 |
|---|---|
| （无参数） | 抓取后端返回的**全部启用源** |
| `--source-id 1` | 只抓指定源；多个用逗号分隔，如 `--source-id 1,5` |
| `--limit N` | 每个源最多处理 N 条 |
| `--dry-run` | **不访问后端**，只抓取并打印解析结果（标题/来源/时间/正文长度/前 120 字） |
| `--no-content` | 只抓列表标题，不进入详情页抓正文（速度快，用于快速验证列表结构） |
| `--list-sources` | 打印后端返回的采集源列表；后端未启动时给出友好提示并显示本地兜底源 |
| `--max-pages N` | 覆盖源配置的 `max_pages`（对不支持翻页的适配器无效，会提示） |
| `--delay 秒` | 覆盖请求间隔下限，便于课堂演示加速（默认随机 0.8~1.8s） |
| `--verbose` | 打印异常堆栈，便于排查站点结构变化 |

退出码：`0` 正常；`1` 所有源都失败（部分源失败不影响整体，仍返回 0）。

## 三、目录结构

```
crawler/
├── config.py        # 后端地址、ingest token、UA、超时、限速、重试、离线兜底源
├── adapters.py      # 4 类适配器：列表解析 + 详情解析 + 限速重试 HTTP 客户端
├── extract.py       # 编码处理、正文抽取、文本清洗、时间归一化、URL/图片归一化
├── store.py         # 后端 API 调用（sources / news / log / touch）
├── run.py           # 主流程 + CLI + 日志
├── requirements.txt # 依赖
├── logs/            # 运行日志 run-YYYYmmdd-HHMMSS.log
└── README.md
```

数据流：

```
GET /api/ingest/sources
        ↓  每个源
列表页 → 条目解析 → 本次运行内按 source_url 去重 → 详情页抓正文
        ↓
标题/正文关键词过滤 → 正文长度校验（< 80 字视为失败）
        ↓
POST /api/ingest/news（批量，按 source_url 幂等） → POST /api/ingest/log → POST /api/ingest/source/{id}/touch
```

## 四、四类采集源说明（均为 2026-10 实测结构）

### 1. `wuhu_kjj_list` —— 芜湖市科技局列表页

- 列表页：`https://kjj.wuhu.gov.cn/gg/tzgg/index.html`（另有 `/gg/gzdt/`、`/gg/kjyw/`、`/gg/xqkj/`）
- 服务端直出 HTML，单页 20 条；列表项形如：

  ```html
  <li class="odd">
    <a class="left" href="https://kjj.wuhu.gov.cn/gg/tzgg/8959644.html" title="……通知">
      <span>……通知</span></a>
    <span class="right date">2026-09-29</span>
  </li>
  ```

- 标题优先取 `a[title]` 属性（不受内部 `<span>` 影响）；
- **分页是 JS 渲染的**：实测 `index_1.html`、`index_2.html` 均返回 **HTTP 404**，
  因此该适配器**只抓第 1 页**，`max_pages` 对它无效（run.py 会打印提示）；
- 列表里可能混入兄弟站点域名（如 `cczx.wuhu.gov.cn`），正常抓取即可（同属 `wuhu.gov.cn`）；
- 详情页：`h1` 是标题，正文容器 `div.newscontnet`；
  `<meta name="PubDate" content="2026-09-29 14:46">`、
  `<meta name="ContentSource" content="芜湖市科技局">` 是**最可靠**的来源/时间字段，
  页面上的"发布日期：… 来源：… 作者：…"文本作为兜底。

### 2. `wuhu_gov_rss` —— 芜湖市政府 RSS

- 地址：`https://www.wuhu.gov.cn/rss/rss.xml?siteId=6787231`
- 标准 RSS 2.0，必须用 **XML 解析器**（用 HTML 解析器会把 `<item>` 丢掉）：

  ```xml
  <item>
    <title><![CDATA[ 陈东调研数字经济发展工作 ]]></title>
    <link>https://www.wuhu.gov.cn/xwzx/zwyw/41350150.html</link>
    <pubDate>2026-10-04 01:39:11.0</pubDate>
    <description><![CDATA[ 摘要…… ]]></description>
  </item>
  ```

- `description` 自带摘要，作为 `content` 兜底；能抓到详情页正文时以正文为准；
- RSS 里混有**英文版**稿件（`WuhuEnglish/LocalNews/...`），按"中文占比"过滤掉；
- 一次返回全部条目，没有分页。

### 3. `wuhu_gov_list` —— 芜湖市政府新闻中心列表

- 列表页：`https://www.wuhu.gov.cn/xwzx/zwyw/index.html`（另有 `/xwzx/bmdt/`）
- 列表项结构与科技局一致（`a.left[title]` + `span.right.date`）。
  设计上按"列表日期可能只有 `10-04`"处理：`extract.normalize_time` 会按
  **"不超过今天"** 的规则补全年份（若该月日还没到，则算去年的）。
  *实测 2026-10 该站列表日期已带年份，补年逻辑作为兼容保留。*
- 分页同样实测 404（`index_1.html`），只抓第 1 页；
- 详情页正文容器 `div.wzcon`；元信息在 `div.wzfbxx`：
  `发布时间：2026-10-04 01:39` + `信息来源：芜湖市人民政府发布`。

### 4. `wuhunews_list` —— 芜湖新闻网

- 列表页：`https://www.wuhunews.cn/yaowen/`、`https://www.wuhunews.cn/djzx/`
- 列表项：

  ```html
  <li><a class="itb-title" href="https://www.wuhunews.cn/yaowen/2026-10-01/669171.html">
        <h3>“五新”二坝  智启新程</h3></a>
      <small><time>2026-10-01 02:03</time></small></li>
  ```

- **支持翻页**：`?pp=10`、`?pp=20` …（每页 10 条），按 `max_pages` 抓取；
  实测部分栏目的 `?pp=` 不生效（返回与第 1 页完全相同的 10 条），
  程序检测到"该页无新增 URL"会**自动停止翻页**，避免重复请求与重复计数；
- 列表页混有"网络举报""媒体社会责任报告"等站内固定链接，
  用**栏目前缀匹配**（详情链接必须落在 `/yaowen/` 下）过滤；
- 详情页正文容器 `div.article-content`；发布时间取页面上
  `div.time` / `<time>` 里的 `2026-10-01 02:03`，URL 路径里的日期作最后兜底；
  该站详情页没有"来源："标签，`origin` 统一记为"芜湖新闻网"。

## 五、几个关键实现点（答辩讲解用）

### 1. 编码处理（踩坑最多的地方）

政府站点各页 charset 不统一，实测 **`kjj.wuhu.gov.cn` 与 `www.wuhu.gov.cn` 的
HTTP 响应头都谎报 `ISO-8859-1`，而页面 meta 里写的是 `utf-8`**。
如果直接用 `response.text`，中文会全部变成乱码。

`extract.decode_response()` 的判定顺序：

1. 文档内部声明（`<meta charset>` / `<meta http-equiv>` / XML declaration）—— 最权威；
2. BOM（`utf-8-sig` / `utf-16`）；
3. HTTP 头 charset —— 但 `iso-8859-1`/`latin-1`/`ascii` 视为"占位值"降级到最后；
4. `requests` 的 `apparent_encoding`（统计猜测）；
5. 兜底 `utf-8` + `errors='replace'`。

落库前统一 UTF-8 纯文本，并清除零宽字符（`\u200b` 等）、BOM、不间断空格，
段落之间固定 `\n\n`。

### 2. 正文抽取

`extract.extract_content()` 两级策略：

1. **站点指定选择器**（每个适配器各带一组，如 `div.newscontnet`、`div.wzcon`、`div.article-content`）；
2. **通用打分兜底**：遍历 `div/article/section/td`，按「段落文字长度 + 总长度 − 链接文字长度」
   打分，class/id 命中 `content|article|zoom|wenzhang|detail` 加分、命中
   `nav|menu|crumb|foot|share|side` 减分；链接密度 > 50% 直接判 0 分。

抽取前先删除导航、面包屑、页脚、推荐位、分享按钮、二维码、字号按钮、附件区等噪声节点；
正文长度 < **80 字**视为抽取失败 → 用列表/RSS 摘要兜底，仍不足则本条不推送（计入 `filtered`）。

### 3. 关键词过滤

源上 `keyword_filter` 为逗号分隔字符串时，**标题或正文命中任一关键词**才推送；
未配置（`null`）则不过滤。统计进 `filtered`。

> 实现细节：先抓正文再过滤。只看标题就过滤会漏掉"标题平淡、正文讲科技创新"的稿件。

### 4. 限速与礼貌

- 单线程顺序抓取，每次请求之间随机 `0.8~1.8s`（`config.DELAY_MIN/DELAY_MAX`）；
- 单次请求超时 20s；失败重试 3 次，指数退避（1.5s → 3s → 6s，上限 30s）；
- 5xx / 429 也当作可重试错误；
- 固定 Chrome UA，并带 `Accept-Language: zh-CN`；
- **不抓附件 PDF**（列表解析阶段就只接受详情页链接，封面图过滤 `pdf.gif` 之类图标）。

### 5. 去重

- **本次运行内**：按 `source_url` 去重（`normalize_url` 会去掉 `#fragment` 与查询串，
  保证同一篇文章只处理一次）；
- **跨运行幂等**：交给后端 —— `source_url` 是唯一键，后端返回的
  `inserted` / `duplicated` 会打印到控制台并写入采集日志。

### 6. 容错

- 单源异常不影响其它源（`crawl_source` 内部捕获所有异常，写入该源的 `status=0` + `message`）；
- 后端未启动时 `--dry-run` 仍可独立工作：源列表自动降级为 `config.FALLBACK_SOURCES`；
- 后端一旦恢复，下一次 HTTP 请求正常发出（不会被历史失败状态卡死）。

## 六、日志

- 控制台输出带颜色（重定向到文件时自动关闭颜色）；
- 同时写入 `crawler/logs/run-YYYYmmdd-HHMMSS.log`（UTF-8）；
- 每次运行结束打印汇总表：`条目 / 解析 / 过滤 / 新增 / 重复`，以及耗时与 HTTP 请求数。

## 七、推送字段与接口契约

`POST /api/ingest/news`，JSON 数组，元素严格按 `docs/api.md`：

```json
[{
  "title": "关于转发《关于进一步做好2026年度首批省科技创新券兑付相关工作的提示》的通知",
  "source_url": "https://kjj.wuhu.gov.cn/gg/tzgg/8959644.html",
  "content": "各县市区、开发区科技管理部门，……",
  "photo_url": "",
  "origin": "芜湖市科技局",
  "publish_time": "2026-09-29 14:46:00",
  "category_code": "notice"
}]
```

其余接口：`POST /api/ingest/log`（单源采集日志）、
`POST /api/ingest/source/{id}/touch`（更新 `last_crawl_time`）。
批量推送按 `config.BATCH_SIZE`（默认 30 条）切片，避免单次请求过大。

## 八、合规说明（重要）

本项目仅用于**课程作业与技术学习**，采集行为遵循以下原则：

1. **只抓公开信息**：仅采集政府/媒体网站的公开新闻页面，
   只保存**标题、正文、来源、原文链接、发布时间、封面图地址**六项；
2. **保守限速**：单线程 + 请求间隔 0.8~1.8s，远低于给站点造成压力的阈值；
   不做并发抓取、不做全站遍历，每个源默认只取列表前 1 页；
3. **不做绕过**：不破解验证码、不伪造登录态、不绕过任何访问控制；
   遇到 4xx/5xx 只做有限次退避重试后放弃；
4. **不修改站点数据**：全部使用 `GET` 请求，只读取不写入；
5. **尊重版权**：正文仅用于本地课程演示与检索，**不二次发布、不商用**；
   转载/引用请以原始链接为准（`source_url` 字段保留了原文地址）；
6. **保留来源标识**：`origin` 字段始终记录原始发布单位，便于溯源。

如站点方要求停止采集，删除对应采集源配置即可。
