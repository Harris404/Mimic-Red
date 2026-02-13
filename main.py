# -*- coding: utf-8 -*-
"""
DrissionPage 小红书批量爬虫 
核心策略：移除所有 API 监听 (降低特征) -> 纯 DOM 交互 (点击/滚动) -> 被动 SSR/DOM 提取
支持存储格式：CSV、JSON、Excel、SQLite
"""
import sys
import argparse
from loguru import logger
from xhs_utils.xhs_spider import DrissionXHSSpider

# 配置日志自动保存
logger.add("logs/spider_{time:YYYY-MM-DD}.log", rotation="1 day", retention="7 days", encoding="utf-8")

def main():
    parser = argparse.ArgumentParser(description="DrissionPage 小红书爬虫 ")
    parser.add_argument("--keywords", "-k", nargs="+", help="关键词列表")
    parser.add_argument("--limit", "-l", type=int, default=20, help="每个关键词最多爬取数量")
    parser.add_argument("--daily-limit", "-d", type=int, default=50,
                        help="每日最多爬取总数（推荐 50-100）")
    parser.add_argument("--min-likes", type=int, default=0,
                        help="最少点赞数过滤（跳过低互动笔记，减少请求）")
    parser.add_argument("--storage", "-s", type=str, default="sqlite",
                        choices=["csv", "json", "excel", "sqlite"],
                        help="存储格式 (csv/json/excel/sqlite，默认: sqlite)")
    parser.add_argument("--output", "-o", type=str, default="datas",
                        help="输出目录（默认: datas）")
    parser.add_argument("--no-warmup", action="store_true", help="跳过会话预热")
    parser.add_argument("--no-shuffle", action="store_true", help="不打乱关键词顺序")
    
    # 新增参数
    parser.add_argument("--ignore-progress", action="store_true", help="忽略历史进度（强制重新爬取）")
    parser.add_argument("--no-filter", action="store_true", help="关闭内容质量过滤（收集所有笔记）")
    parser.add_argument("--min-quality-score", type=int, default=20, help="最低质量分数（默认: 20，低于此分数的笔记将被跳过）")
    parser.add_argument("--static-comments", action="store_true", help="使用静态评论采集数量（关闭动态调整）")
    
    # 浏览器控制参数
    parser.add_argument("--new-browser", action="store_true", help="启动新浏览器实例（不接管现有浏览器）")
    parser.add_argument("--headless", action="store_true", help="无头模式运行（仅在启动新浏览器时有效）")
    
    args = parser.parse_args()
    
    # Use the imported DrissionXHSSpider class
    spider = DrissionXHSSpider(
        storage_type=args.storage, 
        output_dir=args.output,
        takeover=not args.new_browser,
        headless=args.headless
    )
    keywords = args.keywords if args.keywords else ["悉尼咖啡"]
    
    logger.info(f"📦 存储格式: {args.storage.upper()}")
    logger.info(f"📂 输出目录: {args.output}")
        
    spider.crawl(
        keywords, limit=args.limit,
        daily_limit=args.daily_limit,
        min_likes=args.min_likes,
        warmup=not args.no_warmup,
        shuffle=not args.no_shuffle
    )

if __name__ == "__main__":
    main()

