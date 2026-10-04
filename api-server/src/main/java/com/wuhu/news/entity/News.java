package com.wuhu.news.entity;

import lombok.Data;

import javax.persistence.GeneratedValue;
import javax.persistence.GenerationType;
import javax.persistence.Id;
import javax.persistence.Table;
import javax.persistence.Transient;
import java.util.Date;

/**
 * 新闻（采集落库的科技创新资讯）
 */
@Data
@Table(name = "news")
public class News {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /** 标题 */
    private String title;

    /** 原文链接（采集幂等键） */
    private String source_url;

    /** 正文 */
    private String content;

    /** 封面图 */
    private String photo_url;

    /** 来源媒体 */
    private String origin;

    /** 原文发布时间 */
    private Date publish_time;

    /** 采集时间 */
    private Date crawl_time;

    /** 频道ID */
    private Long category_id;

    private Integer read_count;
    private Integer like_count;
    private Integer comment_count;

    /** AI 摘要 */
    private String ai_summary;
    /** AI 关键词，逗号分隔 */
    private String ai_keywords;
    /** 0未生成 1成功 2失败 */
    private Integer ai_status;
    private String ai_model;
    private Integer ai_tokens;
    private Date ai_time;

    /** 0待审 1已发布 2驳回 */
    private Integer status;
    /** 是否可作轮播 */
    private Boolean slider;

    /** 标题+来源哈希，跨源去重 */
    private String content_hash;

    private Date create_time;
    private Date update_time;

    /** 频道名称（非表字段，管理端联表查询回填） */
    @Transient
    private String category_name;
}
