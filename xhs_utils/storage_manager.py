#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多格式数据存储管理器
支持 CSV、JSON、Excel、SQLite 四种存储方式
"""

import csv
import json
import os
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
from loguru import logger


class StorageManager:
    """统一的数据存储管理器"""
    
    def __init__(self, storage_type: str = "sqlite", output_dir: str = "datas"):
        """
        初始化存储管理器
        
        Args:
            storage_type: 存储类型 ('csv', 'json', 'excel', 'sqlite')
            output_dir: 输出目录（将自动在其下创建格式专用子目录）
        """
        self.storage_type = storage_type.lower()
        
        # 根据存储格式创建专用子目录
        format_dirs = {
            'sqlite': 'sqlite_datas',
            'csv': 'csv_datas',
            'json': 'json_datas',
            'excel': 'excel_datas'
        }
        
        base_dir = Path(output_dir)
        self.output_dir = base_dir / format_dirs.get(self.storage_type, self.storage_type)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 存储文件/数据库路径
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.notes_data = []
        self.comments_data = []
        
        if self.storage_type == "sqlite":
            self.db_path = self.output_dir / "notes.db"
            self._init_sqlite()
        elif self.storage_type == "csv":
            self.notes_file = self.output_dir / f"notes_{timestamp}.csv"
            self.comments_file = self.output_dir / f"comments_{timestamp}.csv"
            self._init_csv()
        elif self.storage_type == "json":
            self.json_file = self.output_dir / f"notes_{timestamp}.json"
        elif self.storage_type == "excel":
            self.excel_file = self.output_dir / f"notes_{timestamp}.xlsx"
        else:
            raise ValueError(f"不支持的存储类型: {storage_type}")
        
        logger.info(f"✅ 存储管理器已初始化: {storage_type.upper()}")
    
    def _init_sqlite(self):
        """初始化 SQLite 数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建笔记表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note_id TEXT UNIQUE NOT NULL,
                url TEXT,
                title TEXT,
                desc TEXT,
                note_type TEXT,
                author_id TEXT,
                author_name TEXT,
                liked_count INTEGER DEFAULT 0,
                collected_count INTEGER DEFAULT 0,
                comment_count INTEGER DEFAULT 0,
                total_interaction INTEGER DEFAULT 0,
                traffic_level TEXT,
                tags TEXT,
                upload_time DATETIME,
                crawl_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                keyword_source TEXT,
                full_text TEXT
            )
        """)
        
        # 创建评论表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                comment_id TEXT UNIQUE,
                note_id TEXT NOT NULL,
                content TEXT NOT NULL,
                author_name TEXT,
                like_count INTEGER DEFAULT 0,
                crawl_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (note_id) REFERENCES notes(note_id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _init_csv(self):
        """初始化 CSV 文件（写入表头）"""
        # 笔记 CSV
        with open(self.notes_file, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'note_id', 'url', 'title', 'desc', 'note_type',
                'author_id', 'author_name', 'liked_count', 'collected_count',
                'comment_count', 'total_interaction', 'traffic_level',
                'tags', 'upload_time', 'crawl_time', 'keyword_source', 'full_text'
            ])
            writer.writeheader()
        
        # 评论 CSV
        with open(self.comments_file, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'comment_id', 'note_id', 'content', 'author_name', 'like_count', 'crawl_time'
            ])
            writer.writeheader()
    
    def add_note(self, note: Dict):
        """添加笔记数据"""
        if self.storage_type == "sqlite":
            self._add_note_sqlite(note)
        elif self.storage_type == "csv":
            self._add_note_csv(note)
        else:
            # JSON 和 Excel 先存到内存
            self.notes_data.append(note)
    
    def _add_note_sqlite(self, note: Dict):
        """添加笔记到 SQLite"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO notes (
                    note_id, url, title, desc, note_type,
                    author_id, author_name, liked_count, collected_count,
                    comment_count, total_interaction, traffic_level,
                    tags, upload_time, keyword_source, full_text
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                note.get('note_id'), note.get('url'), note.get('title'),
                note.get('desc'), note.get('note_type', 'normal'),
                note.get('author_id'), note.get('author_name'),
                note.get('liked_count', 0), note.get('collected_count', 0),
                note.get('comment_count', 0), note.get('total_interaction', 0),
                note.get('traffic_level', ''),
                json.dumps(note.get('tags', []), ensure_ascii=False),
                note.get('upload_time'), note.get('keyword_source', ''),
                note.get('full_text', '')
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"SQLite 写入失败: {e}")
    
    def _add_note_csv(self, note: Dict):
        """添加笔记到 CSV"""
        try:
            with open(self.notes_file, 'a', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'note_id', 'url', 'title', 'desc', 'note_type',
                    'author_id', 'author_name', 'liked_count', 'collected_count',
                    'comment_count', 'total_interaction', 'traffic_level',
                    'tags', 'upload_time', 'crawl_time', 'keyword_source', 'full_text'
                ])
                
                row = {
                    'note_id': note.get('note_id'),
                    'url': note.get('url'),
                    'title': note.get('title'),
                    'desc': note.get('desc'),
                    'note_type': note.get('note_type', 'normal'),
                    'author_id': note.get('author_id'),
                    'author_name': note.get('author_name'),
                    'liked_count': note.get('liked_count', 0),
                    'collected_count': note.get('collected_count', 0),
                    'comment_count': note.get('comment_count', 0),
                    'total_interaction': note.get('total_interaction', 0),
                    'traffic_level': note.get('traffic_level', ''),
                    'tags': '|'.join(note.get('tags', [])),
                    'upload_time': note.get('upload_time'),
                    'crawl_time': datetime.now().isoformat(),
                    'keyword_source': note.get('keyword_source', ''),
                    'full_text': note.get('full_text', '')
                }
                
                writer.writerow(row)
        except Exception as e:
            logger.error(f"CSV 写入失败: {e}")
    
    def add_comments(self, note_id: str, comments: List[Dict]):
        """添加评论数据"""
        if not comments:
            return
        
        if self.storage_type == "sqlite":
            self._add_comments_sqlite(note_id, comments)
        elif self.storage_type == "csv":
            self._add_comments_csv(note_id, comments)
        else:
            # JSON 和 Excel 存到内存
            for comment in comments:
                comment['note_id'] = note_id
                self.comments_data.append(comment)
    
    def _add_comments_sqlite(self, note_id: str, comments: List[Dict]):
        """添加评论到 SQLite"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for comment in comments:
                cursor.execute("""
                    INSERT OR REPLACE INTO comments (
                        comment_id, note_id, content, author_name, like_count
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    comment.get('comment_id'),
                    note_id,
                    comment.get('content', ''),
                    comment.get('author_name', ''),
                    comment.get('like_count', 0)
                ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"SQLite 评论写入失败: {e}")
    
    def _add_comments_csv(self, note_id: str, comments: List[Dict]):
        """添加评论到 CSV"""
        try:
            with open(self.comments_file, 'a', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'comment_id', 'note_id', 'content', 'author_name', 'like_count', 'crawl_time'
                ])
                
                for comment in comments:
                    row = {
                        'comment_id': comment.get('comment_id'),
                        'note_id': note_id,
                        'content': comment.get('content', ''),
                        'author_name': comment.get('author_name', ''),
                        'like_count': comment.get('like_count', 0),
                        'crawl_time': datetime.now().isoformat()
                    }
                    writer.writerow(row)
        except Exception as e:
            logger.error(f"CSV 评论写入失败: {e}")
    
    def finalize(self):
        """完成存储（用于 JSON 和 Excel 的最终写入）"""
        if self.storage_type == "json":
            self._save_json()
        elif self.storage_type == "excel":
            self._save_excel()
    
    def _save_json(self):
        """保存为 JSON 文件"""
        try:
            data = {
                'notes': self.notes_data,
                'comments': self.comments_data,
                'crawl_time': datetime.now().isoformat(),
                'total_notes': len(self.notes_data),
                'total_comments': len(self.comments_data)
            }
            
            with open(self.json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ JSON 文件已保存: {self.json_file}")
        except Exception as e:
            logger.error(f"JSON 保存失败: {e}")
    
    def _save_excel(self):
        """保存为 Excel 文件"""
        try:
            import pandas as pd
            
            # 处理笔记数据
            notes_df = pd.DataFrame(self.notes_data)
            if 'tags' in notes_df.columns:
                notes_df['tags'] = notes_df['tags'].apply(lambda x: '|'.join(x) if isinstance(x, list) else '')
            
            # 处理评论数据
            comments_df = pd.DataFrame(self.comments_data) if self.comments_data else pd.DataFrame()
            
            # 写入 Excel
            with pd.ExcelWriter(self.excel_file, engine='openpyxl') as writer:
                notes_df.to_excel(writer, sheet_name='Notes', index=False)
                if not comments_df.empty:
                    comments_df.to_excel(writer, sheet_name='Comments', index=False)
            
            logger.info(f"✅ Excel 文件已保存: {self.excel_file}")
        except ImportError:
            logger.error("❌ 请安装 pandas 和 openpyxl: pip install pandas openpyxl")
        except Exception as e:
            logger.error(f"Excel 保存失败: {e}")
    
    def get_seen_note_ids(self) -> set:
        """获取已爬取的笔记ID（用于去重）"""
        seen_ids = set()
        
        if self.storage_type == "sqlite":
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.execute("SELECT note_id FROM notes")
                seen_ids = {row[0] for row in cursor if row[0]}
                conn.close()
            except:
                pass
        elif self.storage_type == "csv":
            try:
                with open(self.notes_file, 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    seen_ids = {row['note_id'] for row in reader if row.get('note_id')}
            except:
                pass
        else:
            # JSON/Excel 从内存获取
            seen_ids = {note.get('note_id') for note in self.notes_data if note.get('note_id')}
        
        return seen_ids
