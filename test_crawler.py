#!/usr/bin/env python3
"""快速测试爬虫的存储功能"""

from datetime import datetime
from xhs_utils.storage_manager import StorageManager
import json

print("=" * 60)
print("🧪 开始测试多格式存储功能")
print("=" * 60)

# 测试数据
test_note = {
    'note_id': 'test_12345',
    'title': '测试标题',
    'content': '这是一条测试笔记内容',
    'author': '测试作者',
    'author_id': 'author_001',
    'likes': 100,
    'collects': 50,
    'comments_count': 20,
    'share_count': 10,
    'publish_time': '2026-02-10 23:00:00',
    'note_url': 'https://www.xiaohongshu.com/test',
    'tags': 'tag1,tag2',
    'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
}

test_comment = {
    'comment_id': 'comment_001',
    'note_id': 'test_12345',
    'content': '测试评论内容',
    'author': '评论作者',
    'author_id': 'commenter_001',
    'likes': 5,
    'sub_comment_count': 2,
    'create_time': '2026-02-10 23:05:00',
    'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
}

# 测试所有存储格式
formats = ['sqlite', 'csv', 'json', 'excel']
results = {}

for fmt in formats:
    try:
        print(f"\n{'='*60}")
        print(f"📝 测试 {fmt.upper()} 格式...")
        print(f"{'='*60}")
        
        # 初始化存储管理器
        manager = StorageManager(storage_type=fmt, output_dir='datas')
        print(f"✅ 存储管理器初始化成功")
        
        # 保存笔记
        manager.add_note(test_note)
        print(f"✅ 笔记保存成功")
        
        # 保存评论
        manager.add_comments(test_note['note_id'], [test_comment])
        print(f"✅ 评论保存成功")
        
        # 关闭管理器
        manager.finalize()
        print(f"✅ 存储管理器关闭成功")
        
        results[fmt] = '✅ 成功'
        
    except Exception as e:
        print(f"❌ 错误: {str(e)}")
        results[fmt] = f'❌ 失败: {str(e)}'

# 输出测试报告
print(f"\n{'='*60}")
print("📊 测试报告")
print(f"{'='*60}")
for fmt, result in results.items():
    print(f"  {fmt.upper():10s} : {result}")

print(f"\n{'='*60}")
print("📁 检查生成的文件...")
print(f"{'='*60}")

import os
from pathlib import Path

# 检查文件夹
for fmt in formats:
    folder = Path('datas') / f'{fmt}_datas'
    if folder.exists():
        files = list(folder.glob('*'))
        print(f"\n  {fmt}_datas/:")
        if files:
            for f in files[:5]:  # 只显示前5个文件
                size = f.stat().st_size
                print(f"    ✅ {f.name} ({size} bytes)")
        else:
            print(f"    ⚠️  文件夹为空")
    else:
        print(f"\n  {fmt}_datas/: ❌ 不存在")

print(f"\n{'='*60}")
print("🎉 测试完成！")
print(f"{'='*60}")
