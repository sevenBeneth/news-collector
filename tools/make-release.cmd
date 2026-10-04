@echo off
chcp 65001 >nul
setlocal
rem ============================================================
rem 打包提交物：源码压缩包 + 数据库导出
rem   输出到 D:\news-collector-release\
rem ============================================================
set SRC=D:\news-collector
set OUT=D:\news-collector-release
set STAMP=%date:~0,4%%date:~5,2%%date:~8,2%
set MYSQL="C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe"
set MYSQLDUMP="C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe"

if not exist "%OUT%" mkdir "%OUT%"

echo [1/3] 导出数据库 ...
"%MYSQLDUMP%" --host=127.0.0.1 --user=root  --default-character-set=utf8mb4 ^
  --single-transaction --routines --triggers news_collector > "%OUT%\news_collector_dump_%STAMP%.sql"
if errorlevel 1 echo   数据库导出失败（可手动导出）

echo [2/3] 清理临时文件 ...
if exist "%SRC%\crawler\__pycache__" rmdir /s /q "%SRC%\crawler\__pycache__"
if exist "%SRC%\api-server\target" echo   注意：api-server\target 不会打入压缩包

echo [3/3] 打包源码 ...
powershell -NoProfile -Command "Compress-Archive -Path '%SRC%\api-server','%SRC%\crawler','%SRC%\web','%SRC%\sql','%SRC%\docs','%SRC%\tools','%SRC%\README.md' -DestinationPath '%OUT%\news-collector-src-%STAMP%.zip' -Force -CompressionLevel Optimal"
if errorlevel 1 goto :error

echo.
echo 完成，输出目录：%OUT%
dir /b "%OUT%"
goto :eof

:error
echo 打包失败。
exit /b 1
