package com.wuhu.news.entity;

import lombok.Data;

import javax.persistence.GeneratedValue;
import javax.persistence.GenerationType;
import javax.persistence.Id;
import javax.persistence.Table;
import java.util.Date;

/**
 * 评论（一级评论 pid 为空，回复挂 pid）
 */
@Data
@Table(name = "comment")
public class Comment {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private Long news_id;
    private Long user_id;
    private String content;
    private Long pid;
    private Integer reply_count;
    private Integer like_count;
    private Integer enable;
    private Date create_time;
}
