package com.wuhu.news.entity;

import lombok.Data;

import javax.persistence.GeneratedValue;
import javax.persistence.GenerationType;
import javax.persistence.Id;
import javax.persistence.Table;
import java.util.Date;

/**
 * 采集日志
 */
@Data
@Table(name = "crawl_log")
public class CrawlLog {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private Long source_id;
    private String source_name;
    private Integer total;
    private Integer inserted;
    private Integer duplicated;
    private Integer filtered;
    /** 1成功 0失败 */
    private Integer status;
    private String message;
    private Integer duration_ms;
    private Date create_time;
}
