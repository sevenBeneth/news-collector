package com.wuhu.news.mapper;

import com.wuhu.news.entity.Banner;
import com.wuhu.news.utils.MyBaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

import java.util.List;

@Mapper
public interface BannerMapper extends MyBaseMapper<Banner> {

    @Select("select * from banner order by sort asc, id desc")
    List<Banner> selectAllOrdered();

    /** 生成轮播图后回写图片地址 */
    @Update("update banner set image_url = #{url} where id = #{id}")
    int updateImageUrl(@Param("id") Long id, @Param("url") String url);
}
