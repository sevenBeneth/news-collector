<?xml version="1.0" encoding="UTF-8"?>
<map version="1.0.1">
  <node TEXT="芜湖市科技创新新闻收集平台">
    <node TEXT="用户端（H5 / 微信小程序）">
      <node TEXT="首页：轮播图 · 频道切换">
      </node>
      <node TEXT="信息流：标题 · AI摘要前40字 · 来源时间">
      </node>
      <node TEXT="搜索与频道列表">
      </node>
      <node TEXT="新闻详情：AI摘要卡片 · 正文 · 查看原文">
      </node>
      <node TEXT="互动：点赞 · 收藏 · 评论 · 回复">
      </node>
      <node TEXT="我的：资料 · 收藏 · 改密 · 反馈">
      </node>
      <node TEXT="账号：登录 · 注册 · 用户协议">
      </node>
    </node>
    <node TEXT="管理端（内置静态页）">
      <node TEXT="数据看板：总量 · 待审 · AI成败">
      </node>
      <node TEXT="新闻管理：审核 · 编辑 · 重生成摘要">
      </node>
      <node TEXT="轮播管理：新增 · 排序 · 上下线">
      </node>
      <node TEXT="采集源与采集日志">
      </node>
      <node TEXT="用户管理：检索 · 启用禁用">
      </node>
    </node>
    <node TEXT="后端服务（Spring Boot）">
      <node TEXT="用户端接口 /api/**">
      </node>
      <node TEXT="采集端接口 /api/ingest/**">
      </node>
      <node TEXT="管理端接口 /admin/api/**">
      </node>
      <node TEXT="AI摘要服务（DeepSeek）">
      </node>
      <node TEXT="异步任务 · 跨域 · 统一返回体">
      </node>
    </node>
    <node TEXT="采集器（Python）">
      <node TEXT="4类站点适配器（科技局/RSS/政府/新闻网）">
      </node>
      <node TEXT="正文抽取与编码归一">
      </node>
      <node TEXT="关键词过滤与双键去重">
      </node>
      <node TEXT="限速重试 · 采集日志">
      </node>
    </node>
    <node TEXT="数据层（MySQL news_collector）">
      <node TEXT="内容：news · news_category · banner">
      </node>
      <node TEXT="互动：comment · user_action">
      </node>
      <node TEXT="用户：app_user">
      </node>
      <node TEXT="采集：crawl_source · crawl_log · ai_log">
      </node>
    </node>
  </node>
</map>
