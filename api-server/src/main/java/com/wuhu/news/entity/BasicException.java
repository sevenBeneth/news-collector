package com.wuhu.news.entity;

import lombok.Data;

@Data
public class BasicException extends RuntimeException {

    private Integer code;

    public BasicException(String msg) {
        super(msg);
    }

    public BasicException(SysCode sysCode) {
        super(sysCode.MESSAGE);
        this.code = sysCode.CODE;
    }

    public BasicException(Integer code, String msg) {
        super(msg);
        this.code = code;
    }

}
 