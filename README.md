# 芜湖市科技创新新闻收集平台

> 课程作业项目：面向芜湖本地的**科技创新资讯聚合 + AI 摘要**小程序/H5 平台
> 采集芜湖市政府、市科技局、芜湖新闻网等官方渠道，DeepSeek 大模型自动生成摘要与关键词，内置管理端审核发布。

---

## 一、选题与价值

| 项目 | 说明 |
|---|---|
| **目标用户** | 芜湖本地科技型企业从业者（政策申报）、高校师生与科研人员、科技管理部门、招商与产业园区人员 |
| **解决的问题** | 科技政策与企业动态分散在政府网站、部门频道、地方媒体，人工收集耗时；政策时效性强、容易错过申报窗口；单篇资讯篇幅长、阅读成本高 |
| **业务创新** | 本地化"科技信息一站式聚合"：多源自动采集 → AI 30 秒速读 → 频道化归档 → 收藏/评论互动 → 后台审核发布 |
| **技术创新** | 多源采集 + 双键去重（原文链接 + 标题哈希）；大模型结构化摘要（摘要/关键词/频道/重要度）；失败自动降级为抽取式摘要；无状态 JWT 鉴权；采集端与管理端独立令牌 |

---

## 二、技术栈与架构

```
┌────────────────────────── 前端（uni-app / Vue2）──────────────────────────┐
│  H5（HBuilderX dev-server，8080） · 可编译微信小程序（mp-weixin）          │
│  页面：首页(轮播+频道+信息流) 频道 搜索 详情(AI摘要) 评论 收藏 我的 登录注册 │
│  自研组件：banner-swiper · ai-summary-card · keyword-tags                  │
│  复用组件：Parser(富文本) mescroll(上拉加载) uni-ui(卡片/弹窗/图标/抽屉…)   │
└───────────────────────────────┬───────────────────────────────────────────┘
                                │ HTTP + JSON（localhost 任意端口放行跨域）
┌───────────────────────────────▼───────────────────────────────────────────┐
│                     后端 api-server（Spring Boot 2.1.8 / Java 8）          │
│  /api/**          用户端：频道/列表/详情/评论/点赞/收藏/登录注册            │
│  /api/ingest/**   采集端：批量入库(幂等)、采集日志、源配置（X-Ingest-Token）│
│  /admin/api/**    管理端：看板/新闻审核发布/轮播/采集源/日志/用户           │
│  /admin/index.html 内置静态管理页（单文件、零外部依赖）                     │
│  MyBatis + 通用Mapper + PageHelper ｜ 无状态 JWT ｜ 异步线程池生成摘要      │
└──────────┬────────────────────────────────────────────┬───────────────────┘
           │                                            │
┌──────────▼──────────┐                    ┌────────────▼────────────────────┐
│  MySQL 8.0          │                    │  DeepSeek API（第三方大模型）    │
│  news_collector 库  │                    │  /chat/completions              │
│  9 张表             │                    │  deepseek-chat · JSON 结构化输出 │
└──────────▲──────────┘                    └─────────────────────────────────┘
           │ HTTP 入库（X-Ingest-Token）
┌──────────┴────────────────────────────────────────────────────────────────┐
│              采集器 crawler（Python 3.11 + requests + BeautifulSoup）      │
│  adapter：wuhu_kjj_list · wuhu_gov_rss · wuhu_gov_list · wuhunews_list     │
│  正文抽取 · 编码归一 · 关键词过滤 · 限速重试 · 去重 · 日志                 │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## 三、目录结构

```
news-collector/
├── api-server/                      # 后端（Spring Boot）
│   ├── src/main/java/com/wuhu/news/
│   │   ├── NewsCollectorApplication.java   启动类
│   │   ├── config/                跨域过滤器、异步线程池、Swagger
│   │   ├── controller/            ApiController / IngestController / AdminApiController
│   │   ├── entity/                9 个实体 + 统一返回体
│   │   ├── mapper/                MyBatis Mapper
│   │   ├── service/               业务 / AI摘要 / 采集入库 / 管理端 / 启动初始化
│   │   ├── utils/                 JWT、MD5、敏感词、鉴权工具
│   │   └── vo/                    列表/详情/评论/统计等出参对象
│   └── src/main/resources/
│       ├── application.yml        端口、数据源、采集令牌、DeepSeek 配置
│       ├── mapper/*.xml           NewsMapper / CommentMapper 动态 SQL
│       ├── static/admin/index.html 内置管理端页面
│       └── words.txt              敏感词库（评论校验）
├── crawler/                         # 采集器（Python）
│   ├── config.py  adapters.py  extract.py  store.py  run.py
│   ├── requirements.txt
│   └── README.md
├── web/                             # 前端（uni-app）
│   ├── config/api.js               接口地址（唯一需要改的文件）
│   ├── pages/                      页面
│   ├── components/                 组件（含 3 个自研组件）
│   └── manifest.json               H5 / 小程序配置
├── sql/
│   ├── 00_reset.sql                清库（可选）
│   ├── 01_schema.sql               建表（幂等）
│   └── 02_seed.sql                 频道 / 采集源 / 演示数据 / Banner
├── docs/
│   ├── api.md                      接口契约
│   ├── 信息架构.md                 产品信息架构（思维导图版）
│   ├── 录屏脚本.md                 演示视频脚本
│   └── 插件与来源说明.md           插件来源 + 编写比例
├── tools/mvn-settings.xml          本机 Maven 配置修正
└── README.md
```

---

## 四、快速开始（4 步）

### 1. 数据库

```bash
mysql -uroot -p123456 --default-character-set=utf8mb4 -e "source D:/news-collector/sql/01_schema.sql"
mysql -uroot -p123456 --default-character-set=utf8mb4 -e "source D:/news-collector/sql/02_seed.sql"
```

> 注意必须带 `--default-character-set=utf8mb4`，否则中文会二次编码变成乱码。

### 2. 后端

**先创建本地私有配置**（仓库中不含任何密钥）：

```bash
# api-server/src/main/resources/application-local.yml
spring:
  datasource:
    username: root
    password: 你的MySQL密码
ai:
  deepseek:
    key: sk-你的DeepSeek密钥
```

> `application.yml` 已配置 `spring.profiles.active=local`，会自动加载该文件；
> 也可不改文件，改用环境变量 `DB_USER` / `DB_PASSWORD` / `DEEPSEEK_API_KEY`。
> `application-local.yml` 已在 `.gitignore` 中，不会被提交。

```bash
cd D:/news-collector/api-server
mvn -s ../tools/mvn-settings.xml -DskipTests clean package
java -jar target/news-collector-1.0.jar
```

启动后：

| 入口 | 地址 |
|---|---|
| 业务接口 | http://localhost:9533/api/ |
| 采集接口 | http://localhost:9533/api/ingest/ |
| **管理后台** | http://localhost:9533/admin/index.html |
| 接口文档 | http://localhost:9533/swagger-ui.html |

默认账号（启动时自动创建）：

| 角色 | 账号 | 密码 |
|---|---|---|
| 管理员 | 13800000001 | admin123 |
| 演示用户 | 13800000000 | 123456 |

### 3. 采集器

```bash
cd D:/news-collector/crawler
pip install -r requirements.txt
python run.py --dry-run --limit 3        # 只抓取不写库，验证解析
python run.py                            # 全量采集并入库（自动触发 AI 摘要）
```

### 4. 前端

用 HBuilderX 打开 `D:/news-collector/web`，运行到浏览器（H5）。
若后端端口变化，只需改 `web/config/api.js` 一处。

---

## 五、采集源与可抓取性（2026-10 实测）

| 源 | 地址 | 结构 | 结果 |
|---|---|---|---|
| 芜湖市科技局 | kjj.wuhu.gov.cn | 服务端渲染列表，20 条/页，4 个频道 | ✅ 200，无 robots |
| 芜湖市政府 RSS | www.wuhu.gov.cn/rss/rss.xml | 标准 RSS，自带摘要 | ✅ 200 ⭐ 最稳 |
| 芜湖市政府新闻中心 | www.wuhu.gov.cn/xwzx/* | 静态列表，18 条/页 | ✅ 200 |
| 芜湖新闻网 | www.wuhunews.cn/{yaowen,djzx}/ | 静态列表，`?pp=` 可深翻 | ✅ 200 |

- 四个站点均**无 robots.txt（404）**，无显式禁止；采集器仍遵守：随机间隔、单线程、超时重试、仅存标题/正文/来源/原文链接。
- 已知限制：科技局列表分页由 JS 渲染（`index_1.html` 404），因此按**每日增量**策略采集首页 20 条 × 4 频道。

---

## 六、AI 摘要设计

| 环节 | 做法 |
|---|---|
| 触发 | 采集入库后**异步**生成（`@Async` 线程池），不阻塞采集响应；管理端支持单条重生成与批量补齐 |
| 模型 | DeepSeek `deepseek-chat`（OpenAI 兼容 `/chat/completions`） |
| 提示词 | 固定 system 提示词，要求**只输出 JSON**：`{summary≤120字, keywords[3-5], category(8选1), importance 1-5}`，`response_format=json_object`，`temperature=0.2` |
| 落库 | `news.ai_summary / ai_keywords / ai_status / ai_model / ai_tokens / ai_time`，并写入 `ai_log` 记录 token 用量与耗时 |
| 降级 | Key 未配置或调用失败 → 本地抽取式摘要（首段截断 + 标题关键词），`ai_status` 仍为 1，保证演示不中断 |
| 成本 | 实测单篇约 300 tokens；回填 500 篇约 ¥1 以内 |
| 配置 | `application.yml` 的 `ai.deepseek.*`，密钥支持环境变量 `DEEPSEEK_API_KEY` 覆盖 |

---

## 七、作业要求对照

| 作业要求 | 本项目实现 |
|---|---|
| ≥6 个完整页面 | 首页、频道列表、搜索、详情、评论、评论详情、收藏、我的、个人资料、修改密码、登录、注册、关于 = **13 个** |
| ≥10 个不同组件 | 复用 24 个（Parser / mescroll / uni-card / uni-popup / uni-icon / uni-drawer / uni-nav-bar / loading / noData / loadMore / iconfont / time-filter …）+ 自研 3 个 = **27 个** |
| 云服务器或第三方后端 | 第三方 **DeepSeek 大模型 API** 作为后端 AI 能力；本地 MySQL 承担用户管理与 Banner（上云见"后续方案"） |
| 用户管理 / Banner | `app_user`（含角色、启用禁用、管理端列表）+ `banner` 表（管理端增删改查） |
| 管理端（加分项） | 内置静态管理端：**数据看板 / 新闻审核发布 / 轮播管理 / 采集源管理 / 采集日志 / 用户管理** |
| 说明插件与编写比例 | 见 `docs/插件与来源说明.md` |

---

## 八、已知限制与后续方案

**当前限制**
1. 未上云：后端、数据库、采集器均在本机运行（按规划"先本地打通，上云列为后续"）。
2. 管理端为 Spring Boot 内置静态页（单文件），非独立前端工程。
3. 微信小程序端未做真机发布（需 HTTPS 备案域名），演示以 H5 为主；代码保持 `mp-weixin` 可编译。
4. 忘记密码 / 短信验证码 / 头像上传 / 微信登录等在原模板中存在但后端未实现，前端已移除入口。

**后续方案（保留）**
- 上云：轻量应用服务器 + Docker Compose（mysql + api-server + nginx）+ HTTPS + 域名备案；`mysqldump` 导出云数据
- 独立管理端：Vue3 + Element Plus 工程，替换内置静态页
- 采集增强：逆向科技局分页 AJAX 以支持历史回填；接入省科技厅与区县站点
- AI 增强：向量化检索 + 站内问答（RAG）

---

## 九、开发说明

- 本机 Maven 全局配置把本地仓库指向了不存在的 `D:\maven\rep` 且镜像了 central，命令行构建会失效；使用 `tools/mvn-settings.xml` 规避（IDEA 构建不受影响）。
- 数据库连接、采集令牌、DeepSeek Key 均在 `api-server/src/main/resources/application.yml`，**密钥已入库，公开前请替换/轮换**。
