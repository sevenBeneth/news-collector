package com.wuhu.news;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableAsync;
import tk.mybatis.spring.annotation.MapperScan;

/**
 * 芜湖市科技创新新闻收集平台 - 启动类
 *
 * 模块：多源采集入库 / DeepSeek AI 摘要 / 业务 API / 内置管理端
 */
@SpringBootApplication
@EnableAsync
@MapperScan(basePackages = "com.wuhu.news.mapper")
public class NewsCollectorApplication {

    public static void main(String[] args) {
        SpringApplication.run(NewsCollectorApplication.class, args);
        System.out.println("\n==== 芜湖市科技创新新闻收集平台 后端已启动 ====");
        System.out.println("业务接口 : http://localhost:9533/api/");
        System.out.println("采集接口 : http://localhost:9533/api/ingest/");
        System.out.println("管理后台 : http://localhost:9533/admin/index.html");
        System.out.println("接口文档 : http://localhost:9533/swagger-ui.html\n");
    }
}
