package com.wuhu.news.service;

import com.wuhu.news.entity.AppUser;
import com.wuhu.news.entity.BasicException;
import com.wuhu.news.entity.SysCode;
import com.wuhu.news.mapper.AppUserMapper;
import com.wuhu.news.utils.JWTUtil;
import com.wuhu.news.utils.MD5Utils;
import com.wuhu.news.vo.LoginVO;
import com.wuhu.news.vo.UserInfoVO;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.util.Date;

/**
 * 用户业务（演示级：注册不需要短信验证码，登录使用无状态 JWT）
 */
@Slf4j
@Service
public class UserService {

    @Autowired
    private AppUserMapper userMapper;

    /** 登录 */
    public LoginVO login(String mobile, String password) {
        AppUser user = userMapper.selectByMobile(mobile);
        if (user == null) {
            throw new BasicException(SysCode.USER_NOT_EXISTS);
        }
        if (user.getEnable() != null && user.getEnable() == 0) {
            throw new BasicException(1009, "该账号已被禁用");
        }
        if (!MD5Utils.getSaltverifyMD5(password, user.getPassword())) {
            throw new BasicException(SysCode.PASSWORD_ERROR);
        }
        return buildLoginVO(user);
    }

    /** 注册（演示级：无验证码校验），注册成功直接返回登录态 */
    public LoginVO register(String mobile, String nickname, String password) {
        if (StringUtils.isEmpty(mobile) || StringUtils.isEmpty(password)) {
            throw new BasicException(1005, "手机号和密码不能为空");
        }
        if (userMapper.selectByMobile(mobile) != null) {
            throw new BasicException(SysCode.USER_ALREADY_EXISTS);
        }
        AppUser user = new AppUser();
        user.setNickname(StringUtils.isEmpty(nickname) ? ("用户" + mobile.substring(mobile.length() - 4)) : nickname);
        user.setPhone_number(mobile);
        user.setPassword(MD5Utils.getSaltMD5(password));
        user.setAvatar_url("");
        user.setEnable(1);
        user.setRole(0);
        user.setCreate_time(new Date());
        userMapper.insertSelective(user);
        return buildLoginVO(user);
    }

    /** 用户资料（手机号中间四位打码） */
    public UserInfoVO userInfo(Long userId) {
        AppUser user = userMapper.selectByPrimaryKey(userId);
        if (user == null) {
            throw new BasicException(SysCode.USER_NOT_EXISTS);
        }
        UserInfoVO vo = new UserInfoVO();
        vo.setId(user.getId());
        vo.setNickname(user.getNickname());
        vo.setAvatar_url(user.getAvatar_url());
        vo.setSex(user.getGender());
        vo.setStatus(user.getEnable());
        String mobile = user.getPhone_number();
        if (!StringUtils.isEmpty(mobile) && mobile.length() == 11) {
            vo.setMobile(mobile.substring(0, 3) + "****" + mobile.substring(7));
        } else {
            vo.setMobile(mobile);
        }
        return vo;
    }

    /** 修改密码 */
    public Integer updatePassword(Long userId, String oldPassword, String newPassword) {
        AppUser user = userMapper.selectByPrimaryKey(userId);
        if (user == null) {
            throw new BasicException(SysCode.USER_NOT_EXISTS);
        }
        if (!MD5Utils.getSaltverifyMD5(oldPassword, user.getPassword())) {
            throw new BasicException(SysCode.PASSWORD_ERROR);
        }
        user.setPassword(MD5Utils.getSaltMD5(newPassword));
        return userMapper.updateByPrimaryKeySelective(user);
    }

    public AppUser getById(Long userId) {
        return userMapper.selectByPrimaryKey(userId);
    }

    private LoginVO buildLoginVO(AppUser user) {
        LoginVO vo = new LoginVO();
        vo.setUser_id(user.getId());
        vo.setNickname(user.getNickname());
        vo.setMobile(user.getPhone_number());
        vo.setAvatar_url(user.getAvatar_url());
        vo.setRole(user.getRole());
        vo.setToken(JWTUtil.generateToken(user.getId()));
        return vo;
    }
}
