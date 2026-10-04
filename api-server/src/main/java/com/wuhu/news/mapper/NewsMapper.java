package com.wuhu.news.mapper;

import com.wuhu.news.entity.Banner;
import com.wuhu.news.entity.News;
import com.wuhu.news.utils.MyBaseMapper;
import com.wuhu.news.vo.NewsDetailVO;
import com.wuhu.news.vo.NewsItemVO;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

import java.util.List;
import java.util.Map;

/**
 * 新闻 Mapper
 */
@Mapper
public interface NewsMapper extends MyBaseMapper<News> {

    // ---------------- 用户端 ----------------

    /** 首页/频道/搜索列表（仅已发布） */
    List<NewsItemVO> selectIndex(@Param("category_id") Long categoryId, @Param("keyword") String keyword);

    /** 新闻详情（含当前用户点赞/收藏状态） */
    NewsDetailVO selectDetail(@Param("id") Long id, @Param("userId") Long userId);

    /** 启用中的轮播 */
    List<Banner> selectEnabledBanners();

    /** 我的收藏 */
    List<NewsItemVO> selectFavoriteList(@Param("userId") Long userId);

    @Update("update news set read_count = read_count + 1 where id = #{id}")
    int increaseRead(@Param("id") Long id);

    @Update("update news set comment_count = greatest(comment_count + #{delta}, 0) where id = #{id}")
    int updateCommentCount(@Param("id") Long id, @Param("delta") int delta);

    @Update("update news set like_count = greatest(like_count + #{delta}, 0) where id = #{id}")
    int updateLikeCount(@Param("id") Long id, @Param("delta") int delta);

    // ---------------- 管理端 ----------------

    /** 管理端列表（支持状态/频道/AI状态/关键词筛选） */
    List<News> selectAdminList(@Param("status") Integer status,
                               @Param("categoryId") Long categoryId,
                               @Param("keyword") String keyword,
                               @Param("aiStatus") Integer aiStatus);

    /** 取待生成摘要的新闻 */
    @Select("select * from news where ai_status = 0 and content is not null and length(content) > 60 order by id desc limit #{limit}")
    List<News> selectPendingAi(@Param("limit") int limit);

    @Select("select count(*) from news")
    int countAll();

    @Select("select count(*) from news where status = #{status}")
    int countByStatus(@Param("status") int status);

    @Select("select count(*) from news where ai_status = #{aiStatus}")
    int countByAiStatus(@Param("aiStatus") int aiStatus);

    @Select("select count(*) from news where create_time >= curdate()")
    int countToday();

    @Select("select coalesce(sum(ai_tokens), 0) from news")
    long sumTokens();

    @Select("select c.name as name, count(n.id) as count from news_category c " +
            "left join news n on n.category_id = c.id and n.status = 1 " +
            "group by c.id, c.name order by c.sort")
    List<Map<String, Object>> countByCategory();

    // ---------------- 采集入库 / AI 回写 ----------------

    /** 幂等判断：按原文链接查 id */
    @Select("select id from news where source_url = #{url} limit 1")
    Long findIdByUrl(@Param("url") String url);

    /** 跨源去重：按标题哈希查 id */
    @Select("select id from news where content_hash = #{hash} limit 1")
    Long findIdByHash(@Param("hash") String hash);

    /** 回写 AI 摘要结果 */
    @Update("update news set ai_summary = #{summary}, ai_keywords = #{keywords}, ai_status = #{status}, " +
            "ai_model = #{model}, ai_tokens = #{tokens}, ai_time = now() where id = #{id}")
    int updateAi(@Param("id") Long id, @Param("summary") String summary, @Param("keywords") String keywords,
                 @Param("status") int status, @Param("model") String model, @Param("tokens") int tokens);

    /** 自动归档频道 */
    @Update("update news set category_id = #{categoryId} where id = #{id}")
    int updateCategory(@Param("id") Long id, @Param("categoryId") Long categoryId);
}
