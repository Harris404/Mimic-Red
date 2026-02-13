# -*- coding: utf-8 -*-
"""
新模式功能测试脚本
测试目标：
1. 验证 --new-browser 模式能否正常启动浏览器
2. 验证数据能否正确写入独立的测试数据库 (test_datas/notes.db)
3. 验证基本的爬取流程（搜索、详情页提取）是否正常

使用方法：
python test_new_mode.py
"""
import os
import sys
import shutil
from loguru import logger
from xhs_utils.xhs_spider import DrissionXHSSpider

# 配置测试专用日志
logger.remove()
logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
logger.add("logs/test_mode.log", rotation="1 MB", encoding="utf-8")

def test_new_browser_mode():
    print("="*50)
    print("🚀 开始测试：独立浏览器启动模式 (New Browser Mode)")
    print("="*50)
    
    # 1. 准备测试环境
    test_output_dir = "test_datas"
    if os.path.exists(test_output_dir):
        logger.info(f"🧹 清理旧测试数据: {test_output_dir}")
        shutil.rmtree(test_output_dir)
    os.makedirs(test_output_dir, exist_ok=True)
    
    # 2. 初始化爬虫（使用测试配置）
    # 注意：这里 takeover=False 表示启动新浏览器
    # headless=False 方便您观察浏览器行为（首次运行需扫码）
    logger.info("🔧 初始化爬虫...")
    spider = DrissionXHSSpider(
        storage_type="sqlite",
        output_dir=test_output_dir,
        takeover=False,      # 关键：不接管，启动新浏览器
        headless=False       # 有头模式，方便扫码
    )
    
    # 3. 执行小规模爬取
    # 关键词选一个冷门的，避免干扰正常业务
    test_keyword = "测试笔记" 
    logger.info(f"🕷️ 开始爬取测试关键词: {test_keyword}")
    
    try:
        spider.crawl(
            keywords=[test_keyword],
            limit=2,             # 仅爬取 2 条，快速验证
            daily_limit=10,
            min_likes=0,
            warmup=True,        # 开启预热，测试预热逻辑
            shuffle=False
        )
        print("\n" + "="*50)
        print("✅ 爬取流程执行完毕")
    except Exception as e:
        logger.error(f"❌ 爬取过程中发生错误: {e}")
        return

    # 4. 验证数据存储
    db_path = os.path.join(test_output_dir, "sqlite_datas", "notes.db")
    if os.path.exists(db_path):
        import sqlite3
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 验证笔记表
            cursor.execute("SELECT count(*) FROM notes")
            note_count = cursor.fetchone()[0]
            
            # 验证评论表
            cursor.execute("SELECT count(*) FROM comments")
            comment_count = cursor.fetchone()[0]
            
            conn.close()
            
            print(f"📊 数据验证结果:")
            print(f"   - 数据库文件: {db_path}")
            print(f"   - 笔记数量: {note_count} (预期 >= 1)")
            print(f"   - 评论数量: {comment_count}")
            
            if note_count > 0:
                print("\n🎉 测试成功！新模式工作正常。")
                print("⚠️ 注意：登录状态已保存到 browser_data 目录，下次运行无需扫码。")
            else:
                print("\n⚠️ 测试警告：流程执行完成，但未存入数据（可能是搜索结果为空或反爬拦截）。")
                
        except Exception as e:
            logger.error(f"❌ 数据库验证失败: {e}")
    else:
        logger.error(f"❌ 测试失败：数据库文件未创建 {db_path}")

if __name__ == "__main__":
    # 检查是否已安装依赖
    try:
        import DrissionPage
    except ImportError:
        print("❌ 缺少依赖 DrissionPage，请先安装：pip install DrissionPage")
        sys.exit(1)
        
    test_new_browser_mode()
