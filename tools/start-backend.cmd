@echo off
chcp 65001 >nul
setlocal
rem ============================================================
rem 编译并启动后端（端口 9533）
rem   已启动时会先结束占用 9533 的进程
rem ============================================================
set JAVA_HOME=C:\Program Files\Java\jdk1.8.0_341
set MVN=D:\academy\maven\apache-maven-3.9.10\bin\mvn.cmd
set PROJ=D:\news-collector\api-server
set JAR=%PROJ%\target\news-collector-1.0.jar

echo [1/3] 结束占用 9533 的进程 ...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":9533" ^| findstr LISTENING') do taskkill /f /pid %%p >nul 2>&1
timeout /t 2 /nobreak >nul

echo [2/3] 编译 ...
call "%MVN%" -s D:\news-collector\tools\mvn-settings.xml -f "%PROJ%\pom.xml" -DskipTests clean package
if errorlevel 1 goto :error

echo [3/3] 启动 ...
start "news-collector" /min "%JAVA_HOME%\bin\java.exe" -Dfile.encoding=UTF-8 -jar "%JAR%"
timeout /t 8 /nobreak >nul

echo.
echo 业务接口 : http://localhost:9533/api/getCategory
echo 管理后台 : http://localhost:9533/admin/index.html  (13800000001 / admin123)
echo 演示账号 : 13800000000 / 123456
goto :eof

:error
echo 编译失败。
exit /b 1
