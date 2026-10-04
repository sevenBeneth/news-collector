# 接口契约（v1）

后端：Spring Boot 2.1.8 / Java 8，端口 **9533**，上下文路径无前缀。
统一响应体：

```json
{ "code": 0, "msg": "SUCCESS!", "data": {} }
```

| code | 含义 |
|---|---|
| 0 | 成功 |
| 1 | 服务器异常 |
| 1000 | 请先登录（token 缺失或失效） |
| 1003 | 用户不存在 |
| 1004 | 密码错误 |
| 1002 | 用户已存在 |

请求约定：表单参数用 `application/x-www-form-urlencoded`（`?a=1&b=2` 或表单体均可）；
需要登录的接口在 Header 带 `token: <JWT>`，另有 `platform: h5`（仅日志用）。

---

## 一、用户端 `/api/**`

| 接口 | 参数 | 说明 |
|---|---|---|
| `POST /api/banner` | 无 | 首页轮播，返回启用中的 banner 列表（按 sort） |
| `POST /api/getCategory` | 无 | 频道列表（enable=1） |
| `POST /api/getIndex` | `category_id?` `keyword?` `page_index` `page_size` | 新闻分页列表 |
| `POST /api/detail` | `id` `page_size` | 新闻详情（含 AI 摘要、评论首页） |
| `POST /api/comment` | `news_id` `page_index` `page_size` | 一级评论分页 |
| `POST /api/commentDetail` | `id` `page_index` `page_size` | 单条评论 + 其回复分页 |
| `POST /api/addComment` | `news_id` `content` `page_size` 🔒 | 发表评论 |
| `POST /api/addReply` | `comment_id` `pid` `content` `page_size` 🔒 | 回复评论 |
| `POST /api/favorite` | `news_id` 🔒 | 收藏/取消收藏，返回 0 |
| `POST /api/like` | `news_id` 🔒 | 点赞/取消点赞，返回 0 |
| `POST /api/commentLike` | `comment_id` 🔒 | 评论点赞/取消，返回 0 |
| `POST /api/favoriteList` | `page_index` `page_size` 🔒 | 我的收藏 |
| `POST /api/login` | `mobile` `password` | 登录，返回 `{user_id,nickname,mobile,avatar_url,token}` |
| `POST /api/register` | `mobile` `nickname` `password` | 注册（演示级：无短信验证码），直接返回登录态 |
| `POST /api/userInfo` | 🔒 | 用户资料（手机号中间四位打码） |
| `POST /api/userIndex` | 🔒 | 等同 userInfo |
| `POST /api/logout` | 🔒 | 退出（前端清 token 即可，后端返回 0） |
| `POST /api/feedback` | `content` | 意见反馈（演示：写入日志并返回 0） |

**`/api/getIndex` 响应示例**

```json
{
  "code": 0,
  "data": {
    "count": 128, "page": 13,
    "list": [{
      "id": 12,
      "title": "芜湖市启动2026年度高新技术企业认定申报工作",
      "photo_url": "https://.../a.jpg",
      "origin": "芜湖市科技局",
      "publish_time": "2026-05-01 10:00:00",
      "ai_summary": "芜湖市启动2026年度高新技术企业认定申报……",
      "ai_keywords": "高新技术企业,认定申报",
      "read_count": 96, "comment_count": 0, "category_id": 1, "category_name": "科技政策"
    }],
    "slider": [ { "id": 3, "title": "...", "image_url": "...", "news_id": 12, "link_url": null } ]
  }
}
```

> `slider` 为首页轮播数据（banner 表），与 `banner` 接口数据一致，前端二选一使用即可。

**`/api/detail` 响应示例**

```json
{
  "code": 0,
  "data": {
    "id": 12, "title": "...", "content": "<p>正文…</p>",
    "origin": "芜湖市科技局", "source_url": "https://kjj.wuhu.gov.cn/...",
    "publish_time": "2026-05-01 10:00:00", "read_count": 97,
    "ai_summary": "…", "ai_keywords": "a,b,c", "ai_status": 1,
    "like_count": 2, "comment_count": 0,
    "is_like": 0, "is_favorite": 0,
    "comment": { "count": 0, "page": 0, "list": [] }
  }
}
```

