#!/bin/bash
# 启动 Chrome 并开启远程调试端口
# DrissionPage 可以接管这个浏览器，复用你的登录状态

echo "🚀 启动 Chrome (远程调试模式)..."
echo "   端口: 9222"
echo ""
echo "⚠️ 注意："
echo "   1. 请在打开的浏览器中登录小红书"
echo "   2. 登录成功后，运行爬虫脚本即可"
echo "   3. 不要关闭这个浏览器窗口"
echo ""

# macOS
if [[ "$OSTYPE" == "darwin"* ]]; then
    /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
        --remote-debugging-port=9222 \
        --user-data-dir="$HOME/.chrome-debug-profile" \
        --no-first-run \
        "https://www.xiaohongshu.com"
# Linux
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    google-chrome \
        --remote-debugging-port=9222 \
        --user-data-dir="$HOME/.chrome-debug-profile" \
        --no-first-run \
        "https://www.xiaohongshu.com"
else
    echo "❌ 不支持的操作系统: $OSTYPE"
    echo "   请手动启动 Chrome 并添加参数: --remote-debugging-port=9222"
fi
