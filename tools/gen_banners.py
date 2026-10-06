#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生成首页轮播 Banner 图片（与滑动框比例一致）

滑动框尺寸：宽 750rpx × 高 320rpx  →  比例 750:320 = 2.34375:1
本脚本输出 2 倍图 1500×640，保证高清屏清晰；<image mode="aspectFill"> 下不会被裁切。

用法：python tools/gen_banners.py
输出：web/static/images/banner/banner-{1..3}.png
"""
import os
from PIL import Image, ImageDraw, ImageFont

W, H = 1500, 640                      # 2 倍图
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       '..', 'web', 'static', 'images', 'banner')
FONT_BOLD = r'C:\Windows\Fonts\msyhbd.ttc'
FONT_REG = r'C:\Windows\Fonts\msyh.ttc'

BRAND = '芜湖市科技创新新闻收集平台'

# 三张横幅：标题 / 副标题 / 来源行 / 渐变色
BANNERS = [
    dict(
        title=['鸠兹科创湾开园', '打造长三角场景创新高地'],
        sub='场景牵引 · 技术验证 · 产业落地',
        source='来源：芜湖市科技局 · 2026-09-20',
        c1=(142, 20, 20), c2=(198, 40, 40),
    ),
    dict(
        title=['2026年度高新技术企业', '认定申报工作启动'],
        sub='申报条件 · 材料清单 · 时间节点',
        source='来源：芜湖市科技局 · 2026-05-01',
        c1=(120, 26, 60), c2=(190, 44, 78),
    ),
    dict(
        title=['芜湖造航空发动机', '亮相世界制造业大会'],
        sub='高端制造 · 航空装备 · 创新实力',
        source='来源：芜湖新闻网 · 2026-10-01',
        c1=(16, 62, 96), c2=(30, 116, 158),
    ),
]


def gradient(size, c1, c2):
    """纵向渐变底色"""
    w, h = size
    img = Image.new('RGB', size, c1)
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(h - 1, 1)
        d.line([(0, y), (w, y)],
               fill=(int(c1[0] + (c2[0] - c1[0]) * t),
                     int(c1[1] + (c2[1] - c1[1]) * t),
                     int(c1[2] + (c2[2] - c1[2]) * t)))
    return img


def decorate(img):
    """右侧科技感装饰：同心圆环 + 斜向光带"""
    layer = Image.new('RGBA', img.size, (255, 255, 255, 0))
    d = ImageDraw.Draw(layer)
    cx, cy = int(W * 0.86), int(H * 0.52)
    for r, a in ((300, 26), (230, 30), (160, 34), (92, 40)):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 255, 255, a), width=3)
    d.ellipse([cx - 34, cy - 34, cx + 34, cy + 34], fill=(255, 255, 255, 46))
    d.polygon([(W * 0.60, H), (W * 0.80, 0), (W * 0.88, 0), (W * 0.68, H)],
              fill=(255, 255, 255, 16))
    return Image.alpha_composite(img.convert('RGBA'), layer)


def rounded(draw, box, radius, fill=None, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def build(cfg, path):
    img = decorate(gradient((W, H), cfg['c1'], cfg['c2']))
    d = ImageDraw.Draw(img)

    f_brand = ImageFont.truetype(FONT_REG, 30)
    f_title = ImageFont.truetype(FONT_BOLD, 78)
    f_sub = ImageFont.truetype(FONT_REG, 34)
    f_src = ImageFont.truetype(FONT_REG, 30)
    f_badge = ImageFont.truetype(FONT_BOLD, 30)

    # 左上：平台名
    d.text((72, 52), BRAND, font=f_brand, fill=(255, 255, 255, 210))

    # 右上：AI 摘要徽标
    label = 'AI 摘要'
    tw = d.textlength(label, font=f_badge)
    bx1, by1 = W - 72 - (tw + 56), 46
    rounded(d, [bx1, by1, W - 72, by1 + 56], 28, fill=(255, 255, 255, 200))
    d.text((bx1 + 28, by1 + 12), label, font=f_badge, fill=cfg['c1'])

    # 主标题（两行）
    y = 190
    for line in cfg['title']:
        d.text((72, y), line, font=f_title, fill=(255, 255, 255, 255))
        y += 96

    # 副标题
    d.text((76, y + 10), cfg['sub'], font=f_sub, fill=(255, 255, 255, 215))

    # 底部来源行
    d.text((72, H - 76), cfg['source'], font=f_src, fill=(255, 255, 255, 190))

    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.convert('RGB').save(path, 'PNG', optimize=True)
    return path


if __name__ == '__main__':
    out_dir = os.path.abspath(OUT_DIR)
    for i, cfg in enumerate(BANNERS, start=1):
        p = build(cfg, os.path.join(out_dir, 'banner-%d.png' % i))
        size = os.path.getsize(p)
        with Image.open(p) as im:
            print('生成 %s  %dx%d  %.1f KB' % (p, im.width, im.height, size / 1024.0))
    print('完成，比例 %.4f:1（滑动框 750:320）' % (W / float(H)))