---

## 二、采集端 `/api/ingest/**`（Python 爬虫调用）

鉴权：Header `X-Ingest-Token: <配置中的 ingest-token>`（默认 `wuhu-ingest-2026`）。

| 接口 | 说明 |
|---|---|
| `GET /api/ingest/sources` | 返回启用中的采集源列表（id,name,adapter,list_url,default_category_code,keyword_filter,max_pages） |
| `POST /api/ingest/news` | 批量入库，JSON 数组，按 `source_url` 幂等 |
| `POST /api/ingest/log` | 回写单次采集日志 |
| `POST /api/ingest/source/{id}/touch` | 更新该源 last_crawl_time |

**`POST /api/ingest/news` 请求体**

```json
[
  {
    "title": "标题",
    "source_url": "https://kjj.wuhu.gov.cn/gg/tzgg/8959644.html",
    "content": "正文纯文本",
    "photo_url": "https://.../cover.jpg",
    "origin": "芜湖市科技局",
    "publish_time": "2026-09-29 14:46:00",
    "category_code": "notice"
  }
]
```

响应：`{"code":0,"data":{"total":10,"inserted":8,"duplicated":2,"filtered":0}}`

**`POST /api/ingest/log` 请求体**

```json
{"source_id":1,"source_name":"芜湖市科技局-通知公告","total":20,"inserted":18,
 "duplicated":2,"filtered":0,"status":1,"message":"ok","duration_ms":3200}
```

---

## 三、管理端 `/admin/api/**`（内置静态页调用）

登录：`POST /admin/api/login?mobile=13800000001&password=admin123` → `{"code":0,"data":{"token":"...","nickname":"管理员"}}`
后续请求 Header：`X-Admin-Token: <token>`（JWT，需 `role=1`）。

| 接口 | 参数 | 说明 |
|---|---|---|
| `GET /admin/api/stats` | 无 | 看板统计 |
| `GET /admin/api/news` | `status?` `category_id?` `keyword?` `ai_status?` `page_index` `page_size` | 新闻分页 |
| `GET /admin/api/news/{id}` | 路径参数 | 新闻详情 |
| `POST /admin/api/news/save` | `id?` `title` `content` `category_id` `origin` `photo_url` `slider` `status` | 新增/编辑 |
| `POST /admin/api/news/audit` | `id` `status`（1通过 2驳回） | 审核 |
| `POST /admin/api/news/batchAudit` | `ids`（逗号分隔） `status` | 批量审核 |
| `POST /admin/api/news/delete` | `id` | 删除 |
| `GET /admin/api/banner` | 无 | 轮播列表 |
| `POST /admin/api/banner/save` | `id?` `title` `image_url` `link_url` `news_id` `sort` `enable` | 新增/编辑 |
| `POST /admin/api/banner/delete` | `id` | 删除 |
| `GET /admin/api/source` | 无 | 采集源列表（含 last_crawl_time） |
| `POST /admin/api/source/save` | `id?` `name` `adapter` `list_url` `default_category_code` `keyword_filter` `max_pages` `enable` `sort` `remark` | 新增/编辑 |
| `POST /admin/api/source/delete` | `id` | 删除 |
| `GET /admin/api/crawl/logs` | `page_index` `page_size` | 采集日志分页 |
| `POST /admin/api/ai/backfill` | `limit`（默认 5） | 批量补齐 AI 摘要，返回处理条数 |
| `POST /admin/api/ai/regenerate` | `id` | 重新生成某条摘要 |
| `GET /admin/api/user` | `keyword?` `page_index` `page_size` | 用户列表 |
| `POST /admin/api/user/enable` | `id` `enable` | 启用/禁用 |
| `GET /admin/api/category` | 无 | 频道列表 |

**`GET /admin/api/stats` 响应**

```json
{
  "code": 0,
  "data": {
    "newsTotal": 320, "pending": 12, "published": 300, "rejected": 8,
    "aiDone": 280, "aiFailed": 5, "todayInserted": 96,
    "sourceCount": 9, "userCount": 6, "commentCount": 14,
    "categoryDist": [{"name":"科技政策","count":80}]
  }
}
```
