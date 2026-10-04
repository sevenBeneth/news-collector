package com.wuhu.news.service;

import com.github.pagehelper.Page;
import com.github.pagehelper.PageHelper;
import com.wuhu.news.entity.*;
import com.wuhu.news.mapper.*;
import com.wuhu.news.vo.PageResult;
import com.wuhu.news.vo.StatVO;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.Arrays;
import java.util.Date;
import java.util.List;

/**
 * 管理端服务：新闻审核发布、轮播、采集源、日志、用户
 */
@Slf4j
@Service
public class AdminService {

    @Autowired
    private NewsMapper newsMapper;
    @Autowired
    private NewsCategoryMapper categoryMapper;
    @Autowired
    private BannerMapper bannerMapper;
    @Autowired
    private CrawlSourceMapper crawlSourceMapper;
    @Autowired
    private CrawlLogMapper crawlLogMapper;
    @Autowired
    private AppUserMapper userMapper;
    @Autowired
    private CommentMapper commentMapper;
    @Autowired
    private AiService aiService;

    // ---------------- 看板 ----------------

    public StatVO stats() {
        StatVO vo = new StatVO();
        vo.setNewsTotal(newsMapper.countAll());
        vo.setPending(newsMapper.countByStatus(0));
        vo.setPublished(newsMapper.countByStatus(1));
        vo.setRejected(newsMapper.countByStatus(2));
        vo.setAiDone(newsMapper.countByAiStatus(1));
        vo.setAiFailed(newsMapper.countByAiStatus(2));
        vo.setTodayInserted(newsMapper.countToday());
        vo.setSourceCount(crawlSourceMapper.selectAllOrdered().size());
        vo.setUserCount(userMapper.countAll());
        vo.setCommentCount((int) commentMapper.selectCount(null));
        vo.setBannerCount(bannerMapper.selectAllOrdered().size());
        vo.setTotalTokens(newsMapper.sumTokens());
        vo.setCategoryDist(newsMapper.countByCategory());
        return vo;
    }

    // ---------------- 新闻管理 ----------------

    public PageResult<News> newsPage(Integer status, Long categoryId, String keyword, Integer aiStatus,
                                     int pageIndex, int pageSize) {
        String kw = (keyword == null || keyword.trim().isEmpty()) ? null : keyword.trim();
        Page<News> page = PageHelper.startPage(pageIndex, pageSize)
                .doSelectPage(() -> newsMapper.selectAdminList(status, categoryId, kw, aiStatus));
        return PageResult.of(page.getTotal(), pageSize, page.getResult());
    }

    public News getNews(Long id) {
        return newsMapper.selectByPrimaryKey(id);
    }

    /** 新增 / 编辑新闻 */
    @Transactional
    public Integer saveNews(News form) {
        if (form.getId() == null) {
            if (form.getCreate_time() == null) {
                form.setCreate_time(new Date());
            }
            if (form.getCrawl_time() == null) {
                form.setCrawl_time(new Date());
            }
            if (form.getAi_status() == null) {
                form.setAi_status(0);
            }
            if (form.getStatus() == null) {
                form.setStatus(0);
            }
            if (form.getSource_url() == null || form.getSource_url().trim().isEmpty()) {
                form.setSource_url("manual://" + System.currentTimeMillis());
            }
            newsMapper.insertSelective(form);
            // 手工新增的新闻也自动生成摘要
            if (form.getContent() != null && form.getContent().length() > 60) {
                aiService.summarizeAsync(form.getId());
            }
            return 0;
        }
        newsMapper.updateByPrimaryKeySelective(form);
        return 0;
    }

    /** 审核：1 通过发布，2 驳回 */
    public Integer audit(Long id, Integer status) {
        News news = new News();
        news.setId(id);
        news.setStatus(status);
        newsMapper.updateByPrimaryKeySelective(news);
        log.info("审核新闻 id={} status={}", id, status);
        return 0;
    }

