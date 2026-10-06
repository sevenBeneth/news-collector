#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
产品信息架构思维导图生成器

从结构化定义生成：
  1) docs/信息架构图.png     —— 思维导图图片（可直接放进录屏/提交材料）
  2) docs/信息架构图.mm      —— FreeMind 格式，可导入 XMind / ProcessOn 继续编辑

布局：左→右横向树，根节点在左，五条主干分色，曲线连接，画布尺寸自适应。
用法：python tools/gen_mindmap.py
"""
import os
import xml.sax.saxutils as sax
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
OUT_PNG = os.path.join(ROOT, 'docs', '信息架构图.png')
OUT_MM = os.path.join(ROOT, 'docs', '信息架构图.mm')

FONT_BOLD = r'C:\Windows\Fonts\msyhbd.ttc'
FONT_REG = r'C:\Windows\Fonts\msyh.ttc'

# 字号（2 倍图，便于打印与缩放）
FS = {0: 42, 1: 32, 2: 24}
PAD_X = {0: 34, 1: 26, 2: 18}
NODE_GAP_Y = {1: 22, 2: 12}      # 同级垂直间距
LEVEL_GAP_X = 90                 # 列间距
MARGIN = 70

BG = (255, 255, 255)
TXT_DARK = (40, 40, 40)

# 主干配色：(边框/填充深色, 浅色底)
BRANCH_COLORS = [
    ((198, 40, 40), (253, 238, 238)),    # 用户端 红
    ((21, 101, 192), (235, 244, 253)),   # 管理端 蓝
    ((46, 125, 50), (236, 247, 237)),    # 后端服务 绿
    ((239, 108, 0), (255, 244, 230)),    # 采集器 橙
    ((106, 27, 154), (246, 238, 252)),   # 数据层 紫
]

# ---------------- 信息架构定义 ----------------
TREE = {
    'text': '芜湖市科技创新新闻收集平台',
    'children': [
        {'text': '用户端（H5 / 微信小程序）', 'children': [
            {'text': '首页：轮播图 · 频道切换'},
            {'text': '信息流：标题 · AI摘要前40字 · 来源时间'},
            {'text': '搜索与频道列表'},
            {'text': '新闻详情：AI摘要卡片 · 正文 · 查看原文'},
            {'text': '互动：点赞 · 收藏 · 评论 · 回复'},
            {'text': '我的：资料 · 收藏 · 改密 · 反馈'},
            {'text': '账号：登录 · 注册 · 用户协议'},
        ]},
        {'text': '管理端（内置静态页）', 'children': [
            {'text': '数据看板：总量 · 待审 · AI成败'},
            {'text': '新闻管理：审核 · 编辑 · 重生成摘要'},
            {'text': '轮播管理：新增 · 排序 · 上下线'},
            {'text': '采集源与采集日志'},
            {'text': '用户管理：检索 · 启用禁用'},
        ]},
        {'text': '后端服务（Spring Boot）', 'children': [
            {'text': '用户端接口 /api/**'},
            {'text': '采集端接口 /api/ingest/**'},
            {'text': '管理端接口 /admin/api/**'},
            {'text': 'AI摘要服务（DeepSeek）'},
            {'text': '异步任务 · 跨域 · 统一返回体'},
        ]},
        {'text': '采集器（Python）', 'children': [
            {'text': '4类站点适配器（科技局/RSS/政府/新闻网）'},
            {'text': '正文抽取与编码归一'},
            {'text': '关键词过滤与双键去重'},
            {'text': '限速重试 · 采集日志'},
        ]},
        {'text': '数据层（MySQL news_collector）', 'children': [
            {'text': '内容：news · news_category · banner'},
            {'text': '互动：comment · user_action'},
            {'text': '用户：app_user'},
            {'text': '采集：crawl_source · crawl_log · ai_log'},
        ]},
    ]
}


class Node(object):
    def __init__(self, text, level=0, color=None):
        self.text = text
        self.level = level
        self.color = color
        self.children = []
        self.w = 0
        self.h = 0
        self.x = 0
        self.y = 0          # 中心线
        self.sub_h = 0      # 子树占用高度


def build(spec, level=0, color=None, idx=0):
    node = Node(spec['text'], level, color)
    for i, ch in enumerate(spec.get('children') or []):
        child_color = BRANCH_COLORS[i % len(BRANCH_COLORS)][0] if level == 0 else color
        node.children.append(build(ch, level + 1, child_color, i))
    return node


def measure(node, draw):
    font = ImageFont.truetype(FONT_BOLD if node.level <= 1 else FONT_REG, FS[node.level])
    tw = draw.textlength(node.text, font=font)
    node.w = int(tw + PAD_X[node.level] * 2)
    node.h = int(FS[node.level] * (1.9 if node.level == 0 else 1.75))
    for c in node.children:
        measure(c, draw)


def layout(node, draw, top):
    """自底向上分配高度，返回子树占用高度；同时设定中心线 y"""
    if not node.children:
        node.sub_h = node.h
    else:
        gap = NODE_GAP_Y.get(node.level + 1, 12)
        total = 0
        for c in node.children:
            total += layout(c, draw, top + total)
            total += gap
        total -= gap
        node.sub_h = max(node.h, total)
    node.y = top + node.sub_h / 2.0
    return node.sub_h


def assign_x(node, col_x):
    max_w = max(col_x.get(node.level, 0), node.w)
    col_x[node.level] = max_w
    for c in node.children:
        assign_x(c, col_x)


def place_x(node, col_x):
    node.x = sum(col_x[l] + LEVEL_GAP_X for l in range(0, node.level))
    for c in node.children:
        place_x(c, col_x)


def collect(node, out):
    out.append(node)
    for c in node.children:
        collect(c, out)
    return out


def draw_tree(node, draw):
    # 连线（先画线，节点覆盖其上）
    for c in node.children:
        color = c.color if c.level >= 1 else (150, 150, 150)
        x1 = node.x + node.w
        y1 = node.y
        x2 = c.x
        y2 = c.y
        mid = (x1 + x2) / 2.0
        draw.line([(x1, y1), (mid, y1)], fill=color, width=4)
        draw.line([(mid, y1), (mid, y2)], fill=color, width=4)
        draw.line([(mid, y2), (x2, y2)], fill=color, width=4)
        draw.ellipse([x2 - 6, y2 - 6, x2 + 6, y2 + 6], fill=color)
        draw_tree(c, draw)


def draw_node(node, draw, fonts):
    x1 = node.x
    y1 = node.y - node.h / 2.0
    x2 = node.x + node.w
    y2 = node.y + node.h / 2.0
    if node.level == 0:
        fill = (198, 40, 40)
        outline = (198, 40, 40)
        text_color = (255, 255, 255)
    else:
        outline = node.color or (120, 120, 120)
        fill = (255, 255, 255)
        text_color = TXT_DARK
    draw.rounded_rectangle([x1, y1, x2, y2], radius=int(node.h / 2.4),
                           fill=fill, outline=outline, width=4)
    font = fonts[node.level]
    tw = draw.textlength(node.text, font=font)
    draw.text((x1 + (node.w - tw) / 2.0, node.y - FS[node.level] * 0.62),
              node.text, font=font, fill=text_color)


def render_png():
    probe = ImageDraw.Draw(Image.new('RGB', (10, 10)))
    root = build(TREE)
    measure(root, probe)

    col_x = {}
    assign_x(root, col_x)
    place_x(root, col_x)
    layout(root, probe, MARGIN)

    nodes = collect(root, [])
    max_x = max(n.x + n.w for n in nodes) + MARGIN
    max_y = max(n.y + n.h / 2.0 for n in nodes) + MARGIN

    img = Image.new('RGB', (int(max_x), int(max_y)), BG)
    d = ImageDraw.Draw(img)
    # 分区底色：给每条主干一个浅色底，强化分组
    for i, c in enumerate(root.children):
        top = min(collect(c, [])[0].y for _ in [0]) - 0
        ys = [n.y for n in collect(c, [])]
        y1 = min(ys) - NODE_GAP_Y.get(1, 20)
        y2 = max(ys) + NODE_GAP_Y.get(1, 20)
        x1 = root.x + root.w + 20
        x2 = max(n.x + n.w for n in collect(c, [])) + 24
        d.rounded_rectangle([x1, y1, x2, y2], radius=24, fill=BRANCH_COLORS[i][1])
    # 主干标签色块（根节点右侧小三角装饰）
    draw_tree(root, d)
    fonts = {lvl: ImageFont.truetype(FONT_BOLD if lvl <= 1 else FONT_REG, FS[lvl]) for lvl in FS}
    for n in sorted(nodes, key=lambda x: -x.level):   # 先画子节点，根节点最后覆盖
        draw_node(n, d, fonts)

    os.makedirs(os.path.dirname(OUT_PNG), exist_ok=True)
    img.save(OUT_PNG, 'PNG', optimize=True)
    return img.size, len(nodes)


def render_mm():
    def node_xml(spec, indent=2):
        pad = ' ' * indent
        s = '%s<node TEXT="%s">\n' % (pad, sax.escape(spec['text']))
        for ch in spec.get('children') or []:
            s += node_xml(ch, indent + 2)
        s += '%s</node>\n' % pad
        return s

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<map version="1.0.1">\n' + node_xml(TREE) + '</map>\n'
    with open(OUT_MM, 'w', encoding='utf-8') as f:
        f.write(xml)
    return OUT_MM


if __name__ == '__main__':
    size, count = render_png()
    mm = render_mm()
    print('思维导图 PNG：%s  %dx%d  节点 %d 个  %.1f KB'
          % (OUT_PNG, size[0], size[1], count, os.path.getsize(OUT_PNG) / 1024.0))
    print('FreeMind 文件：%s  （可导入 XMind / ProcessOn 继续编辑）' % mm)
