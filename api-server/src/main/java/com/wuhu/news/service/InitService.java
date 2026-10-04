package com.wuhu.news.service;

import com.wuhu.news.entity.AppUser;
import com.wuhu.news.mapper.AppUserMapper;
import com.wuhu.news.utils.MD5Utils;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

import java.util.Date;

/**
 * 启动初始化：确保管理员账号与演示账号存在（幂等）
 *
 * 管理员：13800000001 / admin123   → 登录内置管理页
 * 演示用户：13800000000 / 123456    → 登录小程序/H5 端
 */
@Slf4j
@Component
public class InitService implements CommandLineRunner {

    @Autowired
    private AppUserMapper userMapper;

    @Value("${app.admin.mobile}")
    private String adminMobile;
    @Value("${app.admin.password}")
    private String adminPassword;
    @Value("${app.admin.nickname}")
    private String adminNickname;

    @Value("${app.demo-user.mobile}")
    private String demoMobile;
    @Value("${app.demo-user.password}")
    private String demoPassword;
    @Value("${app.demo-user.nickname}")
    private String demoNickname;

    @Override
    public void run(String... args) {
        ensureUser(adminMobile, adminPassword, adminNickname, 1);
        ensureUser(demoMobile, demoPassword, demoNickname, 0);
    }

    private void ensureUser(String mobile, String password, String nickname, int role) {
        AppUser exist = userMapper.selectByMobile(mobile);
        if (exist != null) {
            if (exist.getRole() == null || exist.getRole() != role) {
                AppUser update = new AppUser();
                update.setId(exist.getId());
                update.setRole(role);
                userMapper.updateByPrimaryKeySelective(update);
            }
            log.info("账号已存在：{} ({})", mobile, role == 1 ? "管理员" : "演示用户");
            return;
        }
        AppUser user = new AppUser();
        user.setNickname(nickname);
        user.setPhone_number(mobile);
        user.setPassword(MD5Utils.getSaltMD5(password));
        user.setAvatar_url("");
        user.setEnable(1);
        user.setRole(role);
        user.setCreate_time(new Date());
        userMapper.insertSelective(user);
        log.info("初始化账号：{} / {} ({})", mobile, password, role == 1 ? "管理员" : "演示用户");
    }
}
