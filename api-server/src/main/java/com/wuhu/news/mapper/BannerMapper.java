package com.wuhu.news.mapper;

import com.wuhu.news.entity.Banner;
import com.wuhu.news.utils.MyBaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface BannerMapper extends MyBaseMapper<Banner> {

    @Select("select * from banner order by sort asc, id desc")
    List<Banner> selectAllOrdered();
}
