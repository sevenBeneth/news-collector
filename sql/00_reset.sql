-- ============================================================
-- 清空重建（会删除所有数据，仅在需要全新环境时使用）
-- 用法：mysql -uroot -p --default-character-set=utf8mb4 -e "source D:/news-collector/sql/00_reset.sql"
--       然后依次执行 01_schema.sql、02_seed.sql
-- ============================================================
DROP DATABASE IF EXISTS `news_collector`;
