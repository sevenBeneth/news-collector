package com.wuhu.news.entity;

import lombok.Data;

import javax.persistence.GeneratedValue;
import javax.persistence.GenerationType;
import javax.persistence.Id;
import javax.persistence.Table;
import java.util.Date;

/**
 * AI 摘要调用日志（成本可观测）
 */
@Data
@Table(name = "ai_log")
public class AiLog {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private Long news_id;
    private String model;
    private Integer prompt_tokens;
    private Integer completion_tokens;
    private Integer total_tokens;
    /** 1成功 0失败 */
    private Integer status;
    private String message;
    private Integer duration_ms;
    private Date create_time;
}
