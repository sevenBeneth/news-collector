package com.wuhu.news.vo;

import lombok.Data;

/**
 * 用户资料
 */
@Data
public class UserInfoVO {

    private Long id;
    private String nickname;
    private String mobile;
    private String avatar_url;
    private Integer sex;
    private Integer status;
}
