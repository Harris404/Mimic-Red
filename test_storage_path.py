#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试存储管理器路径生成
"""

import sys
sys.path.insert(0, '/Users/paris404/Documents/项目/Spider_XHS')

from xhs_utils.storage_manager import StorageManager

print("=" * 60)
print("测试存储路径生成")
print("=" * 60)

formats = ['sqlite', 'csv', 'json', 'excel']

for fmt in formats:
    manager = StorageManager(storage_type=fmt, output_dir='datas')
    print(f"\n格式: {fmt.upper()}")
    print(f"输出目录: {manager.output_dir}")
    print(f"目录是否存在: {manager.output_dir.exists()}")
    
    if fmt == 'sqlite':
        print(f"数据库路径: {manager.db_path}")
    elif fmt == 'csv':
        print(f"笔记文件: {manager.notes_file}")
        print(f"评论文件: {manager.comments_file}")
    elif fmt == 'json':
        print(f"JSON文件: {manager.json_file}")
    elif fmt == 'excel':
        print(f"Excel文件: {manager.excel_file}")

print("\n" + "=" * 60)
print("测试完成！")
print("=" * 60)
