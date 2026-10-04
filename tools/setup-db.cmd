@echo off
chcp 65001 >nul
setlocal
rem ============================================================
rem 初始化数据库（幂等，可重复执行）
rem   01_schema.sql 建表   02_seed.sql 频道/采集源/演示数据
rem 需要 mysql 客户端在 PATH 中，或修改下面的 MYSQL 变量
rem ============================================================
set MYSQL="C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe"
set DBARGS=--host=127.0.0.1 --port=3306 --user=root  --default-character-set=utf8mb4

echo [1/2] 建表 ...
%MYSQL% %DBARGS% --execute="source D:/news-collector/sql/01_schema.sql"
if errorlevel 1 goto :error

echo [2/2] 初始化数据 ...
%MYSQL% %DBARGS% --execute="source D:/news-collector/sql/02_seed.sql"
if errorlevel 1 goto :error

echo.
echo 完成。当前数据：
%MYSQL% %DBARGS% --database=news_collector -e "select (select count(*) from news) news, (select count(*) from news_category) categories, (select count(*) from crawl_source) sources, (select count(*) from banner) banners;"
goto :eof

:error
echo.
echo 执行失败，请检查 mysql 路径与账号密码。
exit /b 1
