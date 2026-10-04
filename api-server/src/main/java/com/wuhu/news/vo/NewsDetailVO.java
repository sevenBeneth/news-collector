package com.wuhu.news.vo;

import com.fasterxml.jackson.annotation.JsonFormat;
import lombok.Data;

import java.util.Date;

/**
 * 新闻详情
 */
@Data
public class NewsDetailVO {

    private Long id;
    private String title;
    private String content;
    private String photo_url;
    private String origin;
    private String source_url;

    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss", timezone = "GMT+8")
    private Date publish_time;

    private Integer read_count;
    private Integer like_count;
    private Integer comment_count;

    /** AI 摘要相关信息 */
    private String ai_summary;
    private String ai_keywords;
    private Integer ai_status;
    private String ai_model;

    private Long category_id;
    private String category_name;

    /** 当前用户是否已点赞/收藏（未登录为 null） */
    private Integer is_like;
    private Integer is_favorite;

    /** 评论首页 */
    private PageResult<CommentVO> comment;
}
