package com.wuhu.news.controller;

import com.wuhu.news.entity.*;
import com.wuhu.news.service.AdminService;
import com.wuhu.news.service.UserService;
import com.wuhu.news.utils.JWTUtil;
import com.wuhu.news.vo.LoginVO;
import com.wuhu.news.vo.PageResult;
import com.wuhu.news.vo.StatVO;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import javax.servlet.http.HttpServletRequest;
import java.util.List;

/**
 * 内置管理端接口
 *
 * 鉴权：登录后返回 JWT，管理页把 token 放在 Header X-Admin-Token；
 *      服务端校验 token 有效且该用户 role=1。
 */
@Slf4j
@RestController
@RequestMapping("/admin/api")
public class AdminApiController {

    @Autowired
    private AdminService adminService;
    @Autowired
    private UserService userService;

    // ---------------- 登录 ----------------

    @PostMapping("login")
    public LoginVO login(@RequestParam String mobile, @RequestParam String password,
                         @RequestParam(required = false) String username) {
        String account = (mobile != null && !mobile.isEmpty()) ? mobile : username;
        LoginVO vo = userService.login(account, password);
        if (vo.getRole() == null || vo.getRole() != 1) {
            throw new BasicException(1010, "该账号无管理权限");
        }
        return vo;
    }

    // ---------------- 看板 ----------------

    @GetMapping("stats")
    public StatVO stats(HttpServletRequest request) {
        requireAdmin(request);
        return adminService.stats();
    }

    // ---------------- 新闻 ----------------

    @GetMapping("news")
    public PageResult<News> news(HttpServletRequest request,
                                 @RequestParam(required = false) Integer status,
                                 @RequestParam(required = false) Long category_id,
                                 @RequestParam(required = false) String keyword,
                                 @RequestParam(required = false) Integer ai_status,
                                 @RequestParam(defaultValue = "1") Integer page_index,
                                 @RequestParam(defaultValue = "10") Integer page_size) {
        requireAdmin(request);
        return adminService.newsPage(status, category_id, keyword, ai_status, page_index, page_size);
    }

    @GetMapping("news/{id}")
    public News newsDetail(HttpServletRequest request, @PathVariable("id") Long id) {
        requireAdmin(request);
        return adminService.getNews(id);
    }

    @PostMapping("news/save")
    public Integer newsSave(HttpServletRequest request, News news) {
        requireAdmin(request);
        return adminService.saveNews(news);
    }

    @PostMapping("news/audit")
    public Integer newsAudit(HttpServletRequest request, @RequestParam Long id, @RequestParam Integer status) {
        requireAdmin(request);
        return adminService.audit(id, status);
    }

    @PostMapping("news/batchAudit")
    public Integer newsBatchAudit(HttpServletRequest request, @RequestParam String ids, @RequestParam Integer status) {
        requireAdmin(request);
        return adminService.batchAudit(ids, status);
    }

    @PostMapping("news/delete")
    public Integer newsDelete(HttpServletRequest request, @RequestParam Long id) {
        requireAdmin(request);
        return adminService.deleteNews(id);
    }

    // ---------------- AI ----------------

    @PostMapping("ai/backfill")
    public Integer aiBackfill(HttpServletRequest request, @RequestParam(defaultValue = "5") Integer limit) {
        requireAdmin(request);
        return adminService.backfillAi(limit);
    }

    @PostMapping("ai/regenerate")
    public Integer aiRegenerate(HttpServletRequest request, @RequestParam Long id) {
        requireAdmin(request);
        return adminService.regenerateAi(id);
    }

    // ---------------- 轮播 ----------------

    @GetMapping("banner")
    public List<Banner> banner(HttpServletRequest request) {
        requireAdmin(request);
        return adminService.banners();
    }

    @PostMapping("banner/save")
    public Integer bannerSave(HttpServletRequest request, Banner banner) {
        requireAdmin(request);
        return adminService.saveBanner(banner);
    }

    @PostMapping("banner/delete")
    public Integer bannerDelete(HttpServletRequest request, @RequestParam Long id) {
        requireAdmin(request);
        return adminService.deleteBanner(id);
    }

    // ---------------- 采集源 ----------------

    @GetMapping("source")
    public List<CrawlSource> source(HttpServletRequest request) {
        requireAdmin(request);
        return adminService.sources();
    }

    @PostMapping("source/save")
    public Integer sourceSave(HttpServletRequest request, CrawlSource source) {
        requireAdmin(request);
        return adminService.saveSource(source);
    }

    @PostMapping("source/delete")
    public Integer sourceDelete(HttpServletRequest request, @RequestParam Long id) {
        requireAdmin(request);
        return adminService.deleteSource(id);
    }

    // ---------------- 采集日志 ----------------

    @GetMapping("crawl/logs")
    public PageResult<CrawlLog> crawlLogs(HttpServletRequest request,
                                          @RequestParam(defaultValue = "1") Integer page_index,
                                          @RequestParam(defaultValue = "10") Integer page_size) {
        requireAdmin(request);
        return adminService.crawlLogs(page_index, page_size);
    }

    // ---------------- 用户 ----------------

    @GetMapping("user")
    public PageResult<AppUser> user(HttpServletRequest request,
                                    @RequestParam(required = false) String keyword,
                                    @RequestParam(defaultValue = "1") Integer page_index,
                                    @RequestParam(defaultValue = "10") Integer page_size) {
        requireAdmin(request);
        return adminService.users(keyword, page_index, page_size);
    }

    @PostMapping("user/enable")
    public Integer userEnable(HttpServletRequest request, @RequestParam Long id, @RequestParam Integer enable) {
        requireAdmin(request);
        return adminService.enableUser(id, enable);
    }

    // ---------------- 频道 ----------------

    @GetMapping("category")
    public List<NewsCategory> category(HttpServletRequest request) {
        requireAdmin(request);
        return adminService.categories();
    }

    // ---------------- 内部 ----------------

    private Long requireAdmin(HttpServletRequest request) {
        String token = request.getHeader("X-Admin-Token");
        if (token == null || token.trim().isEmpty() || !JWTUtil.verify(token)) {
            throw new BasicException(SysCode.TOKEN_NOT_NULL);
        }
        Long userId = JWTUtil.getUserId(token);
        adminService.requireAdmin(userId);
        return userId;
    }
}
