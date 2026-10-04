package com.wuhu.news.service;

import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONArray;
import com.alibaba.fastjson.JSONObject;
import com.wuhu.news.entity.AiLog;
import com.wuhu.news.entity.News;
import com.wuhu.news.entity.NewsCategory;
import com.wuhu.news.mapper.AiLogMapper;
import com.wuhu.news.mapper.NewsCategoryMapper;
import com.wuhu.news.mapper.NewsMapper;
import com.wuhu.news.vo.AiResult;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;
import org.springframework.web.client.RestTemplate;

import javax.annotation.PostConstruct;
import java.text.SimpleDateFormat;
import java.util.*;

/**
 * DeepSeek 大模型摘要服务
 *
 * 流程：新闻入库 →（异步）读取正文 → 调用 DeepSeek（OpenAI 兼容接口）
 *      → 解析 JSON（摘要/关键词/频道/重要度）→ 回写数据库并记录 token 用量
 * 降级：Key 未配置或调用失败时，自动切换为本地抽取式摘要，保证演示不中断
 */
@Slf4j
@Service
public class AiService {

    /** 固定提示词：要求模型只输出 JSON */
    private static final String SYSTEM_PROMPT =
            "你是芜湖市科技创新新闻平台的内容编辑助手。用户会给你一篇新闻的标题、来源和正文。"
                    + "请阅读后输出严格的 JSON，不要输出任何解释文字，不要使用 markdown 代码块，格式如下："
                    + "{\"summary\":\"不超过120字的中文摘要，突出芜湖本地主体、政策或技术要点及影响\","
                    + "\"keywords\":[\"3到5个关键词\"],"
                    + "\"category\":\"从 policy,platform,enterprise,achievement,talent,park,notice,learn 中选择最匹配的一个\","
                    + "\"importance\":1到5的整数}";

    private static final Set<String> VALID_CATEGORY = new HashSet<>(Arrays.asList(
            "policy", "platform", "enterprise", "achievement", "talent", "park", "notice", "learn"));

    @Value("${ai.deepseek.enabled:true}")
    private boolean enabled;
    @Value("${ai.deepseek.base-url}")
    private String baseUrl;
    @Value("${ai.deepseek.key}")
    private String apiKey;
    @Value("${ai.deepseek.model}")
    private String model;
    @Value("${ai.deepseek.connect-timeout:10000}")
    private int connectTimeout;
    @Value("${ai.deepseek.read-timeout:90000}")
    private int readTimeout;
    @Value("${ai.deepseek.temperature:0.2}")
    private double temperature;
    @Value("${ai.deepseek.max-tokens:900}")
    private int maxTokens;

    @Autowired
    private NewsMapper newsMapper;
    @Autowired
    private NewsCategoryMapper categoryMapper;
    @Autowired
    private AiLogMapper aiLogMapper;

    private RestTemplate restTemplate;

    @PostConstruct
    public void init() {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(connectTimeout);
        factory.setReadTimeout(readTimeout);
        this.restTemplate = new RestTemplate(factory);
        log.info("AI 摘要服务初始化完成：enabled={} model={} key={}", enabled, model, mask(apiKey));
    }

    // ---------------- 对外方法 ----------------

    /** 同步生成摘要并落库（管理端"重新生成"、批量补齐使用） */
    public AiResult summarize(News news) {
        long start = System.currentTimeMillis();
        if (news == null) {
            AiResult r = new AiResult();
            r.setMessage("新闻不存在");
            return r;
        }
        if (!enabled || StringUtils.isEmpty(apiKey) || apiKey.contains("xxx")) {
            return fallback(news, "未配置有效的 DeepSeek API Key，使用本地抽取式摘要", start);
        }
        try {
            AiResult result = callDeepSeek(news);
            result.setDurationMs(System.currentTimeMillis() - start);
            result.setSuccess(true);
            persist(news.getId(), result);
            saveLog(news.getId(), result);
            log.info("AI摘要生成成功 newsId={} tokens={} 耗时={}ms", news.getId(), result.getTotalTokens(), result.getDurationMs());
            return result;
        } catch (Exception e) {
            log.warn("DeepSeek 调用失败，降级为抽取式摘要：{}", e.getMessage());
            AiResult fb = fallback(news, "DeepSeek 调用失败：" + e.getMessage(), start);
            saveLog(news.getId(), fb);
            return fb;
        }
    }

