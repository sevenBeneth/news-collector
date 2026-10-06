-- ============================================================
-- 初始化数据：频道、采集源、演示新闻、Banner
-- 幂等：使用 INSERT ... ON DUPLICATE KEY UPDATE / 编码唯一键
-- ============================================================
USE `news_collector`;

-- ------------------------------------------------------------
-- 1. 频道（8 个）
-- ------------------------------------------------------------
INSERT INTO `news_category` (`name`,`code`,`sort`,`enable`) VALUES
  ('科技政策','policy',1,1),
  ('创新平台','platform',2,1),
  ('企业创新','enterprise',3,1),
  ('成果转化','achievement',4,1),
  ('人才引育','talent',5,1),
  ('园区动态','park',6,1),
  ('通知公告','notice',7,1),
  ('他山之石','learn',8,1)
ON DUPLICATE KEY UPDATE `name`=VALUES(`name`), `sort`=VALUES(`sort`);

-- ------------------------------------------------------------
-- 2. 采集源（芜湖本地，实测可抓取）
--    adapter 说明：
--      wuhu_kjj_list  : 芜湖市科技局列表页（服务端渲染，20条/页）
--      wuhu_gov_rss   : 芜湖市人民政府 RSS
--      wuhu_gov_list  : 芜湖市人民政府新闻中心列表页
--      wuhunews_list  : 芜湖新闻网列表页（?pp= 翻页）
-- ------------------------------------------------------------
INSERT INTO `crawl_source`
  (`id`,`name`,`adapter`,`list_url`,`default_category_code`,`keyword_filter`,`max_pages`,`enable`,`sort`,`remark`) VALUES
  (1,'芜湖市科技局-通知公告','wuhu_kjj_list','https://kjj.wuhu.gov.cn/gg/tzgg/index.html','notice',NULL,1,1,1,'政策申报/公示类，时效性强'),
  (2,'芜湖市科技局-工作动态','wuhu_kjj_list','https://kjj.wuhu.gov.cn/gg/gzdt/index.html','policy',NULL,1,1,2,'科技局日常工作'),
  (3,'芜湖市科技局-科技要闻','wuhu_kjj_list','https://kjj.wuhu.gov.cn/gg/kjyw/index.html','learn','科技创新,科创,高新技术,人工智能,机器人,成果转化,专利,实验室,数字经济,鸠兹科创湾,科技,研发,算力',1,1,3,'多为省级以上媒体转载，需关键词过滤'),
  (4,'芜湖市科技局-县区科技','wuhu_kjj_list','https://kjj.wuhu.gov.cn/gg/xqkj/index.html','park',NULL,1,1,4,'各区县科技动态'),
  (5,'芜湖市政府-新闻RSS','wuhu_gov_rss','https://www.wuhu.gov.cn/rss/rss.xml?siteId=6787231','policy','科技创新,科创,高新技术,人工智能,机器人,成果转化,专利,实验室,数字经济,鸠兹科创湾,科技,研发,算力',1,1,5,'官方RSS，自带摘要，最稳定；仅保留科技类'),
  (6,'芜湖市政府-芜湖要闻','wuhu_gov_list','https://www.wuhu.gov.cn/xwzx/zwyw/index.html','policy','科技创新,科创,高新技术,人工智能,机器人,成果转化,专利,实验室,数字经济,鸠兹科创湾,科技,研发,算力',1,1,6,'分页为JS渲染，仅抓第1页；仅保留科技类'),
  (7,'芜湖市政府-部门动态','wuhu_gov_list','https://www.wuhu.gov.cn/xwzx/bmdt/index.html','enterprise','科技创新,科创,高新技术,人工智能,机器人,成果转化,专利,实验室,数字经济,鸠兹科创湾,科技,研发,算力',1,1,7,'分页为JS渲染，仅抓第1页；仅保留科技类'),
  (8,'芜湖新闻网-要闻','wuhunews_list','https://www.wuhunews.cn/yaowen/','enterprise','科技创新,科创,高新技术,人工智能,机器人,成果转化,专利,实验室,数字经济,鸠兹科创湾,科技,研发,算力',3,1,8,'支持 ?pp= 翻页；关键词过滤'),
  (9,'芜湖新闻网-大江资讯','wuhunews_list','https://www.wuhunews.cn/djzx/','enterprise','科技创新,科创,高新技术,人工智能,机器人,成果转化,专利,实验室,数字经济,鸠兹科创湾,科技,研发,算力',1,1,9,'该栏目 ?pp= 翻页失效，仅抓第1页')
