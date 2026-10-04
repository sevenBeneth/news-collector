package com.wuhu.news.service;

import com.github.pagehelper.Page;
import com.github.pagehelper.PageHelper;
import com.wuhu.news.entity.*;
import com.wuhu.news.mapper.*;
import com.wuhu.news.utils.AuthUtil;
import com.wuhu.news.utils.SensitiveWordFilter;
import com.wuhu.news.vo.CommentVO;
import com.wuhu.news.vo.NewsDetailVO;
import com.wuhu.news.vo.NewsItemVO;
import com.wuhu.news.vo.PageResult;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import javax.annotation.PostConstruct;
import java.util.Date;
import java.util.List;

/**
 * 新闻业务：列表 / 详情 / 评论 / 点赞收藏
 */
@Slf4j
@Service
public class NewsService {

    @Autowired
    private NewsMapper newsMapper;
    @Autowired
    private CommentMapper commentMapper;
    @Autowired
    private UserActionMapper userActionMapper;
    @Autowired
    private NewsCategoryMapper categoryMapper;

    private SensitiveWordFilter sensitiveWordFilter;

    @PostConstruct
    public void init() {
        try {
            sensitiveWordFilter = new SensitiveWordFilter();
            sensitiveWordFilter.InitializationWork();
        } catch (Exception e) {
            log.warn("敏感词库初始化失败，评论将不做敏感词校验：{}", e.getMessage());
        }
    }

    // ---------------- 频道 / 轮播 ----------------

    public List<NewsCategory> categories() {
        return categoryMapper.selectEnabled();
    }

    public List<Banner> banners() {
        return newsMapper.selectEnabledBanners();
    }

    // ---------------- 列表 / 详情 ----------------

    public PageResult<NewsItemVO> index(Long categoryId, String keyword, int pageIndex, int pageSize) {
        String kw = (keyword == null || keyword.trim().isEmpty()) ? null : keyword.trim();
        Page<NewsItemVO> page = PageHelper.startPage(pageIndex, pageSize)
                .doSelectPage(() -> newsMapper.selectIndex(categoryId, kw));
        return PageResult.of(page.getTotal(), pageSize, page.getResult());
    }

    public NewsDetailVO detail(Long id, int pageSize) {
        Long userId = AuthUtil.optionalUserId();
        NewsDetailVO detail = newsMapper.selectDetail(id, userId);
        if (detail == null) {
            throw new BasicException(SysCode.NOT_EXISTS);
        }
        Page<CommentVO> page = PageHelper.startPage(1, pageSize)
                .doSelectPage(() -> commentMapper.selectTopComments(id, userId));
        detail.setComment(PageResult.of(page.getTotal(), pageSize, page.getResult()));
        newsMapper.increaseRead(id);
        return detail;
    }

    // ---------------- 评论 ----------------

    public PageResult<CommentVO> comments(Long newsId, int pageIndex, int pageSize) {
        Long userId = AuthUtil.optionalUserId();
        Page<CommentVO> page = PageHelper.startPage(pageIndex, pageSize)
                .doSelectPage(() -> commentMapper.selectTopComments(newsId, userId));
        return PageResult.of(page.getTotal(), pageSize, page.getResult());
    }

    public CommentVO commentDetail(Long id, int pageIndex, int pageSize) {
        Long userId = AuthUtil.optionalUserId();
        CommentVO vo = commentMapper.selectCommentById(id, userId);
        if (vo == null) {
            throw new BasicException(SysCode.NOT_EXISTS);
        }
        Page<CommentVO> page = PageHelper.startPage(pageIndex, pageSize)
                .doSelectPage(() -> commentMapper.selectReplies(id, userId));
        vo.setReply(PageResult.of(page.getTotal(), pageSize, page.getResult()));
        return vo;
    }

    /** 发表评论 */
    @Transactional
    public PageResult<CommentVO> addComment(Long newsId, String content, int pageSize) {
        Long userId = AuthUtil.requireUserId();
        checkSensitive(content);
        News news = newsMapper.selectByPrimaryKey(newsId);
        if (news == null) {
            throw new BasicException(SysCode.NOT_EXISTS);
        }
        Comment comment = new Comment();
        comment.setNews_id(newsId);
        comment.setUser_id(userId);
        comment.setContent(content);
        comment.setReply_count(0);
        comment.setLike_count(0);
        comment.setEnable(1);
        comment.setCreate_time(new Date());
        commentMapper.insertSelective(comment);
        newsMapper.updateCommentCount(newsId, 1);
        return comments(newsId, 1, pageSize);
    }

