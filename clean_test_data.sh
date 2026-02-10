#!/bin/bash
# 清理测试文件和旧数据（可选）

echo "🧹 数据文件清理脚本"
echo "=================="
echo

# 列出可以清理的文件
echo "可以清理的文件："
echo "1. datas/notes.db             (旧的根目录数据库)"
echo "2. 测试生成的数据文件         (demo_storage.py 生成的)"
echo

read -p "是否删除这些文件？[y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "正在清理..."
    
    # 删除旧文件
    [ -f datas/notes.db ] && rm datas/notes.db && echo "✓ 删除 datas/notes.db"
    
    # 删除测试文件（保留文件夹）
    rm -f datas/csv_datas/notes_20260210_*.csv
    rm -f datas/csv_datas/comments_20260210_*.csv
    rm -f datas/json_datas/notes_20260210_*.json
    rm -f datas/excel_datas/notes_20260210_*.xlsx
    rm -f datas/sqlite_datas/notes.db
    
    echo "✓ 删除测试生成的数据文件"
    echo
    echo "✅ 清理完成！"
    echo
    echo "当前保留："
    echo "- datas/crawl_progress.json  (断点续爬进度)"
    echo "- datas/reports/             (爬取报告)"
    echo "- 各个格式的空文件夹"
else
    echo "已取消清理"
fi
