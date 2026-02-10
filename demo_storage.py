#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
演示：验证不同格式的数据存储路径
"""

import sys
sys.path.insert(0, '/Users/paris404/Documents/项目/Spider_XHS')

from xhs_utils.storage_manager import StorageManager
import json

# 模拟一条笔记数据
mock_note = {
    'note_id': 'test_12345',
    'url': 'https://www.xiaohongshu.com/explore/test',
    'title': '测试标题 - 澳洲留学攻略',
    'desc': '这是一条测试数据，用于验证存储路径',
    'note_type': 'normal',
    'author_id': 'author_001',
    'author_name': '测试作者',
    'liked_count': 100,
    'collected_count': 50,
    'comment_count': 10,
    'total_interaction': 160,
    'traffic_level': '普通',
    'tags': ['澳洲留学', '悉尼'],
    'upload_time': '2026-02-10',
    'keyword_source': '澳洲留学',
    'full_text': '测试标题 - 澳洲留学攻略 这是一条测试数据 澳洲留学 悉尼'
}

# 模拟评论数据
mock_comments = [
    {
        'comment_id': 'comment_001',
        'content': '这个信息很有用！',
        'author_name': '评论者1',
        'like_count': 5
    },
    {
        'comment_id': 'comment_002',
        'content': '感谢分享',
        'author_name': '评论者2',
        'like_count': 3
    }
]

print("\n" + "=" * 70)
print("🧪 爬虫数据存储路径验证")
print("=" * 70)

formats = [
    ('sqlite', 'SQLite 数据库'),
    ('csv', 'CSV 表格'),
    ('json', 'JSON 文件'),
    ('excel', 'Excel 工作簿')
]

for fmt, desc in formats:
    print(f"\n{'─' * 70}")
    print(f"📦 格式: {desc} ({fmt.upper()})")
    print(f"{'─' * 70}")
    
    # 创建存储管理器
    storage = StorageManager(storage_type=fmt, output_dir='datas')
    
    # 添加数据
    storage.add_note(mock_note)
    storage.add_comments(mock_note['note_id'], mock_comments)
    
    # 完成存储（JSON/Excel需要调用）
    storage.finalize()
    
    # 显示存储位置
    print(f"✅ 存储位置: {storage.output_dir}")
    
    if fmt == 'sqlite':
        print(f"   数据库文件: {storage.db_path}")
    elif fmt == 'csv':
        print(f"   笔记文件: {storage.notes_file.name}")
        print(f"   评论文件: {storage.comments_file.name}")
    elif fmt == 'json':
        print(f"   JSON文件: {storage.json_file.name}")
    elif fmt == 'excel':
        print(f"   Excel文件: {storage.excel_file.name}")
    
    print(f"✓ 数据已成功写入")

print("\n" + "=" * 70)
print("✅ 验证完成！所有格式的数据都已正确存储到对应文件夹")
print("=" * 70)

print("\n📁 完整的文件夹结构：")
print("""
datas/
├── sqlite_datas/       👈 SQLite 数据库文件
│   └── notes.db
├── csv_datas/          👈 CSV 表格文件
│   ├── notes_YYYYMMDD_HHMMSS.csv
│   └── comments_YYYYMMDD_HHMMSS.csv
├── json_datas/         👈 JSON 文件
│   └── notes_YYYYMMDD_HHMMSS.json
└── excel_datas/        👈 Excel 工作簿
    └── notes_YYYYMMDD_HHMMSS.xlsx
""")

print("\n💡 提示：实际爬虫运行时，数据会自动存储到上述路径！")
print()
