package com.wuhu.news.controller;

import com.alibaba.fastjson.JSONObject;
import com.wuhu.news.entity.Banner;
import com.wuhu.news.entity.NewsCategory;
import com.wuhu.news.service.NewsService;
import com.wuhu.news.service.UserService;
import com.wuhu.news.utils.AuthUtil;
import com.wuhu.news.vo.CommentVO;
import com.wuhu.news.vo.LoginVO;
import com.wuhu.news.vo.NewsDetailVO;
import com.wuhu.news.vo.NewsItemVO;
import com.wuhu.news.vo.PageResult;
import com.wuhu.news.vo.UserInfoVO;
import io.swagger.annotations.Api;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 用户端接口（小程序 / H5）
 */
@Slf4j
@Api(tags = "用户端")
@RestController
@RequestMapping("/api")
public class ApiController {

    @Autowired
    private NewsService newsService;
    @Autowired
    private UserService userService;

    // ---------------- 首页 ----------------

    @PostMapping("banner")
    public List<Banner> banner() {
        return newsService.banners();
    }

    @PostMapping("getCategory")
    public List<NewsCategory> getCategory() {
        return newsService.categories();
    }

    @PostMapping("getIndex")
    public Map<String, Object> getIndex(@RequestParam(required = false) String category_id,
                                        @RequestParam(required = false) String keyword,
                                        @RequestParam(defaultValue = "1") Integer page_index,
                                        @RequestParam(defaultValue = "10") Integer page_size) {
        PageResult<NewsItemVO> page = newsService.index(parseLong(category_id), keyword, page_index, page_size);
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("count", page.getCount());
        data.put("page", page.getPage());
        data.put("list", page.getList());
        data.put("slider", newsService.banners());
        return data;
    }

    @PostMapping("detail")
    public NewsDetailVO detail(@RequestParam Long id,
                               @RequestParam(defaultValue = "10") Integer page_size) {
        return newsService.detail(id, page_size);
    }

    // ---------------- 评论 ----------------

    @PostMapping("comment")
    public PageResult<CommentVO> comment(@RequestParam Long news_id,
                                         @RequestParam(defaultValue = "1") Integer page_index,
                                         @RequestParam(defaultValue = "10") Integer page_size) {
        return newsService.comments(news_id, page_index, page_size);
    }

    @PostMapping("commentDetail")
    public CommentVO commentDetail(@RequestParam Long id,
                                   @RequestParam(defaultValue = "1") Integer page_index,
                                   @RequestParam(defaultValue = "10") Integer page_size) {
        return newsService.commentDetail(id, page_index, page_size);
    }

    @PostMapping("addComment")
    public PageResult<CommentVO> addComment(@RequestParam Long news_id,
                                            @RequestParam String content,
                                            @RequestParam(defaultValue = "10") Integer page_size) {
        return newsService.addComment(news_id, content, page_size);
    }

    @PostMapping("addReply")
    public PageResult<CommentVO> addReply(@RequestParam Long comment_id,
                                          @RequestParam(required = false) Long pid,
                                          @RequestParam String content,
                                          @RequestParam(defaultValue = "10") Integer page_size) {
        return newsService.addReply(comment_id, pid, content, page_size);
    }

    // ---------------- 互动 ----------------

    @PostMapping("favorite")
    public Integer favorite(@RequestParam Long news_id) {
        return newsService.toggleFavorite(news_id);
    }

    @PostMapping("like")
    public Integer like(@RequestParam Long news_id) {
        return newsService.toggleNewsLike(news_id);
    }

    @PostMapping("commentLike")
    public Integer commentLike(@RequestParam Long comment_id) {
        return newsService.toggleCommentLike(comment_id);
    }

    @PostMapping("favoriteList")
    public PageResult<NewsItemVO> favoriteList(@RequestParam(defaultValue = "1") Integer page_index,
                                               @RequestParam(defaultValue = "10") Integer page_size) {
        return newsService.favoriteList(page_index, page_size);
    }

    // ---------------- 账号 ----------------

    @PostMapping("login")
    public LoginVO login(@RequestParam String mobile, @RequestParam String password) {
        return userService.login(mobile, password);
    }

    @PostMapping("register")
    public LoginVO register(@RequestParam String mobile,
                            @RequestParam(required = false) String nickname,
                            @RequestParam String password) {
        return userService.register(mobile, nickname, password);
    }

    @PostMapping({"userInfo", "userIndex"})
    public UserInfoVO userInfo() {
        return userService.userInfo(AuthUtil.requireUserId());
    }

    @PostMapping("logout")
    public Integer logout() {
        return 0;
    }

    @PostMapping("updatePassword")
    public Integer updatePassword(@RequestParam String old_password, @RequestParam String new_password) {
        return userService.updatePassword(AuthUtil.requireUserId(), old_password, new_password);
    }

    @PostMapping("feedback")
    public Integer feedback(@RequestParam(required = false) String content) {
        log.info("收到用户反馈：{}", content);
        return 0;
    }

    /** 兼容旧前端的 1000 兜底接口 */
    @PostMapping("noAuth")
    public JSONObject noAuth() {
        JSONObject json = new JSONObject();
        json.put("code", 1000);
        json.put("msg", "请先登录");
        return json;
    }

    private static Long parseLong(String value) {
        if (value == null || value.trim().isEmpty()) {
            return null;
        }
        try {
            return Long.valueOf(value.trim());
        } catch (NumberFormatException e) {
            return null;
        }
    }
}
