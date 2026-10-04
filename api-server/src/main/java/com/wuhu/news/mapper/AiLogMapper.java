package com.wuhu.news.mapper;

import com.wuhu.news.entity.AiLog;
import com.wuhu.news.utils.MyBaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface AiLogMapper extends MyBaseMapper<AiLog> {

    @Select("select * from ai_log order by id desc limit 100")
    List<AiLog> selectRecent();
}
