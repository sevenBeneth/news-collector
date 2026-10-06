#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
轮播图自动生成器（标题文字驱动）

思路：不再手写横幅文案，而是从后端接口读取 banner 记录 → 取每条 banner 关联新闻的
      真实标题 / 来源 / 发布时间 / 频道 / AI 关键词 → 自动排版生成与滑动框同比例的横幅。

滑动框尺寸：750rpx × 320rpx  →  比例 750:320 = 2.34375:1
输出：2 倍图 1500×640（高清屏清晰，aspectFill 下不裁切）
落盘：web/static/images/banner/banner-{bannerId}.png
可选：--update-api 回写 banner.image_url（需管理员账号）

用法示例：
  python tools/gen_banners.py                      # 用默认后端，生成全部启用轮播
  python tools/gen_banners.py --ids 1,3            # 只生成指定 banner
  python tools/gen_banners.py --dry-run            # 只打印排版结果，不写文件
  python tools/gen_banners.py --update-api         # 生成后回写数据库
  python tools/gen_banners.py --title-only         # 只用 banner 标题，不取关联新闻标题
"""
import argparse
import json
import os
import re
import sys

import requests
from PIL import Image, ImageDraw, ImageFont

# ---------------- 画布与排版常量 ----------------
W, H = 1500, 640                     # 2 倍图，比例 2.34375:1
MARGIN_X = 72                        # 左右安全边距
FONT_BOLD = r'C:\Windows\Fonts\msyhbd.ttc'
FONT_REG = r'C:\Windows\Fonts\msyh.ttc'
BRAND = '芜湖市科技创新新闻收集平台'

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
OUT_DIR = os.path.join(ROOT, 'web', 'static', 'images', 'banner')

# 频道 → 配色（深→浅渐变），让不同主题的横幅有辨识度
THEMES = {
    'policy':      ((142, 20, 20),  (198, 40, 40)),
    'platform':    ((74, 20, 140),  (123, 31, 162)),
    'enterprise':  ((13, 71, 161),  (25, 118, 210)),
    'achievement': ((0, 105, 92),   (0, 137, 123)),
    'talent':      ((191, 54, 12),  (244, 81, 30)),
    'park':        ((27, 94, 32),   (56, 142, 60)),
    'notice':      ((78, 52, 46),   (141, 110, 99)),
    'learn':       ((26, 35, 126),  (57, 73, 171)),
}
DEFAULT_THEME = ((142, 20, 20), (198, 40, 40))


# ---------------- 后端访问 ----------------
class Api(object):
    def __init__(self, base):
        self.base = base.rstrip('/')
        self.s = requests.Session()
        self.s.headers.update({'User-Agent': 'banner-generator/1.0'})

    def banner_list(self):
        r = self.s.post(self.base + '/api/banner', timeout=20)
        r.raise_for_status()
        data = r.json()
        if data.get('code') != 0:
            raise RuntimeError('接口返回异常：%s' % data.get('msg'))
        return data.get('data') or []

    def news_detail(self, news_id):
        r = self.s.post(self.base + '/api/detail',
                        data={'id': news_id, 'page_size': 1}, timeout=20)
        r.raise_for_status()
        return (r.json() or {}).get('data') or {}

    def admin_login(self, mobile, password):
        r = self.s.post(self.base + '/admin/api/login',
                        data={'mobile': mobile, 'password': password}, timeout=20)
        j = r.json()
        if j.get('code') != 0:
            raise RuntimeError('管理员登录失败：%s' % j.get('msg'))
        return j['data']['token']

    def banner_save(self, token, banner_id, image_url):
        r = self.s.post(self.base + '/admin/api/banner/save',
                        data={'id': banner_id, 'image_url': image_url},
                        headers={'X-Admin-Token': token}, timeout=20)
        j = r.json()
        if j.get('code') != 0:
            raise RuntimeError('回写失败(id=%s)：%s' % (banner_id, j.get('msg')))


# ---------------- 文本处理 ----------------
def wrap(text, font, max_width, draw, max_lines=3):
    """按像素宽度贪心折行；超出 max_lines 时最后一行加省略号"""
    text = re.sub(r'\s+', ' ', (text or '').strip())
    if not text:
        return []
    lines, cur = [], ''
    for ch in text:
        if draw.textlength(cur + ch, font=font) <= max_width:
            cur += ch
        else:
            lines.append(cur)
            cur = ch
            if len(lines) == max_lines:
                break
    if len(lines) < max_lines and cur:
        lines.append(cur)
    if len(lines) == max_lines and draw.textlength(cur, font=font) > 0 and len(''.join(lines)) < len(text):
        # 还有剩余文字：最后一行截断加省略号
        last = lines[-1]
        while last and draw.textlength(last + '…', font=font) > max_width:
            last = last[:-1]
        lines[-1] = last + '…'
    return lines


def pick_title_font(draw, title, max_width, max_lines=3):
    """字号自适应：从 78 逐步降到 54，找到能放下（不超过 max_lines 行）的字号"""
    for size in (78, 72, 66, 60, 54):
        font = ImageFont.truetype(FONT_BOLD, size)
        lines = wrap(title, font, max_width, draw, max_lines)
        if lines and len(lines) <= max_lines and not lines[-1].endswith('…'):
            return font, lines, size
    font = ImageFont.truetype(FONT_BOLD, 54)
    return font, wrap(title, font, max_width, draw, max_lines), 54


# ---------------- 绘图 ----------------
def gradient(size, c1, c2):
    img = Image.new('RGB', size, c1)
    d = ImageDraw.Draw(img)
    for y in range(size[1]):
        t = y / float(max(size[1] - 1, 1))
        d.line([(0, y), (size[0], y)],
               fill=(int(c1[0] + (c2[0] - c1[0]) * t),
                     int(c1[1] + (c2[1] - c1[1]) * t),
                     int(c1[2] + (c2[2] - c1[2]) * t)))
    return img


def decorate(img):
    layer = Image.new('RGBA', img.size, (255, 255, 255, 0))
    d = ImageDraw.Draw(layer)
    cx, cy = int(W * 0.86), int(H * 0.52)
    for r, a in ((300, 26), (230, 30), (160, 34), (92, 40)):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 255, 255, a), width=3)
    d.ellipse([cx - 34, cy - 34, cx + 34, cy + 34], fill=(255, 255, 255, 46))
    d.polygon([(W * 0.60, H), (W * 0.80, 0), (W * 0.88, 0), (W * 0.68, H)],
              fill=(255, 255, 255, 16))
    return Image.alpha_composite(img.convert('RGBA'), layer)


def build_image(banner, news, title_only=False):
    """生成一张横幅，返回 (Image, 排版信息)"""
    theme = THEMES.get(_code_of(news), DEFAULT_THEME)
    img = decorate(gradient((W, H), theme[0], theme[1]))
    d = ImageDraw.Draw(img)

    f_brand = ImageFont.truetype(FONT_REG, 30)
    f_sub = ImageFont.truetype(FONT_REG, 34)
    f_src = ImageFont.truetype(FONT_REG, 30)
    f_badge = ImageFont.truetype(FONT_BOLD, 30)

    # 左上：平台名
    d.text((MARGIN_X, 52), BRAND, font=f_brand, fill=(255, 255, 255, 210))

    # 右上：AI 徽标
    label = 'AI 实时摘要'
    tw = d.textlength(label, font=f_badge)
    bx1 = W - MARGIN_X - (tw + 56)
    d.rounded_rectangle([bx1, 46, W - MARGIN_X, 102], radius=28, fill=(255, 255, 255, 205))
    d.text((bx1 + 28, 58), label, font=f_badge, fill=theme[0])

    # 标题来源：默认用关联新闻标题（信息量更大），--title-only 时用 banner 标题
    title = (banner.get('title') or '').strip()
    if not title_only and news and (news.get('title') or '').strip():
        title = news['title'].strip()

    max_w = W - MARGIN_X * 2 - 40
    f_title, lines, size = pick_title_font(d, title, max_w)

    # 标题垂直居中于 170~430 区域
    line_h = int(size * 1.24)
    block_h = line_h * len(lines)
    y = 190 + max(0, (240 - block_h) // 2)
    for line in lines:
        d.text((MARGIN_X, y), line, font=f_title, fill=(255, 255, 255, 255))
        y += line_h

    # 副标题：频道 · AI关键词（去掉与频道名重复的、过长的关键词，整体超宽则省略）
    sub_parts = []
    cat = (news or {}).get('category_name') or ''
    if cat:
        sub_parts.append(cat)
    kw = (news or {}).get('ai_keywords') or ''
    for k in [x.strip() for x in re.split(r'[,，]', kw) if x.strip()]:
        if k == cat or k in sub_parts:
            continue
        sub_parts.append(k[:12])
        if len(sub_parts) >= 4:
            break
    sub = ' · '.join(sub_parts) if sub_parts else (banner.get('title') or '')
    max_sub_w = W - MARGIN_X * 2 - 40
    while sub and d.textlength(sub, font=f_sub) > max_sub_w:
        sub = sub[:-2] + '…'
    if sub:
        d.text((MARGIN_X + 4, y + 12), sub, font=f_sub, fill=(255, 255, 255, 215))

    # 底部来源行
    src_bits = []
    if news and news.get('origin'):
        src_bits.append('来源：' + news['origin'])
    pt = (news or {}).get('publish_time') or ''
    if pt:
        src_bits.append(pt[:10])
    model = (news or {}).get('ai_model') or ''
    # 只展示真实大模型名，演示种子数据（demo-seed）不显示
    if model and model != 'demo-seed' and not model.startswith('extractive'):
        src_bits.append('摘要：' + model)
    if src_bits:
        d.text((MARGIN_X, H - 76), ' · '.join(src_bits), font=f_src, fill=(255, 255, 255, 190))

    info = {'title': title, 'lines': lines, 'font': size, 'sub': sub,
            'src': ' · '.join(src_bits), 'news_id': (news or {}).get('id')}
    return img, info


def _code_of(news):
    """把频道名映射回主题键（detail 接口给的是中文名）"""
    name = (news or {}).get('category_name') or ''
    for code, cn in (('policy', '科技政策'), ('platform', '创新平台'), ('enterprise', '企业创新'),
                     ('achievement', '成果转化'), ('talent', '人才引育'), ('park', '园区动态'),
                     ('notice', '通知公告'), ('learn', '他山之石')):
        if name == cn:
            return code
    return ''


# ---------------- 主流程 ----------------
def main():
    ap = argparse.ArgumentParser(description='从数据库标题自动生成轮播图')
    ap.add_argument('--api', default='http://127.0.0.1:9533', help='后端地址')
    ap.add_argument('--ids', default='', help='只生成指定 banner id，逗号分隔')
    ap.add_argument('--out-dir', default=OUT_DIR, help='输出目录')
    ap.add_argument('--title-only', action='store_true', help='只用 banner 标题，不取关联新闻标题')
    ap.add_argument('--update-api', action='store_true', help='生成后回写 banner.image_url')
    ap.add_argument('--admin-mobile', default='13800000001')
    ap.add_argument('--admin-password', default='admin123')
    ap.add_argument('--dry-run', action='store_true', help='只打印排版结果，不写文件')
    args = ap.parse_args()

    api = Api(args.api)
    try:
        banners = api.banner_list()
    except Exception as e:
        print('× 无法读取轮播数据（后端是否已启动？）：%s' % e)
        return 1
    if not banners:
        print('× 没有启用中的轮播记录')
        return 1

    want = set(int(x) for x in re.split(r'[,\s]+', args.ids) if x.strip()) if args.ids else None
    banners = [b for b in banners if want is None or int(b.get('id')) in want]
    if not banners:
        print('× 过滤后没有可生成的轮播')
        return 1

    token = api.admin_login(args.admin_mobile, args.admin_password) if args.update_api else None

    out_dir = os.path.abspath(args.out_dir)
    if not args.dry_run:
        os.makedirs(out_dir, exist_ok=True)

    print('后端：%s   待生成：%d 张   画布：%dx%d（比例 %.4f:1）'
          % (args.api, len(banners), W, H, W / float(H)))
    print('-' * 96)
    ok = 0
    for b in banners:
        bid = int(b.get('id'))
        news = {}
        if b.get('news_id'):
            try:
                news = api.news_detail(b['news_id'])
            except Exception as e:
                print('  ! banner %s 关联新闻 %s 读取失败：%s' % (bid, b.get('news_id'), e))
        img, info = build_image(b, news, args.title_only)
        rel = '/static/images/banner/banner-%d.png' % bid
        path = os.path.join(out_dir, 'banner-%d.png' % bid)
        if not args.dry_run:
            img.convert('RGB').save(path, 'PNG', optimize=True)
        print('  [%s] %s' % (bid, info['title'][:44]))
        print('        标题行数=%d 字号=%d | 副标题=%s' % (len(info['lines']), info['font'], info['sub'][:52]))
        print('        %s' % info['src'][:72])
        print('        输出=%s  %s' % (rel, '(dry-run)' if args.dry_run else '%.1f KB' % (os.path.getsize(path) / 1024.0)))
        if token:
            api.banner_save(token, bid, rel)
            print('        已回写 image_url')
        ok += 1
    print('-' * 96)
    print('完成：%d/%d 张%s' % (ok, len(banners), '（dry-run，未写文件）' if args.dry_run else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
