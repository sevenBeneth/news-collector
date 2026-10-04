package com.wuhu.news.mapper;

import com.wuhu.news.entity.AppUser;
import com.wuhu.news.utils.MyBaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface AppUserMapper extends MyBaseMapper<AppUser> {

    @Select("select * from app_user where phone_number = #{mobile} limit 1")
    AppUser selectByMobile(@Param("mobile") String mobile);

    @Select("select * from app_user order by id desc")
    List<AppUser> selectAllOrdered();

    @Select("select count(*) from app_user")
    int countAll();

    /** 管理端：按手机号/昵称搜索 */
    @Select("<script>select * from app_user <where>"
            + "<if test='keyword != null and keyword != \"\"'>"
            + " and (phone_number like concat('%', #{keyword}, '%') or nickname like concat('%', #{keyword}, '%'))"
            + "</if></where> order by id desc</script>")
    List<AppUser> search(@Param("keyword") String keyword);
}
