-- ============================================================
-- 芜湖市科技创新新闻收集平台 - 数据库结构 v1
-- MySQL 8.0 / utf8mb4
-- 幂等：全部使用 CREATE TABLE IF NOT EXISTS，可重复执行，不清空数据
-- 需要清空重建请使用 sql/00_reset.sql
-- ============================================================

CREATE DATABASE IF NOT EXISTS `news_collector`
  DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;

USE `news_collector`;

-- ------------------------------------------------------------
-- 频道（科技政策/创新平台/...）
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `news_category` (
  `id`          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  `name`        VARCHAR(50)     NOT NULL                COMMENT '频道名',
  `code`        VARCHAR(50)     NOT NULL                COMMENT '频道编码',
  `sort`        INT             NOT NULL DEFAULT 1      COMMENT '排序',
  `enable`      TINYINT(1)      NOT NULL DEFAULT 1      COMMENT '1启用 0停用',
  `create_time` DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='新闻频道';

-- ------------------------------------------------------------
-- 新闻主表
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `news` (
  `id`            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  `title`         VARCHAR(500)    NOT NULL                COMMENT '标题',
  `source_url`    VARCHAR(500)    NOT NULL                COMMENT '原文链接（幂等去重键）',
  `content`       MEDIUMTEXT      NULL                    COMMENT '正文（清洗后纯文本/HTML）',
  `photo_url`     VARCHAR(500)    NULL                    COMMENT '封面图',
  `origin`        VARCHAR(100)    NULL                    COMMENT '来源媒体，如 芜湖市科技局',
  `publish_time`  DATETIME        NULL                    COMMENT '原文发布时间',
  `crawl_time`    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '采集时间',
  `category_id`   BIGINT UNSIGNED NULL                    COMMENT '频道ID',
  `read_count`    INT             NOT NULL DEFAULT 0      COMMENT '阅读数',
  `like_count`    INT             NOT NULL DEFAULT 0      COMMENT '点赞数',
  `comment_count` INT             NOT NULL DEFAULT 0      COMMENT '评论数',
  `ai_summary`    VARCHAR(1000)   NULL                    COMMENT 'AI摘要',
  `ai_keywords`   VARCHAR(500)    NULL                    COMMENT 'AI关键词，逗号分隔',
  `ai_status`     TINYINT         NOT NULL DEFAULT 0      COMMENT '0未生成 1成功 2失败',
  `ai_model`      VARCHAR(50)     NULL                    COMMENT '摘要使用的模型',
  `ai_tokens`     INT             NOT NULL DEFAULT 0      COMMENT '消耗token',
  `ai_time`       DATETIME        NULL                    COMMENT '摘要生成时间',
  `status`        TINYINT         NOT NULL DEFAULT 0      COMMENT '0待审 1已发布 2驳回',
  `slider`        TINYINT(1)      NOT NULL DEFAULT 0      COMMENT '1可作轮播',
  `content_hash`  CHAR(32)        NULL                    COMMENT '标题+来源哈希，跨源去重',
  `create_time`   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time`   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_source_url` (`source_url`(200)),
  KEY `idx_status_publish` (`status`, `publish_time`),
  KEY `idx_category` (`category_id`, `status`),
  KEY `idx_ai_status` (`ai_status`, `status`),
  KEY `idx_hash` (`content_hash`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='科技创新新闻';

-- ------------------------------------------------------------
-- 首页轮播 Banner
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `banner` (
  `id`          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `title`       VARCHAR(200)    NOT NULL,
  `image_url`   VARCHAR(500)    NULL                COMMENT '图片地址',
  `link_url`    VARCHAR(500)    NULL                COMMENT '跳转链接（外部）',
  `news_id`     BIGINT UNSIGNED NULL                COMMENT '关联新闻ID（优先跳详情）',
  `sort`        INT             NOT NULL DEFAULT 1,
  `enable`      TINYINT(1)      NOT NULL DEFAULT 1,
  `create_time` DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_enable_sort` (`enable`, `sort`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='首页轮播';

-- ------------------------------------------------------------
-- 用户（演示级：手机号+密码，无短信验证）
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `app_user` (
  `id`           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `nickname`     VARCHAR(100)    NULL,
  `avatar_url`   VARCHAR(500)    NULL,
  `phone_number` VARCHAR(20)     NULL,
  `password`     VARCHAR(100)    NULL                COMMENT '加盐MD5',
  `gender`       TINYINT         NULL,
  `enable`       TINYINT(1)      NOT NULL DEFAULT 1,
  `role`         TINYINT         NOT NULL DEFAULT 0   COMMENT '0普通用户 1管理员',
  `create_time`  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_phone` (`phone_number`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户';

-- ------------------------------------------------------------
-- 评论（保留互动能力，单层+回复）
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `comment` (
  `id`          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `news_id`     BIGINT UNSIGNED NOT NULL,
  `user_id`     BIGINT UNSIGNED NOT NULL,
  `content`     VARCHAR(1000)   NOT NULL,
  `pid`         BIGINT UNSIGNED NULL                COMMENT '父评论ID，NULL为一级评论',
  `reply_count` INT             NOT NULL DEFAULT 0,
  `like_count`  INT             NOT NULL DEFAULT 0,
  `enable`      TINYINT(1)      NOT NULL DEFAULT 1,
  `create_time` DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_news_pid` (`news_id`, `pid`),
  KEY `idx_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='评论';

-- ------------------------------------------------------------
-- 用户行为（收藏/点赞，统一表）
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `user_action` (
  `id`          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id`     BIGINT UNSIGNED NOT NULL,
  `target_type` TINYINT         NOT NULL COMMENT '1收藏新闻 2点赞新闻 3点赞评论',
  `target_id`   BIGINT UNSIGNED NOT NULL,
  `create_time` DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_target` (`user_id`, `target_type`, `target_id`),
  KEY `idx_target` (`target_type`, `target_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户行为';

-- ------------------------------------------------------------
-- 采集源配置（adapter 由爬虫实现，可在管理页开关）
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `crawl_source` (
  `id`                    BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `name`                  VARCHAR(100)    NOT NULL,
  `adapter`               VARCHAR(50)     NOT NULL COMMENT 'wuhu_kjj_list / wuhu_gov_rss / wuhu_gov_list / wuhunews_list',
  `list_url`              VARCHAR(500)    NOT NULL COMMENT '列表页或RSS地址',
  `default_category_code` VARCHAR(50)     NULL     COMMENT '默认归入频道',
  `keyword_filter`        VARCHAR(500)    NULL     COMMENT '命中任一关键词才入库，空则不过滤',
  `max_pages`             INT             NOT NULL DEFAULT 1 COMMENT '最大翻页数',
  `enable`                TINYINT(1)      NOT NULL DEFAULT 1,
  `sort`                  INT             NOT NULL DEFAULT 1,
  `last_crawl_time`       DATETIME        NULL,
  `remark`                VARCHAR(500)    NULL,
  `create_time`           DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time`           DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_enable` (`enable`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='采集源';

-- ------------------------------------------------------------
-- 采集日志
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `crawl_log` (
  `id`          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `source_id`   BIGINT UNSIGNED NULL,
  `source_name` VARCHAR(100)    NULL,
  `total`       INT             NOT NULL DEFAULT 0 COMMENT '抓取条数',
  `inserted`    INT             NOT NULL DEFAULT 0 COMMENT '新增入库',
  `duplicated`  INT             NOT NULL DEFAULT 0 COMMENT '重复跳过',
  `filtered`    INT             NOT NULL DEFAULT 0 COMMENT '关键词过滤掉',
  `status`      TINYINT         NOT NULL DEFAULT 1 COMMENT '1成功 0失败',
  `message`     VARCHAR(1000)   NULL,
  `duration_ms` INT             NOT NULL DEFAULT 0,
  `create_time` DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_source_time` (`source_id`, `create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='采集日志';

-- ------------------------------------------------------------
-- AI 调用日志（成本可观测）
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `ai_log` (
  `id`                BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `news_id`           BIGINT UNSIGNED NULL,
  `model`             VARCHAR(50)     NULL,
  `prompt_tokens`     INT             NOT NULL DEFAULT 0,
  `completion_tokens` INT             NOT NULL DEFAULT 0,
  `total_tokens`      INT             NOT NULL DEFAULT 0,
  `status`            TINYINT         NOT NULL DEFAULT 1 COMMENT '1成功 0失败',
  `message`           VARCHAR(500)    NULL,
  `duration_ms`       INT             NOT NULL DEFAULT 0,
  `create_time`       DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_news` (`news_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI调用日志';
