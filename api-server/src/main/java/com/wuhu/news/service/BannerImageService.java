package com.wuhu.news.service;

import com.wuhu.news.entity.Banner;
import com.wuhu.news.vo.NewsDetailVO;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import javax.imageio.ImageIO;
import java.awt.*;
import java.awt.image.BufferedImage;
import java.io.File;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 轮播图生成服务（Java2D 绘制，不依赖任何外部脚本与第三方库）
 *
 * 设计要点：
 *  - 画布 1500×640，比例 2.34375:1，与前端滑动框 750rpx×320rpx 完全一致（aspectFill 不裁切）
 *  - 文案来自数据库：优先用关联新闻的真实标题，自动折行 + 字号自适应
 *  - 副标题 = 频道 + AI 关键词，来源行 = 来源 · 日期 · 模型
 *  - 按频道配色，右侧科技感装饰，左上平台名，右上“AI 实时摘要”徽标
 *  - 输出到配置目录（默认 ../web/static/images/banner），并把 image_url 回写 banner 表
 */
@Slf4j
@Service
public class BannerImageService {

    private static final int W = 1500;
    private static final int H = 640;
    private static final int MARGIN_X = 72;
    private static final String BRAND = "芜湖市科技创新新闻收集平台";
    private static final String BADGE = "AI 实时摘要";

    /** 频道配色：深色 → 浅色（纵向渐变） */
    private static final Map<String, Color[]> THEMES = new LinkedHashMap<>();
    static {
        THEMES.put("科技政策", new Color[]{new Color(142, 20, 20), new Color(198, 40, 40)});
        THEMES.put("创新平台", new Color[]{new Color(74, 20, 140), new Color(123, 31, 162)});
        THEMES.put("企业创新", new Color[]{new Color(13, 71, 161), new Color(25, 118, 210)});
        THEMES.put("成果转化", new Color[]{new Color(0, 105, 92), new Color(0, 137, 123)});
        THEMES.put("人才引育", new Color[]{new Color(191, 54, 12), new Color(244, 81, 30)});
        THEMES.put("园区动态", new Color[]{new Color(27, 94, 32), new Color(56, 142, 60)});
        THEMES.put("通知公告", new Color[]{new Color(78, 52, 46), new Color(141, 110, 99)});
        THEMES.put("他山之石", new Color[]{new Color(26, 35, 126), new Color(57, 73, 171)});
    }
    private static final Color[] DEFAULT_THEME = new Color[]{new Color(142, 20, 20), new Color(198, 40, 40)};

    /** 中文字体候选（Windows / Linux 通用顺序） */
    private static final String[] FONT_FAMILIES = {
            "Microsoft YaHei", "微软雅黑", "SimHei", "黑体", "Noto Sans CJK SC",
            "Source Han Sans SC", "WenQuanYi Zen Hei", "PingFang SC", "SansSerif"
    };

    @Value("${app.banner.dir:../web/static/images/banner}")
    private String bannerDir;

    private static volatile String cachedFamily;

