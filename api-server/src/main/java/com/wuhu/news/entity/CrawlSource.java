package com.wuhu.news.entity;

import lombok.Data;

import javax.persistence.GeneratedValue;
import javax.persistence.GenerationType;
import javax.persistence.Id;
import javax.persistence.Table;
import java.util.Date;

/**
 * 采集源配置（adapter 由 Python 采集器实现）
 *
 * adapter 取值：
 *  - wuhu_kjj_list  芜湖市科技局列表页
 *  - wuhu_gov_rss   芜湖市人民政府 RSS
 *  - wuhu_gov_list  芜湖市人民政府新闻中心列表页
 *  - wuhunews_list  芜湖新闻网列表页
 */
@Data
@Table(name = "crawl_source")
public class CrawlSource {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String name;
    private String adapter;
    private String list_url;
    private String default_category_code;
    private String keyword_filter;
    private Integer max_pages;
    private Integer enable;
    private Integer sort;
    private Date last_crawl_time;
    private String remark;
    private Date create_time;
    private Date update_time;
}
