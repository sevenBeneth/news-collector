package com.wuhu.news.entity;

import lombok.Data;

import javax.persistence.GeneratedValue;
import javax.persistence.GenerationType;
import javax.persistence.Id;
import javax.persistence.Table;
import java.util.Date;

/**
 * 用户行为：收藏 / 点赞（统一表，target_type 区分）
 */
@Data
@Table(name = "user_action")
public class UserAction {

    public static final int TYPE_FAVORITE_NEWS = 1;
    public static final int TYPE_LIKE_NEWS = 2;
    public static final int TYPE_LIKE_COMMENT = 3;

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private Long user_id;
    private Integer target_type;
    private Long target_id;
    private Date create_time;
}