    /** 生成一张轮播图，返回可直接给前端使用的相对路径 */
    public String render(Banner banner, NewsDetailVO news) throws Exception {
        File dir = new File(bannerDir);
        if (!dir.isAbsolute()) {
            dir = new File(System.getProperty("user.dir"), bannerDir);
        }
        if (!dir.exists() && !dir.mkdirs()) {
            throw new IllegalStateException("无法创建输出目录：" + dir.getAbsolutePath());
        }
        BufferedImage img = new BufferedImage(W, H, BufferedImage.TYPE_INT_RGB);
        Graphics2D g = img.createGraphics();
        try {
            g.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
            g.setRenderingHint(RenderingHints.KEY_TEXT_ANTIALIASING, RenderingHints.VALUE_TEXT_ANTIALIAS_ON);
            g.setRenderingHint(RenderingHints.KEY_STROKE_CONTROL, RenderingHints.VALUE_STROKE_PURE);

            Color[] theme = THEMES.getOrDefault(categoryOf(news), DEFAULT_THEME);
            // 1) 渐变底色
            g.setPaint(new GradientPaint(0, 0, theme[0], 0, H, theme[1]));
            g.fillRect(0, 0, W, H);
            // 2) 右侧科技感装饰
            drawDecoration(g);
            // 3) 左上平台名 + 右上徽标
            Font brandFont = font(Font.PLAIN, 30);
            g.setFont(brandFont);
            g.setColor(new Color(255, 255, 255, 210));
            g.drawString(BRAND, MARGIN_X, 52 + g.getFontMetrics().getAscent());

            Font badgeFont = font(Font.BOLD, 30);
            g.setFont(badgeFont);
            FontMetrics bfm = g.getFontMetrics();
            int badgeW = bfm.stringWidth(BADGE) + 56;
            int bx = W - MARGIN_X - badgeW;
            g.setColor(new Color(255, 255, 255, 205));
            g.fillRoundRect(bx, 46, badgeW, 56, 28, 28);
            g.setColor(theme[0]);
            g.drawString(BADGE, bx + 28, 46 + 12 + bfm.getAscent());
            // 4) 标题：优先关联新闻标题，自动折行 + 字号自适应
            String title = news != null && !StringUtils.isEmpty(news.getTitle())
                    ? news.getTitle() : banner.getTitle();
            int maxW = W - MARGIN_X * 2 - 40;
            TitleBlock block = layoutTitle(g, title, maxW);
            int lineH = (int) (block.size * 1.24);
            int blockH = lineH * block.lines.size();
            int blockTop = 190 + Math.max(0, (240 - blockH) / 2);
            int y = blockTop;
            for (String line : block.lines) {
                g.setColor(Color.WHITE);
                g.drawString(line, MARGIN_X, y + g.getFontMetrics().getAscent());
                y += lineH;
            }
            // 5) 副标题：频道 · AI关键词
            String sub = buildSubtitle(banner, news);
            if (!StringUtils.isEmpty(sub)) {
                g.setFont(font(Font.PLAIN, 34));
                g.setColor(new Color(255, 255, 255, 215));
                sub = clip(g, sub, maxW);
                g.drawString(sub, MARGIN_X + 4, y + 12 + g.getFontMetrics().getAscent());
            }
            // 6) 底部来源行
            String src = buildSource(news);
            if (!StringUtils.isEmpty(src)) {
                g.setFont(font(Font.PLAIN, 30));
                g.setColor(new Color(255, 255, 255, 190));
                g.drawString(clip(g, src, maxW), MARGIN_X, H - 76 + g.getFontMetrics().getAscent());
            }
        } finally {
            g.dispose();
        }
        File out = new File(dir, "banner-" + banner.getId() + ".png");
        ImageIO.write(img, "png", out);
        String url = "/static/images/banner/banner-" + banner.getId() + ".png";
        log.info("轮播图已生成：{} -> {} ({} KB)", url, out.getAbsolutePath(), out.length() / 1024);
        return url;
    }

    // ---------------- 内部实现 ----------------

    private void drawDecoration(Graphics2D g) {
        int cx = (int) (W * 0.86);
        int cy = (int) (H * 0.52);
        g.setStroke(new BasicStroke(3f));
        int[][] rings = {{300, 26}, {230, 30}, {160, 34}, {92, 40}};
        for (int[] ring : rings) {
            g.setColor(new Color(255, 255, 255, ring[1]));
            int r = ring[0];
            g.drawOval(cx - r, cy - r, r * 2, r * 2);
        }
        g.setColor(new Color(255, 255, 255, 46));
        g.fillOval(cx - 34, cy - 34, 68, 68);
        g.setColor(new Color(255, 255, 255, 16));
        g.fillPolygon(new int[]{(int) (W * 0.60), (int) (W * 0.80), (int) (W * 0.88), (int) (W * 0.68)},
                new int[]{H, 0, 0, H}, 4);
    }

    /** 标题排版：字号从 78 递减到 54，找出能完整放下的最大字号 */
    private TitleBlock layoutTitle(Graphics2D g, String text, int maxW) {
        String t = text == null ? "" : text.replaceAll("\\s+", " ").trim();
        for (int size : new int[]{78, 72, 66, 60, 54}) {
            g.setFont(font(Font.BOLD, size));
            FontMetrics fm = g.getFontMetrics();
            List<String> lines = wrap(t, fm, maxW, 3);
            boolean truncated = !lines.isEmpty() && lines.get(lines.size() - 1).endsWith("…");
            if (!truncated) {
                return new TitleBlock(lines, size);
            }
        }
        g.setFont(font(Font.BOLD, 54));
        return new TitleBlock(wrap(t, g.getFontMetrics(), maxW, 3), 54);
    }

