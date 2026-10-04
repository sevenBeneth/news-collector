package com.wuhu.news.mapper;

import com.wuhu.news.entity.Comment;
import com.wuhu.news.utils.MyBaseMapper;
import com.wuhu.news.vo.CommentVO;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Update;

import java.util.List;

/**
 * 评论 Mapper
 */
@Mapper
public interface CommentMapper extends MyBaseMapper<Comment> {

    /** 一级评论分页 */
    List<CommentVO> selectTopComments(@Param("newsId") Long newsId, @Param("userId") Long userId);

    /** 单条评论 */
    CommentVO selectCommentById(@Param("id") Long id, @Param("userId") Long userId);

    /** 某条评论下的回复分页 */
    List<CommentVO> selectReplies(@Param("pid") Long pid, @Param("userId") Long userId);

    @Update("update comment set reply_count = greatest(reply_count + #{delta}, 0) where id = #{id}")
    int updateReplyCount(@Param("id") Long id, @Param("delta") int delta);

    @Update("update comment set like_count = greatest(like_count + #{delta}, 0) where id = #{id}")
    int updateLikeCount(@Param("id") Long id, @Param("delta") int delta);
}