    /** 批量审核 */
    public Integer batchAudit(String ids, Integer status) {
        if (ids == null || ids.trim().isEmpty()) {
            return 0;
        }
        int count = 0;
        for (String id : ids.split(",")) {
            if (id.trim().isEmpty()) {
                continue;
            }
            News news = new News();
            news.setId(Long.valueOf(id.trim()));
            news.setStatus(status);
            newsMapper.updateByPrimaryKeySelective(news);
            count++;
        }
        log.info("批量审核 {} 条 -> status={}", count, status);
        return count;
    }

    @Transactional
    public Integer deleteNews(Long id) {
        newsMapper.deleteByPrimaryKey(id);
        return 0;
    }

    public Integer regenerateAi(Long id) {
        News news = newsMapper.selectByPrimaryKey(id);
        if (news != null) {
            aiService.summarize(news);
        }
        return 0;
    }

    public Integer backfillAi(int limit) {
        return aiService.backfill(limit);
    }

    // ---------------- 轮播管理 ----------------

    public List<Banner> banners() {
        return bannerMapper.selectAllOrdered();
    }

    public Integer saveBanner(Banner banner) {
        if (banner.getEnable() == null) {
            banner.setEnable(1);
        }
        if (banner.getSort() == null) {
            banner.setSort(1);
        }
        if (banner.getId() == null) {
            banner.setCreate_time(new Date());
            bannerMapper.insertSelective(banner);
        } else {
            bannerMapper.updateByPrimaryKeySelective(banner);
        }
        return 0;
    }

    public Integer deleteBanner(Long id) {
        bannerMapper.deleteByPrimaryKey(id);
        return 0;
    }

    // ---------------- 采集源 ----------------

    public List<CrawlSource> sources() {
        return crawlSourceMapper.selectAllOrdered();
    }

    public Integer saveSource(CrawlSource source) {
        if (source.getEnable() == null) {
            source.setEnable(1);
        }
        if (source.getSort() == null) {
            source.setSort(1);
        }
        if (source.getMax_pages() == null) {
            source.setMax_pages(1);
        }
        if (source.getId() == null) {
            source.setCreate_time(new Date());
            crawlSourceMapper.insertSelective(source);
        } else {
            crawlSourceMapper.updateByPrimaryKeySelective(source);
        }
        return 0;
    }

    public Integer deleteSource(Long id) {
        crawlSourceMapper.deleteByPrimaryKey(id);
        return 0;
    }

    // ---------------- 采集日志 ----------------

    public PageResult<CrawlLog> crawlLogs(int pageIndex, int pageSize) {
        Page<CrawlLog> page = PageHelper.startPage(pageIndex, pageSize)
                .doSelectPage(() -> crawlLogMapper.selectRecent());
        return PageResult.of(page.getTotal(), pageSize, page.getResult());
    }

    // ---------------- 用户管理 ----------------

    public PageResult<AppUser> users(String keyword, int pageIndex, int pageSize) {
        String kw = (keyword == null || keyword.trim().isEmpty()) ? null : keyword.trim();
        Page<AppUser> page = PageHelper.startPage(pageIndex, pageSize)
                .doSelectPage(() -> userMapper.search(kw));
        return PageResult.of(page.getTotal(), pageSize, page.getResult());
    }

    public Integer enableUser(Long id, Integer enable) {
        AppUser user = new AppUser();
        user.setId(id);
        user.setEnable(enable);
        userMapper.updateByPrimaryKeySelective(user);
        return 0;
    }

    // ---------------- 频道 ----------------

    public List<NewsCategory> categories() {
        return categoryMapper.selectAllOrdered();
    }

    /** 校验管理员身份 */
    public AppUser requireAdmin(Long userId) {
        AppUser user = userMapper.selectByPrimaryKey(userId);
        if (user == null || user.getRole() == null || user.getRole() != 1) {
            throw new BasicException(1010, "无管理权限");
        }
        return user;
    }

    /** 供静态管理页显示的可选频道编码（与提示词中的枚举保持一致） */
    public List<String> categoryCodes() {
        return Arrays.asList("policy", "platform", "enterprise", "achievement", "talent", "park", "notice", "learn");
    }
}