    /** 按像素宽度折行；超过 maxLines 时最后一行加省略号 */
    private List<String> wrap(String text, FontMetrics fm, int maxW, int maxLines) {
        List<String> lines = new ArrayList<>();
        if (StringUtils.isEmpty(text)) {
            return lines;
        }
        StringBuilder cur = new StringBuilder();
        for (int i = 0; i < text.length(); i++) {
            char ch = text.charAt(i);
            if (fm.stringWidth(cur.toString() + ch) <= maxW) {
                cur.append(ch);
            } else {
                lines.add(cur.toString());
                cur.setLength(0);
                cur.append(ch);
                if (lines.size() == maxLines) {
                    break;
                }
            }
        }
        if (lines.size() < maxLines && cur.length() > 0) {
            lines.add(cur.toString());
        }
        if (lines.size() == maxLines) {
            String joined = String.join("", lines);
            if (joined.length() < text.length()) {
                String last = lines.get(maxLines - 1);
                while (last.length() > 1 && fm.stringWidth(last + "…") > maxW) {
                    last = last.substring(0, last.length() - 1);
                }
                lines.set(maxLines - 1, last + "…");
            }
        }
        return lines;
    }

    private String buildSubtitle(Banner banner, NewsDetailVO news) {
        List<String> parts = new ArrayList<>();
        String cat = news == null ? null : news.getCategory_name();
        if (!StringUtils.isEmpty(cat)) {
            parts.add(cat);
        }
        String kw = news == null ? null : news.getAi_keywords();
        if (!StringUtils.isEmpty(kw)) {
            for (String k : kw.split("[,，]")) {
                String v = k.trim();
                if (v.isEmpty() || v.equals(cat) || parts.contains(v)) {
                    continue;
                }
                parts.add(v.length() > 12 ? v.substring(0, 12) : v);
                if (parts.size() >= 4) {
                    break;
                }
            }
        }
        if (parts.isEmpty()) {
            return banner.getTitle();
        }
        return String.join(" · ", parts);
    }

    private String buildSource(NewsDetailVO news) {
        List<String> bits = new ArrayList<>();
        if (news != null) {
            if (!StringUtils.isEmpty(news.getOrigin())) {
                bits.add("来源：" + news.getOrigin());
            }
            if (news.getPublish_time() != null) {
                bits.add(new SimpleDateFormat("yyyy-MM-dd").format(news.getPublish_time()));
            }
            String model = news.getAi_model();
            // 演示种子数据与降级摘要不显示为模型名
            if (!StringUtils.isEmpty(model) && !"demo-seed".equals(model) && !model.startsWith("extractive")) {
                bits.add("摘要：" + model);
            }
        }
        return String.join(" · ", bits);
    }

    private String categoryOf(NewsDetailVO news) {
        return news == null || news.getCategory_name() == null ? "" : news.getCategory_name();
    }

    private String clip(Graphics2D g, String text, int maxW) {
        FontMetrics fm = g.getFontMetrics();
        if (fm.stringWidth(text) <= maxW) {
            return text;
        }
        String t = text;
        while (t.length() > 1 && fm.stringWidth(t + "…") > maxW) {
            t = t.substring(0, t.length() - 1);
        }
        return t + "…";
    }

    /** 选择能显示中文的字体族（结果缓存，避免每次遍历） */
    private static Font font(int style, int size) {
        if (cachedFamily == null) {
            synchronized (BannerImageService.class) {
                if (cachedFamily == null) {
                    cachedFamily = pickFamily();
                }
            }
        }
        return new Font(cachedFamily, style, size);
    }

    private static String pickFamily() {
        List<String> available = Arrays.asList(GraphicsEnvironment.getLocalGraphicsEnvironment()
                .getAvailableFontFamilyNames());
        for (String candidate : FONT_FAMILIES) {
            for (String name : available) {
                if (name.equalsIgnoreCase(candidate)) {
                    Font f = new Font(name, Font.PLAIN, 20);
                    if (f.canDisplay('芜') && f.canDisplay('科')) {
                        log.info("轮播图使用字体：{}", name);
                        return name;
                    }
                }
            }
        }
        log.warn("未找到可显示中文的字体，轮播图中文可能显示为方块（候选：{}）", Arrays.toString(FONT_FAMILIES));
        return "SansSerif";
    }

    /** 标题排版结果 */
    private static class TitleBlock {
        final List<String> lines;
        final int size;

        TitleBlock(List<String> lines, int size) {
            this.lines = lines;
            this.size = size;
        }
    }
}
