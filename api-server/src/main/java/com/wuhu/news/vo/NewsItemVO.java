package com.wuhu.news.vo;

import com.fasterxml.jackson.annotation.JsonFormat;
import lombok.Data;

import java.util.Date;

/**
 * 列表项（首页/频道/搜索/收藏共用）
 */
@Data
public class NewsItemVO {

    private Long id;
    private String title;
    private String photo_url;
    private String origin;
    private String source_url;
    private String ai_summary;
    private String ai_keywords;

    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss", timezone = "GMT+8")
    private Date publish_time;

    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss", timezone = "GMT+8")
    private Date favorite_time;

    private Integer read_count;
    private Integer like_count;
    private Integer comment_count;
    private Long category_id;
    private String category_name;
}
