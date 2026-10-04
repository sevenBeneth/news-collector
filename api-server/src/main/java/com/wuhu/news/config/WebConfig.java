package com.wuhu.news.config;

import org.springframework.boot.web.servlet.FilterRegistrationBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.Ordered;
import org.springframework.web.filter.OncePerRequestFilter;

import javax.servlet.FilterChain;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.regex.Pattern;

/**
 * 跨域配置。
 *
 * H5 端由 HBuilderX 的 dev-server 提供（默认 8080，端口可能浮动），
 * 这里对 localhost / 127.0.0.1 的任意端口放行，避免演示时因端口变化导致跨域失败。
 */
@Configuration
public class WebConfig {

    /** 仅放行本机来源 */
    private static final Pattern LOCAL_ORIGIN =
            Pattern.compile("^https?://(localhost|127\\.0\\.0\\.1)(:\\d+)?$");

    @Bean
    public FilterRegistrationBean<OncePerRequestFilter> localCorsFilter() {
        FilterRegistrationBean<OncePerRequestFilter> bean = new FilterRegistrationBean<>();
        bean.setName("localCorsFilter");
        bean.setFilter(new OncePerRequestFilter() {
            @Override
            protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
                    throws ServletException, IOException {
                String origin = request.getHeader("Origin");
                if (origin != null && LOCAL_ORIGIN.matcher(origin).matches()) {
                    response.setHeader("Access-Control-Allow-Origin", origin);
                    response.setHeader("Access-Control-Allow-Credentials", "true");
                    response.setHeader("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS");
                    String reqHeaders = request.getHeader("Access-Control-Request-Headers");
                    response.setHeader("Access-Control-Allow-Headers",
                            reqHeaders != null ? reqHeaders : "Content-Type,token,platform,X-Admin-Token,X-Ingest-Token");
                    response.setHeader("Access-Control-Max-Age", "3600");
                    response.setHeader("Vary", "Origin");
                }
                if ("OPTIONS".equalsIgnoreCase(request.getMethod())) {
                    response.setStatus(HttpServletResponse.SC_OK);
                    return;
                }
                chain.doFilter(request, response);
            }
        });
        bean.addUrlPatterns("/*");
        bean.setOrder(Ordered.HIGHEST_PRECEDENCE);
        return bean;
    }
}