    /** 采集入库后异步生成摘要 */
    @Async("aiExecutor")
    public void summarizeAsync(Long newsId) {
        try {
            News news = newsMapper.selectByPrimaryKey(newsId);
            if (news != null) {
                summarize(news);
            }
        } catch (Exception e) {
            log.warn("异步生成摘要异常 newsId={} : {}", newsId, e.getMessage());
        }
    }

    /** 批量补齐待生成摘要的新闻，返回成功条数 */
    public int backfill(int limit) {
        List<News> list = newsMapper.selectPendingAi(limit);
        int success = 0;
        for (News news : list) {
            AiResult r = summarize(news);
            if (r.isSuccess()) {
                success++;
            }
        }
        log.info("批量补齐 AI 摘要：本次处理 {} 条，成功 {} 条", list.size(), success);
        return success;
    }

    // ---------------- 内部实现 ----------------

    private AiResult callDeepSeek(News news) {
        String content = plainText(news.getContent());
        if (content.length() > 2500) {
            content = content.substring(0, 2500);
        }
        String date = news.getPublish_time() == null ? "" : new SimpleDateFormat("yyyy-MM-dd").format(news.getPublish_time());
        String userPrompt = "标题：" + news.getTitle() + "\n来源：" + nvl(news.getOrigin())
                + "\n发布时间：" + date + "\n正文：\n" + content;

        List<Map<String, String>> messages = new ArrayList<>();
        messages.add(message("system", SYSTEM_PROMPT));
        messages.add(message("user", userPrompt));

        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("model", model);
        payload.put("messages", messages);
        payload.put("temperature", temperature);
        payload.put("max_tokens", maxTokens);
        payload.put("stream", false);
        payload.put("response_format", Collections.singletonMap("type", "json_object"));

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        headers.set("Authorization", "Bearer " + apiKey);

        String url = baseUrl + "/chat/completions";
        ResponseEntity<String> response = restTemplate.postForEntity(
                url, new HttpEntity<>(JSON.toJSONString(payload), headers), String.class);

        JSONObject body = JSON.parseObject(response.getBody());
        if (body == null || body.getJSONArray("choices") == null || body.getJSONArray("choices").isEmpty()) {
            throw new IllegalStateException("DeepSeek 返回内容为空");
        }
        JSONObject choice = body.getJSONArray("choices").getJSONObject(0).getJSONObject("message");
        String text = stripCodeFence(choice.getString("content"));

        AiResult result = new AiResult();
        result.setModel(model);
        try {
            JSONObject json = JSON.parseObject(text);
            result.setSummary(trim(json.getString("summary"), 500));
            JSONArray keywords = json.getJSONArray("keywords");
            if (keywords != null) {
                result.setKeywords(trim(String.join(",", keywords.toJavaList(String.class)), 480));
            }
            String category = json.getString("category");
            if (category != null && VALID_CATEGORY.contains(category.trim())) {
                result.setCategoryCode(category.trim());
            }
            result.setImportance(json.getInteger("importance"));
        } catch (Exception e) {
            // 模型偶尔会返回非严格 JSON，退化为原文前 120 字
            log.warn("模型返回非标准 JSON，降级处理：{}", text);
            result.setSummary(trim(text, 500));
        }

        JSONObject usage = body.getJSONObject("usage");
        if (usage != null) {
            result.setPromptTokens(usage.getIntValue("prompt_tokens"));
            result.setCompletionTokens(usage.getIntValue("completion_tokens"));
            result.setTotalTokens(usage.getIntValue("total_tokens"));
        }
        return result;
    }

    /** 本地抽取式摘要（降级方案） */
    private AiResult fallback(News news, String reason, long start) {
        AiResult result = new AiResult();
        result.setSuccess(true);
        result.setModel("extractive-fallback");
        result.setSummary(extractive(news));
        result.setKeywords(guessKeywords(news));
        result.setDurationMs(System.currentTimeMillis() - start);
        result.setMessage(reason);
        persist(news.getId(), result);
        log.info("使用抽取式摘要 newsId={} reason={}", news.getId(), reason);
        return result;
    }

