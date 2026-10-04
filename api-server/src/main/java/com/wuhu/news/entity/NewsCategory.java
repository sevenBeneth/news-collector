package com.wuhu.news.entity;

import lombok.Data;

import javax.persistence.GeneratedValue;
import javax.persistence.GenerationType;
import javax.persistence.Id;
import javax.persistence.Table;
import java.util.Date;

/**
 * 新闻频道（科技政策/创新平台/企业创新/成果转化/人才引育/园区动态/通知公告/他山之石）
 */
@Data
@Table(name = "news_category")
public class NewsCategory {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String name;
    private String code;
    private Integer sort;
    private Integer enable;
    private Date create_time;
}
