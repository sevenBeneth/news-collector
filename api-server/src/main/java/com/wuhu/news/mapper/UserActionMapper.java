package com.wuhu.news.mapper;

import com.wuhu.news.entity.UserAction;
import com.wuhu.news.utils.MyBaseMapper;
import org.apache.ibatis.annotations.Delete;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

@Mapper
public interface UserActionMapper extends MyBaseMapper<UserAction> {

    /** 是否已存在该行为，返回记录 id（不存在返回 null） */
    @Select("select id from user_action where user_id = #{userId} and target_type = #{type} and target_id = #{targetId} limit 1")
    Long findId(@Param("userId") Long userId, @Param("type") int type, @Param("targetId") Long targetId);

    @Delete("delete from user_action where user_id = #{userId} and target_type = #{type} and target_id = #{targetId}")
    int deleteAction(@Param("userId") Long userId, @Param("type") int type, @Param("targetId") Long targetId);
}
