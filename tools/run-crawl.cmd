@echo off
chcp 65001 >nul
setlocal
rem ============================================================
rem 运行采集器
rem   run-crawl.cmd              全量采集（所有启用源）
rem   run-crawl.cmd --dry-run    只抓取不写库
rem   run-crawl.cmd --source-id 1 --limit 5
rem
rem 定时采集：用「任务计划程序」新建任务，操作填
rem   D:\news-collector\tools\run-crawl.cmd
rem 触发器建议每天 08:30 与 12:30 各一次
rem ============================================================
cd /d D:\news-collector\crawler
python run.py %*
