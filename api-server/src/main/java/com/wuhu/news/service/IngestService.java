package com.wuhu.news.service;

import com.alibaba.fastjson.JSONObject;
import com.wuhu.news.entity.CrawlLog;
import com.wuhu.news.entity.CrawlSource;
import com.wuhu.news.entity.News;
import com.wuhu.news.entity.NewsCategory;
import com.wuhu.news.mapper.CrawlLogMapper;
import com.wuhu.news.mapper.CrawlSourceMapper;
import com.wuhu.news.mapper.NewsCategoryMapper;
import com.wuhu.news.mapper.NewsMapper;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.codec.digest.DigestUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 采集入库服务（Python 采集器 → 本服务 → 数据库）
 *
 * 幂等策略：
 *  1) source_url 唯一，重复直接跳过
 *  2) content_hash（标题哈希）跨源去重，避免同一条新闻转载多次入库
 */
@Slf4j
@Service
public class IngestService {

    @Autowired
    private NewsMapper newsMapper;
    @Autowired
    private NewsCategoryMapper categoryMapper;
    @Autowired
    private CrawlSourceMapper crawlSourceMapper;
    @Autowired
    private CrawlLogMapper crawlLogMapper;
    @Autowired
    private AiService aiService;

    /** 采集器拉取启用中的采集源配置 */
    public List<CrawlSource> sources() {
        return crawlSourceMapper.selectEnabled();
    }

    /** 批量入库，并异步触发生成 AI 摘要 */
    public Map<String, Object> ingest(List<JSONObject> items) {
        int total = items == null ? 0 : items.size();
        int inserted = 0;
        int duplicated = 0;
        int filtered = 0;
        if (items != null) {
            for (JSONObject item : items) {
                String url = str(item, "source_url");
                String title = str(item, "title");
                if (StringUtils.isEmpty(url) || StringUtils.isEmpty(title)) {
                    filtered++;
                    continue;
                }
                if (newsMapper.findIdByUrl(url) != null) {
                    duplicated++;
                    continue;
                }
                String hash = DigestUtils.md5Hex(title.trim());
                if (newsMapper.findIdByHash(hash) != null) {
                    duplicated++;
                    continue;
                }
                News news = new News();
                news.setTitle(trim(title, 480));
                news.setSource_url(trim(url, 480));
                news.setContent(str(item, "content"));
                news.setPhoto_url(trim(str(item, "photo_url"), 480));
                news.setOrigin(trim(str(item, "origin"), 90));
                news.setPublish_time(parseDate(str(item, "publish_time")));
                news.setCrawl_time(new Date());

                String categoryCode = str(item, "category_code");
                NewsCategory category = StringUtils.isEmpty(categoryCode) ? null : categoryMapper.selectByCode(categoryCode);
                news.setCategory_id(category == null ? null : category.getId());

                news.setRead_count(0);
                news.setLike_count(0);
                news.setComment_count(0);
                news.setAi_status(0);
                news.setAi_tokens(0);
                news.setStatus(0);
                news.setSlider(false);
                news.setContent_hash(hash);
                news.setCreate_time(new Date());
                newsMapper.insertSelective(news);
                inserted++;

                // 异步生成摘要（不阻塞采集响应）
                aiService.summarizeAsync(news.getId());
            }
        }
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("total", total);
        result.put("inserted", inserted);
        result.put("duplicated", duplicated);
        result.put("filtered", filtered);
        log.info("采集入库完成：{}", result);
        return result;
    }

    /** 采集器回写采集日志 */
    public Integer saveLog(JSONObject body) {
        CrawlLog log = new CrawlLog();
        log.setSource_id(body.getLong("source_id"));
        log.setSource_name(trim(body.getString("source_name"), 90));
        log.setTotal(body.getIntValue("total"));
        log.setInserted(body.getIntValue("inserted"));
        log.setDuplicated(body.getIntValue("duplicated"));
        log.setFiltered(body.getIntValue("filtered"));
        log.setStatus(body.getIntValue("status"));
        log.setMessage(trim(body.getString("message"), 900));
        log.setDuration_ms(body.getIntValue("duration_ms"));
        log.setCreate_time(new Date());
        crawlLogMapper.insertSelective(log);
        return 0;
    }

    /** 更新采集源的最近采集时间 */
    public Integer touch(Long sourceId) {
        crawlSourceMapper.touch(sourceId);
        return 0;
    }

    // ---------------- 工具 ----------------

    private static String str(JSONObject item, String key) {
        String value = item.getString(key);
        return value == null ? null : value.trim();
    }

    private static String trim(String value, int max) {
        if (value == null) {
            return null;
        }
        return value.length() <= max ? value : value.substring(0, max);
    }

    private static Date parseDate(String value) {
        if (StringUtils.isEmpty(value)) {
            return null;
        }
        String[] patterns = {"yyyy-MM-dd HH:mm:ss", "yyyy-MM-dd HH:mm", "yyyy-MM-dd"};
        for (String pattern : patterns) {
            try {
                return new SimpleDateFormat(pattern).parse(value);
            } catch (Exception ignored) {
                // 尝试下一个格式
            }
        }
        return null;
    }
}
