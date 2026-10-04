package com.wuhu.news.vo;

import com.fasterxml.jackson.annotation.JsonFormat;
import lombok.Data;

import java.util.Date;

/**
 * 评论（含作者信息与回复分页）
 */
@Data
public class CommentVO {

    private Long id;
    private Long news_id;
    private Long user_id;
    private String content;
    private Long pid;
    private Integer reply_count;
    private Integer like_count;

    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss", timezone = "GMT+8")
    private Date create_time;

    /** 评论人昵称/头像 */
    private String nickname;
    private String avatar_url;

    /** 被回复人昵称（回复列表用） */
    private String parent_nickname;

    /** 当前用户是否已点赞该评论 */
    private Integer is_like;

    /** 回复分页（评论详情用） */
    private PageResult<CommentVO> reply;
}
