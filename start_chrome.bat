@echo off
:: ============================================================================
:: 启动 Chrome 并开启远程调试端口 (Windows版)
:: 作用: 开启9222端口，让 Python 爬虫可以接管浏览器，复用登录状态
:: ============================================================================

setlocal

echo.
echo ============================================================================
echo  🚀 启动 Chrome (远程调试模式)...
echo  端口: 9222
echo ============================================================================
echo.
echo  ⚠️ 注意：
echo     1. 请在打开的浏览器中登录小红书 (https://www.xiaohongshu.com)
echo     2. 登录成功后，保持浏览器开启，然后运行 Python 爬虫脚本
echo     3. 如果 Chrome 没有启动，请检查安装路径是否正确
echo.

:: 设置用户数据目录 (用于保存登录状态，避免每次都要登录)
set "USER_DATA_DIR=%USERPROFILE%\.chrome-debug-profile"

:: 尝试常见的 Chrome 安装路径
set "CHROME_PATH="

if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    set "CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe"
) else if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
    set "CHROME_PATH=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
) else if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" (
    set "CHROME_PATH=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
)

if "%CHROME_PATH%"=="" (
    echo ❌ 未找到 Chrome 安装路径，请手动修改脚本中的路径！
    echo.
    pause
    exit /b 1
)

echo  ✅ 找到 Chrome: "%CHROME_PATH%"
echo  📂 用户数据目录: "%USER_DATA_DIR%"
echo.

:: 启动 Chrome
:: --remote-debugging-port=9222 : 开启调试端口
:: --user-data-dir : 指定独立的配置目录，不影响日常使用的 Chrome
:: --no-first-run : 跳过首次运行向导
start "" "%CHROME_PATH%" --remote-debugging-port=9222 --user-data-dir="%USER_DATA_DIR%" --no-first-run "https://www.xiaohongshu.com"

echo  🎉 Chrome 已启动！请扫码登录。
echo.
pause
