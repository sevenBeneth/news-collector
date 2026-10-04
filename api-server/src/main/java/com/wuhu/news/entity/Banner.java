package com.wuhu.news.entity;

import lombok.Data;

import javax.persistence.GeneratedValue;
import javax.persistence.GenerationType;
import javax.persistence.Id;
import javax.persistence.Table;
import java.util.Date;

/**
 * 首页轮播
 */
@Data
@Table(name = "banner")
public class Banner {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String title;
    private String image_url;
    private String link_url;
    /** 关联新闻，点击优先跳详情 */
    private Long news_id;
    private Integer sort;
    private Integer enable;
    private Date create_time;
    private Date update_time;
}
