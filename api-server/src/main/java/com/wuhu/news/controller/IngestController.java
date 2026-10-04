package com.wuhu.news.controller;

import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONObject;
import com.wuhu.news.entity.BasicException;
import com.wuhu.news.entity.CrawlSource;
import com.wuhu.news.service.IngestService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * 采集端接口（Python 采集器调用）
 *
 * 鉴权：Header X-Ingest-Token
 */
@Slf4j
@RestController
@RequestMapping("/api/ingest")
public class IngestController {

    @Value("${app.ingest-token}")
    private String ingestToken;

    @Autowired
    private IngestService ingestService;

    /** 采集源配置 */
    @GetMapping("sources")
    public List<CrawlSource> sources(@RequestHeader(value = "X-Ingest-Token", required = false) String token) {
        checkToken(token);
        return ingestService.sources();
    }

    /** 批量入库 */
    @PostMapping("news")
    public Map<String, Object> news(@RequestHeader(value = "X-Ingest-Token", required = false) String token,
                                    @RequestBody String body) {
        checkToken(token);
        List<JSONObject> items = JSON.parseArray(body, JSONObject.class);
        return ingestService.ingest(items);
    }

    /** 采集日志 */
    @PostMapping("log")
    public Integer log(@RequestHeader(value = "X-Ingest-Token", required = false) String token,
                       @RequestBody String body) {
        checkToken(token);
        return ingestService.saveLog(JSON.parseObject(body));
    }

    /** 更新采集源最近采集时间 */
    @PostMapping("source/{id}/touch")
    public Integer touch(@RequestHeader(value = "X-Ingest-Token", required = false) String token,
                         @PathVariable("id") Long id) {
        checkToken(token);
        return ingestService.touch(id);
    }

    private void checkToken(String token) {
        if (token == null || !token.equals(ingestToken)) {
            throw new BasicException(403, "采集令牌不合法");
        }
    }
}
