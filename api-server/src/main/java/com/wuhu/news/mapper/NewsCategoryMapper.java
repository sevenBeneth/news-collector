package com.wuhu.news.mapper;

import com.wuhu.news.entity.NewsCategory;
import com.wuhu.news.utils.MyBaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface NewsCategoryMapper extends MyBaseMapper<NewsCategory> {

    @Select("select * from news_category where enable = 1 order by sort asc, id asc")
    List<NewsCategory> selectEnabled();

    @Select("select * from news_category order by sort asc, id asc")
    List<NewsCategory> selectAllOrdered();

    @Select("select * from news_category where code = #{code} limit 1")
    NewsCategory selectByCode(String code);
}
