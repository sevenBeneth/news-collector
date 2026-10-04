package com.wuhu.news.entity;

import lombok.Data;

import javax.persistence.GeneratedValue;
import javax.persistence.GenerationType;
import javax.persistence.Id;
import javax.persistence.Table;
import java.util.Date;

/**
 * 用户（演示级：手机号 + 密码，无短信验证）
 */
@Data
@Table(name = "app_user")
public class AppUser {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String nickname;
    private String avatar_url;
    private String phone_number;
    /** 加盐 MD5 */
    private String password;
    private Integer gender;
    private Integer enable;
    /** 0普通用户 1管理员 */
    private Integer role;
    private Date create_time;
}
