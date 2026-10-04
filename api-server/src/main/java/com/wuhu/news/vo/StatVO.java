package com.wuhu.news.vo;

import lombok.Data;

import java.util.List;
import java.util.Map;

/**
 * 管理端看板统计
 */
@Data
public class StatVO {

    private int newsTotal;
    private int pending;
    private int published;
    private int rejected;
    private int aiDone;
    private int aiFailed;
    private int todayInserted;
    private int sourceCount;
    private int userCount;
    private int commentCount;
    private int bannerCount;
    private long totalTokens;

    /** 各频道新闻数：[{name, count}] */
    private List<Map<String, Object>> categoryDist;
}
