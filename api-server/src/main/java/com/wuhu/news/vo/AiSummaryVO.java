package com.wuhu.news.vo;

import com.fasterxml.jackson.annotation.JsonFormat;
import lombok.Data;

import java.util.Date;

/**
 * AI 摘要状态（供前端轮询，不含任何写操作，不会影响阅读数）
 */
@Data
public class AiSummaryVO {

    private Long id;
    /** 0生成中 1成功 2失败 */
    private Integer ai_status;
    private String ai_summary;
    private String ai_keywords;
    private String ai_model;

    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss", timezone = "GMT+8")
    private Date ai_time;
}
