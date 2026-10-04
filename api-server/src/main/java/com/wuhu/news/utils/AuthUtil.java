package com.wuhu.news.utils;

import com.wuhu.news.entity.BasicException;
import com.wuhu.news.entity.SysCode;

/**
 * 登录态工具：统一处理 JWT 解析失败的情况。
 *
 * 说明：本项目为演示级实现，不引入 Redis，登录态完全由无状态 JWT 承载。
 */
public class AuthUtil {

    /** 可选登录：未登录返回 null（用于详情页判断是否已点赞/收藏） */
    public static Long optionalUserId() {
        try {
            Long userId = JWTUtil.getUserId();
            return (userId == null || userId <= 0) ? null : userId;
        } catch (Exception e) {
            return null;
        }
    }

    /** 必须登录：未登录抛 1000，前端据此跳转登录页 */
    public static Long requireUserId() {
        Long userId = optionalUserId();
        if (userId == null) {
            throw new BasicException(SysCode.TOKEN_NOT_NULL);
        }
        return userId;
    }
}
