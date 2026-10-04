package com.wuhu.news.mapper;

import com.wuhu.news.entity.CrawlLog;
import com.wuhu.news.utils.MyBaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface CrawlLogMapper extends MyBaseMapper<CrawlLog> {

    @Select("select * from crawl_log order by id desc limit 200")
    List<CrawlLog> selectRecent();
}
