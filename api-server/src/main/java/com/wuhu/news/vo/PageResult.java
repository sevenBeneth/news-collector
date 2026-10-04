package com.wuhu.news.vo;

import lombok.Data;

import java.util.ArrayList;
import java.util.List;

/**
 * 通用分页返回结构：{count: 总条数, page: 总页数, list: 当前页数据}
 */
@Data
public class PageResult<T> {

    private long count;
    private int page;
    private List<T> list = new ArrayList<>();

    public PageResult() {
    }

    public PageResult(long count, int page, List<T> list) {
        this.count = count;
        this.page = page;
        this.list = list == null ? new ArrayList<>() : list;
    }

    public static <T> PageResult<T> of(long total, int pageSize, List<T> list) {
        int pages = 0;
        if (pageSize > 0) {
            pages = (int) (total / pageSize + (total % pageSize == 0 ? 0 : 1));
        }
        return new PageResult<>(total, pages, list);
    }
}