ON DUPLICATE KEY UPDATE
  `name`=VALUES(`name`), `adapter`=VALUES(`adapter`), `list_url`=VALUES(`list_url`),
  `default_category_code`=VALUES(`default_category_code`), `keyword_filter`=VALUES(`keyword_filter`),
  `max_pages`=VALUES(`max_pages`), `sort`=VALUES(`sort`), `remark`=VALUES(`remark`);

-- ------------------------------------------------------------
-- 3. 演示新闻（保证首次启动页面非空，后续被采集数据覆盖扩充）
-- ------------------------------------------------------------
INSERT INTO `news`
  (`title`,`source_url`,`content`,`photo_url`,`origin`,`publish_time`,`category_id`,`ai_summary`,`ai_keywords`,`ai_status`,`ai_model`,`status`,`slider`,`read_count`)
VALUES
  ('芜湖"鸠兹科创湾"开园 打造长三角场景创新高地',
   'https://example.local/demo/1',
   '芜湖市"鸠兹科创湾"正式开园，聚焦场景创新与成果转化，首批入驻一批创新平台与科技型企业。芜湖将依托该平台推动新技术新产品在本地的先行先试，形成"场景牵引—技术验证—产业落地"的闭环。',
   '/static/images/banner/banner-1.png',
   '芜湖市科技局','2026-09-20 09:00:00',
   (SELECT id FROM news_category WHERE code='platform' LIMIT 1),
   '芜湖"鸠兹科创湾"开园，定位场景创新与成果转化，通过"场景牵引—技术验证—产业落地"闭环推动新技术先行先试。',
   '鸠兹科创湾,场景创新,成果转化',1,'demo-seed',1,1,128),
  ('芜湖市启动2026年度高新技术企业认定申报工作',
   'https://example.local/demo/2',
   '芜湖市科技局发布通知，启动2026年度全市高新技术企业认定申报工作，明确申报条件、材料清单与时间节点，并要求各县市区科技管理部门做好辅导服务。',
   '/static/images/banner/banner-2.png',
   '芜湖市科技局','2026-05-01 10:00:00',
   (SELECT id FROM news_category WHERE code='policy' LIMIT 1),
   '芜湖市启动2026年度高新技术企业认定申报，明确申报条件、材料与时间节点，并要求县区做好企业辅导。',
   '高新技术企业,认定申报,科技政策',1,'demo-seed',1,0,96),
  ('芜湖造航空发动机亮相2026世界制造业大会',
   'https://example.local/demo/3',
   '在2026世界制造业大会上，芜湖企业展出的航空发动机产品受到关注，体现了芜湖在航空装备与高端制造领域的产业积累与创新能力的持续提升。',
   '/static/images/banner/banner-3.png',
   '芜湖新闻网','2026-10-01 08:00:00',
   (SELECT id FROM news_category WHERE code='enterprise' LIMIT 1),
   '芜湖航空发动机产品亮相2026世界制造业大会，反映本地航空装备与高端制造领域的产业积累与创新能力。',
   '航空发动机,世界制造业大会,高端制造',1,'demo-seed',1,0,75)
ON DUPLICATE KEY UPDATE `title`=VALUES(`title`);

-- ------------------------------------------------------------
-- 4. Banner（关联演示新闻，后续可在管理页替换为真实图片）
-- ------------------------------------------------------------
INSERT INTO `banner` (`id`,`title`,`image_url`,`news_id`,`sort`,`enable`) VALUES
  (1,'鸠兹科创湾开园',          '/static/images/banner/banner-1.png',
      (SELECT id FROM news WHERE source_url='https://example.local/demo/1' LIMIT 1),1,1),
  (2,'2026年度高新技术企业申报','/static/images/banner/banner-2.png',
      (SELECT id FROM news WHERE source_url='https://example.local/demo/2' LIMIT 1),2,1),
  (3,'芜湖造航空发动机亮相',    '/static/images/banner/banner-3.png',
      (SELECT id FROM news WHERE source_url='https://example.local/demo/3' LIMIT 1),3,1)
ON DUPLICATE KEY UPDATE `title`=VALUES(`title`), `image_url`=VALUES(`image_url`);