    private void persist(Long newsId, AiResult result) {
        newsMapper.updateAi(newsId, result.getSummary(), result.getKeywords(), 1, result.getModel(), result.getTotalTokens());
        if (result.getCategoryCode() != null) {
            News current = newsMapper.selectByPrimaryKey(newsId);
            if (current != null && current.getCategory_id() == null) {
                NewsCategory category = categoryMapper.selectByCode(result.getCategoryCode());
                if (category != null) {
                    newsMapper.updateCategory(newsId, category.getId());
                }
            }
        }
    }

    private void saveLog(Long newsId, AiResult result) {
        try {
            AiLog log = new AiLog();
            log.setNews_id(newsId);
            log.setModel(result.getModel());
            log.setPrompt_tokens(result.getPromptTokens());
            log.setCompletion_tokens(result.getCompletionTokens());
            log.setTotal_tokens(result.getTotalTokens());
            log.setStatus(result.isSuccess() ? 1 : 0);
            log.setMessage(trim(result.getMessage(), 480));
            log.setDuration_ms((int) result.getDurationMs());
            log.setCreate_time(new Date());
            aiLogMapper.insertSelective(log);
        } catch (Exception e) {
            log.warn("写入 AI 日志失败：{}", e.getMessage());
        }
    }

    // ---------------- 文本工具 ----------------

    /** 去掉 HTML 标签与多余空白 */
    public static String plainText(String html) {
        if (html == null) {
            return "";
        }
        String text = html.replaceAll("(?is)<script.*?</script>", " ")
                .replaceAll("(?is)<style.*?</style>", " ")
                .replaceAll("(?s)<[^>]+>", " ")
                .replace("&nbsp;", " ")
                .replace("&amp;", "&")
                .replace("&quot;", "\"")
                .replace("&ldquo;", "“")
                .replace("&rdquo;", "”");
        return text.replaceAll("[\\u00a0\\u200b\\ufeff]", " ").replaceAll("\\s+", " ").trim();
    }

    private static String extractive(News news) {
        String text = plainText(news.getContent());
        if (text.length() < 20) {
            return trim(news.getTitle(), 120);
        }
        String first = text.length() > 110 ? text.substring(0, 110) : text;
        int cut = Math.max(first.lastIndexOf('。'), Math.max(first.lastIndexOf('；'), first.lastIndexOf('，')));
        if (cut > 40) {
            first = first.substring(0, cut + 1);
        }
        return trim(first, 200);
    }

    private static String guessKeywords(News news) {
        if (news.getTitle() == null) {
            return "";
        }
        String[] parts = news.getTitle().split("[\\s，。、：:；;（）()《》“”\"'’‘\\[\\]【】]+");
        LinkedHashSet<String> keywords = new LinkedHashSet<>();
        for (String part : parts) {
            String word = part.trim();
            if (word.length() >= 2 && word.length() <= 12 && !word.matches(".*\\d{4}.*")) {
                keywords.add(word);
            }
            if (keywords.size() >= 4) {
                break;
            }
        }
        return String.join(",", keywords);
    }

    private static Map<String, String> message(String role, String content) {
        Map<String, String> m = new HashMap<>(2);
        m.put("role", role);
        m.put("content", content);
        return m;
    }

    private static String stripCodeFence(String text) {
        if (text == null) {
            return "";
        }
        String t = text.trim();
        if (t.startsWith("```")) {
            t = t.replaceAll("^```[a-zA-Z]*", "").replaceAll("```$", "").trim();
        }
        return t;
    }

    private static String trim(String value, int max) {
        if (value == null) {
            return null;
        }
        return value.length() <= max ? value : value.substring(0, max);
    }

    private static String nvl(String value) {
        return value == null ? "" : value;
    }

    private static String mask(String key) {
        if (StringUtils.isEmpty(key) || key.length() < 12) {
            return "******";
        }
        return key.substring(0, 8) + "****" + key.substring(key.length() - 4);
    }
}
