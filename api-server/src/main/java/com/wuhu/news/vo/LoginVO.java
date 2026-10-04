package com.wuhu.news.vo;

import lombok.Data;

/**
 * 登录返回
 */
@Data
public class LoginVO {

    private Long user_id;
    private String nickname;
    private String mobile;
    private String avatar_url;
    /** 管理员登录时为 1 */
    private Integer role;
    private String token;
}
