package com.wuhu.news.mapper;

import com.wuhu.news.entity.CrawlSource;
import com.wuhu.news.utils.MyBaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

import java.util.List;

@Mapper
public interface CrawlSourceMapper extends MyBaseMapper<CrawlSource> {

    @Select("select * from crawl_source order by sort asc, id asc")
    List<CrawlSource> selectAllOrdered();

    @Select("select * from crawl_source where enable = 1 order by sort asc, id asc")
    List<CrawlSource> selectEnabled();

    @Update("update crawl_source set last_crawl_time = now() where id = #{id}")
    int touch(Long id);
}