    /** 回复评论 */
    @Transactional
    public PageResult<CommentVO> addReply(Long commentId, Long pid, String content, int pageSize) {
        Long userId = AuthUtil.requireUserId();
        checkSensitive(content);
        Long parentId = (pid == null || pid <= 0) ? commentId : pid;
        Comment parent = commentMapper.selectByPrimaryKey(parentId);
        if (parent == null) {
            throw new BasicException(SysCode.NOT_EXISTS);
        }
        Comment comment = new Comment();
        comment.setNews_id(parent.getNews_id());
        comment.setUser_id(userId);
        comment.setContent(content);
        comment.setPid(parentId);
        comment.setReply_count(0);
        comment.setLike_count(0);
        comment.setEnable(1);
        comment.setCreate_time(new Date());
        commentMapper.insertSelective(comment);
        commentMapper.updateReplyCount(parentId, 1);
        Long viewer = userId;
        Page<CommentVO> page = PageHelper.startPage(1, pageSize)
                .doSelectPage(() -> commentMapper.selectReplies(parentId, viewer));
        return PageResult.of(page.getTotal(), pageSize, page.getResult());
    }

    // ---------------- 收藏 / 点赞 ----------------

    /** 收藏新闻（再次调用即取消），返回 0 */
    @Transactional
    public Integer toggleFavorite(Long newsId) {
        Long userId = AuthUtil.requireUserId();
        Long exist = userActionMapper.findId(userId, UserAction.TYPE_FAVORITE_NEWS, newsId);
        if (exist != null) {
            userActionMapper.deleteByPrimaryKey(exist);
        } else {
            UserAction action = new UserAction();
            action.setUser_id(userId);
            action.setTarget_type(UserAction.TYPE_FAVORITE_NEWS);
            action.setTarget_id(newsId);
            action.setCreate_time(new Date());
            userActionMapper.insertSelective(action);
        }
        return 0;
    }

    /** 点赞新闻（再次调用即取消），返回 0 */
    @Transactional
    public Integer toggleNewsLike(Long newsId) {
        Long userId = AuthUtil.requireUserId();
        Long exist = userActionMapper.findId(userId, UserAction.TYPE_LIKE_NEWS, newsId);
        if (exist != null) {
            userActionMapper.deleteByPrimaryKey(exist);
            newsMapper.updateLikeCount(newsId, -1);
        } else {
            UserAction action = new UserAction();
            action.setUser_id(userId);
            action.setTarget_type(UserAction.TYPE_LIKE_NEWS);
            action.setTarget_id(newsId);
            action.setCreate_time(new Date());
            userActionMapper.insertSelective(action);
            newsMapper.updateLikeCount(newsId, 1);
        }
        return 0;
    }

    /** 点赞评论，返回 0 */
    @Transactional
    public Integer toggleCommentLike(Long commentId) {
        Long userId = AuthUtil.requireUserId();
        Long exist = userActionMapper.findId(userId, UserAction.TYPE_LIKE_COMMENT, commentId);
        if (exist != null) {
            userActionMapper.deleteByPrimaryKey(exist);
            commentMapper.updateLikeCount(commentId, -1);
        } else {
            UserAction action = new UserAction();
            action.setUser_id(userId);
            action.setTarget_type(UserAction.TYPE_LIKE_COMMENT);
            action.setTarget_id(commentId);
            action.setCreate_time(new Date());
            userActionMapper.insertSelective(action);
            commentMapper.updateLikeCount(commentId, 1);
        }
        return 0;
    }

    /** 我的收藏 */
    public PageResult<NewsItemVO> favoriteList(int pageIndex, int pageSize) {
        Long userId = AuthUtil.requireUserId();
        Page<NewsItemVO> page = PageHelper.startPage(pageIndex, pageSize)
                .doSelectPage(() -> newsMapper.selectFavoriteList(userId));
        return PageResult.of(page.getTotal(), pageSize, page.getResult());
    }

    // ---------------- 内部工具 ----------------

    private void checkSensitive(String content) {
        if (StringUtils.isEmpty(content)) {
            throw new BasicException(1007, "内容不能为空");
        }
        if (content.length() > 500) {
            throw new BasicException(1008, "内容过长，请控制在 500 字以内");
        }
        if (sensitiveWordFilter != null) {
            String filtered = sensitiveWordFilter.filterInfo(content);
            if (!content.equals(filtered)) {
                throw new BasicException(SysCode.SENSITIVE_ERROR);
            }
        }
    }
}
