package com.wuhu.news.vo;

import lombok.Data;

/**
 * 大模型摘要结果（内部使用，也用于返回给管理端展示）
 */
@Data
public class AiResult {

    private boolean success;
    private String summary;
    private String keywords;
    /** 频道 code，如 policy / enterprise */
    private String categoryCode;
    private Integer importance;
    private String model;
    private int promptTokens;
    private int completionTokens;
    private int totalTokens;
    private long durationMs;
    private String message;
}
