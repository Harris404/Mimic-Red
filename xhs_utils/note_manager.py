#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
笔记数据库管理系统
管理爬取的笔记和评论数据，支持动态查询和管理
"""

import sqlite3
import json
import hashlib
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from loguru import logger
from contextlib import contextmanager


class NoteManager:
    """笔记数据库管理器"""
    
    def __init__(self, db_path: str = "datas/notes.db"):
        self.db_path = db_path
        self._init_database()
        logger.info(f"✅ 笔记数据库已连接: {db_path}")
    
    @contextmanager
    def _get_connection(self):
        """获取数据库连接（上下文管理器）"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def _init_database(self):
        """初始化数据库表结构"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 笔记主表（精简版 - 24个核心字段）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    note_id TEXT UNIQUE NOT NULL,
                    url TEXT,
                    
                    -- 基本信息
                    title TEXT,
                    desc TEXT,
                    note_type TEXT,
                    
                    -- 作者信息
                    author_id TEXT,
                    author_name TEXT,
                    author_ip_location TEXT,
                    
                    -- 互动数据
                    liked_count INTEGER DEFAULT 0,
                    collected_count INTEGER DEFAULT 0,
                    comment_count INTEGER DEFAULT 0,
                    total_interaction INTEGER DEFAULT 0,
                    traffic_level TEXT,
                    
                    -- 标签（JSON数组）
                    tags TEXT,
                    
                    -- 时间信息
                    upload_time DATETIME,
                    crawl_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    
                    -- 关键词来源与分类
                    keyword_source TEXT,
                    matrix_category TEXT,
                    city_category TEXT,
                    domain_category TEXT,
                    
                    -- RAG相关
                    full_text TEXT,  -- 用于RAG的完整文本（标题+内容+标签）
                    comments_text TEXT,  -- 聚合的评论文本（只保留内容）
                    vectorized_at DATETIME,  -- 向量化时间戳（用于增量更新）
                    
                    -- 爬取批次
                    crawl_batch TEXT
                )
            """)
            
            # 评论表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS comments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    comment_id TEXT UNIQUE,
                    note_id TEXT NOT NULL,
                    content TEXT NOT NULL,  -- 只保留评论内容
                    crawl_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (note_id) REFERENCES notes(note_id)
                )
            """)
            
            # 爬取批次记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS crawl_batches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_id TEXT UNIQUE NOT NULL,
                    keyword TEXT,
                    mode TEXT,
                    notes_count INTEGER DEFAULT 0,
                    comments_count INTEGER DEFAULT 0,
                    start_time DATETIME,
                    end_time DATETIME,
                    status TEXT DEFAULT 'running',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_note_id ON notes(note_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_keyword ON notes(keyword_source)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_traffic ON notes(traffic_level)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_city ON notes(city_category)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_domain ON notes(domain_category)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_crawl_time ON notes(crawl_time)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_comments_note_id ON comments(note_id)")
    
    def add_note(self, note_info: Dict, batch_id: str = None) -> bool:
        """
        添加笔记到数据库
        
        Args:
            note_info: 笔记信息字典
            batch_id: 爬取批次ID
        
        Returns:
            是否添加成功
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # 处理tags为JSON字符串
                tags = note_info.get('tags', [])
                if isinstance(tags, list):
                    tags_json = json.dumps(tags, ensure_ascii=False)
                else:
                    tags_json = str(tags)
                
                # 构建full_text用于RAG
                full_text = self._build_full_text(note_info)
                
                # 精简版INSERT（22个字段 - 移除 author_ip_location）
                cursor.execute("""
                    INSERT OR REPLACE INTO notes (
                        note_id, url,
                        title, desc, note_type,
                        author_id, author_name,
                        liked_count, collected_count, comment_count,
                        total_interaction, traffic_level,
                        tags,
                        upload_time, crawl_time,
                        keyword_source, matrix_category, city_category, domain_category,
                        full_text, comments_text,
                        crawl_batch
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    note_info.get('note_id', ''),
                    note_info.get('url', ''),
                    note_info.get('title', ''),
                    note_info.get('desc', ''),
                    note_info.get('note_type', ''),
                    note_info.get('author_id', ''),
                    note_info.get('author_name', ''),
                    self._safe_int(note_info.get('liked_count', 0)),
                    self._safe_int(note_info.get('collected_count', 0)),
                    self._safe_int(note_info.get('comment_count', 0)),
                    self._safe_int(note_info.get('total_interaction', 0)),
                    note_info.get('traffic_level', ''),
                    tags_json,
                    note_info.get('upload_time', ''),
                    datetime.now().isoformat(),
                    note_info.get('keyword_source', ''),
                    note_info.get('matrix_category', ''),
                    note_info.get('city_category', ''),
                    note_info.get('domain_category', ''),
                    full_text,
                    note_info.get('comments_text', ''),
                    batch_id
                ))
                
                logger.debug(f"✅ 添加笔记: {note_info.get('title', '')[:30]}...")
                return True
                
        except Exception as e:
            logger.error(f"❌ 添加笔记失败: {e}")
            return False
    
    def add_comments(self, note_id: str, comments: List[Dict]) -> int:
        """
        批量添加评论（只保留content）
        
        Args:
            note_id: 笔记ID
            comments: 评论列表
        
        Returns:
            添加成功的评论数量
        """
        added_count = 0
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            for idx, comment in enumerate(comments):
                try:
                    content = comment.get('content', '')
                    if not content:
                        continue
                    
                    comment_id = comment.get('comment_id', comment.get('id', ''))
                    # 安全防护：如果 comment_id 为空，自动生成唯一ID
                    if not comment_id:
                        content_hash = hashlib.md5(f"{note_id}_{content}_{idx}".encode()).hexdigest()[:12]
                        comment_id = f"{note_id}_{content_hash}"
                    
                    cursor.execute("""
                        INSERT OR IGNORE INTO comments (comment_id, note_id, content)
                        VALUES (?, ?, ?)
                    """, (comment_id, note_id, content))
                    
                    if cursor.rowcount > 0:
                        added_count += 1
                        
                except Exception as e:
                    logger.debug(f"添加评论失败: {e}")
                    continue
        
        return added_count
    
    def get_comments_text_by_note(self, note_id: str) -> str:
        """获取笔记的所有评论内容（聚合为文本）"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT content FROM comments WHERE note_id = ?
            """, (note_id,))
            
            contents = [row['content'] for row in cursor.fetchall()]
            return '\n'.join(contents)
    
    def update_comments_text(self, note_id: str):
        """将评论内容聚合后回写到notes表的comments_text字段"""
        try:
            comments_text = self.get_comments_text_by_note(note_id)
            if comments_text:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE notes SET comments_text = ? WHERE note_id = ?
                    """, (comments_text, note_id))
                    logger.debug(f"✅ 回写评论文本: {note_id} ({len(comments_text)}字)")
        except Exception as e:
            logger.error(f"❌ 回写评论文本失败: {note_id}, {e}")
    
    def _build_full_text(self, note_info: Dict) -> str:
        """构建用于RAG的完整文本"""
        parts = []
        
        title = note_info.get('title', '')
        if title:
            parts.append(f"标题: {title}")
        
        desc = note_info.get('desc', '')
        if desc:
            parts.append(f"内容: {desc}")
        
        tags = note_info.get('tags', [])
        if tags:
            if isinstance(tags, list):
                parts.append(f"标签: {', '.join(str(t) for t in tags)}")
            else:
                parts.append(f"标签: {tags}")
        
        return '\n\n'.join(parts)
    
    def _safe_int(self, value, default=0) -> int:
        """安全转换为整数"""
        try:
            if isinstance(value, int):
                return value
            if isinstance(value, str):
                value = value.strip()
                if '万' in value:
                    return int(float(value.replace('万', '')) * 10000)
                elif 'w' in value.lower():
                    return int(float(value.replace('w', '').replace('W', '')) * 10000)
                else:
                    return int(value)
            return int(value)
        except:
            return default
    
    # ==================== 查询方法 ====================
    
    def get_note_by_id(self, note_id: str) -> Optional[Dict]:
        """根据ID获取笔记"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM notes WHERE note_id = ?", (note_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def note_exists(self, note_id: str) -> bool:
        """检查笔记是否存在"""
        return self.get_note_by_id(note_id) is not None
    
    def get_notes(
        self,
        keyword: Optional[str] = None,
        city: Optional[str] = None,
        domain: Optional[str] = None,
        traffic_level: Optional[str] = None,
        min_interaction: Optional[int] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        order_by: str = 'crawl_time DESC'
    ) -> List[Dict]:
        """
        查询笔记
        
        Args:
            keyword: 关键词来源筛选
            city: 城市分类筛选
            domain: 领域分类筛选
            traffic_level: 流量层级筛选
            min_interaction: 最小互动量
            limit: 返回数量限制
            offset: 偏移量
            order_by: 排序方式
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM notes WHERE 1=1"
            params = []
            
            if keyword:
                query += " AND keyword_source = ?"
                params.append(keyword)
            
            if city:
                query += " AND city_category = ?"
                params.append(city)
            
            if domain:
                query += " AND domain_category = ?"
                params.append(domain)
            
            if traffic_level:
                query += " AND traffic_level = ?"
                params.append(traffic_level)
            
            if min_interaction is not None:
                query += " AND total_interaction >= ?"
                params.append(min_interaction)
            
            query += f" ORDER BY {order_by}"
            
            if limit:
                query += " LIMIT ? OFFSET ?"
                params.extend([limit, offset])
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_notes_for_rag(self, limit: Optional[int] = None) -> List[Dict]:
        """获取用于RAG的笔记数据（full_text + comments_text 合并为完整文本）"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT 
                    note_id, title, desc, full_text, comments_text,
                    tags, keyword_source, city_category, domain_category,
                    traffic_level, total_interaction, author_name, upload_time
                FROM notes
                WHERE full_text IS NOT NULL AND full_text != ''
                ORDER BY total_interaction DESC
            """
            
            if limit:
                query += f" LIMIT {limit}"
            
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_unvectorized_notes(self, limit: Optional[int] = None) -> List[Dict]:
        """获取未向量化的笔记（用于增量更新）"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT 
                    note_id, title, desc, full_text, comments_text,
                    tags, keyword_source, city_category, domain_category,
                    traffic_level, total_interaction, author_name, upload_time
                FROM notes
                WHERE full_text IS NOT NULL AND full_text != ''
                  AND (vectorized_at IS NULL OR vectorized_at = '')
                ORDER BY total_interaction DESC
            """
            
            if limit:
                query += f" LIMIT {limit}"
            
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]
    
    def mark_as_vectorized(self, note_ids: List[str]):
        """标记笔记为已向量化"""
        if not note_ids:
            return
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            timestamp = datetime.now().isoformat()
            
            placeholders = ','.join('?' * len(note_ids))
            cursor.execute(f"""
                UPDATE notes 
                SET vectorized_at = ?
                WHERE note_id IN ({placeholders})
            """, [timestamp] + note_ids)
            
            logger.info(f"✅ 标记 {len(note_ids)} 条笔记为已向量化")
    
    def search_notes(self, query: str, limit: int = 50) -> List[Dict]:
        """全文搜索笔记"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # SQLite LIKE搜索
            search_pattern = f"%{query}%"
            cursor.execute("""
                SELECT * FROM notes
                WHERE title LIKE ? OR desc LIKE ? OR full_text LIKE ?
                ORDER BY total_interaction DESC
                LIMIT ?
            """, (search_pattern, search_pattern, search_pattern, limit))
            
            return [dict(row) for row in cursor.fetchall()]
    
    # ==================== 批次管理 ====================
    
    def start_batch(self, keyword: str = None, mode: str = None) -> str:
        """开始新的爬取批次"""
        batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO crawl_batches (batch_id, keyword, mode, start_time, status)
                VALUES (?, ?, ?, ?, 'running')
            """, (batch_id, keyword, mode, datetime.now().isoformat()))
        
        logger.info(f"📦 开始批次: {batch_id}")
        return batch_id
    
    def finish_batch(self, batch_id: str, notes_count: int, comments_count: int):
        """完成爬取批次"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE crawl_batches 
                SET end_time = ?, notes_count = ?, comments_count = ?, status = 'completed'
                WHERE batch_id = ?
            """, (datetime.now().isoformat(), notes_count, comments_count, batch_id))
        
        logger.info(f"✅ 完成批次: {batch_id} (笔记:{notes_count}, 评论:{comments_count})")
    
    # ==================== 统计方法 ====================
    
    def get_statistics(self) -> Dict:
        """获取数据库统计信息"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 笔记总数
            cursor.execute("SELECT COUNT(*) as total FROM notes")
            total_notes = cursor.fetchone()['total']
            
            # 评论总数
            cursor.execute("SELECT COUNT(*) as total FROM comments")
            total_comments = cursor.fetchone()['total']
            
            # 按城市统计
            cursor.execute("""
                SELECT city_category, COUNT(*) as count 
                FROM notes 
                WHERE city_category IS NOT NULL AND city_category != ''
                GROUP BY city_category
            """)
            by_city = {row['city_category']: row['count'] for row in cursor.fetchall()}
            
            # 按领域统计
            cursor.execute("""
                SELECT domain_category, COUNT(*) as count 
                FROM notes 
                WHERE domain_category IS NOT NULL AND domain_category != ''
                GROUP BY domain_category
            """)
            by_domain = {row['domain_category']: row['count'] for row in cursor.fetchall()}
            
            # 按流量层级统计
            cursor.execute("""
                SELECT traffic_level, COUNT(*) as count 
                FROM notes 
                WHERE traffic_level IS NOT NULL AND traffic_level != ''
                GROUP BY traffic_level
            """)
            by_traffic = {row['traffic_level']: row['count'] for row in cursor.fetchall()}
            
            # 按关键词统计（前20）
            cursor.execute("""
                SELECT keyword_source, COUNT(*) as count 
                FROM notes 
                WHERE keyword_source IS NOT NULL AND keyword_source != ''
                GROUP BY keyword_source
                ORDER BY count DESC
                LIMIT 20
            """)
            top_keywords = {row['keyword_source']: row['count'] for row in cursor.fetchall()}
            
            # 批次统计
            cursor.execute("SELECT COUNT(*) as total FROM crawl_batches WHERE status = 'completed'")
            completed_batches = cursor.fetchone()['total']
            
            return {
                'total_notes': total_notes,
                'total_comments': total_comments,
                'completed_batches': completed_batches,
                'by_city': by_city,
                'by_domain': by_domain,
                'by_traffic_level': by_traffic,
                'top_keywords': top_keywords
            }
    
    # ==================== 导出方法 ====================
    
    def export_to_jsonl(self, output_path: str, limit: Optional[int] = None, incremental: bool = False) -> int:
        """导出为JSONL格式（适合RAG）"""
        import os
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 增量模式只导出未向量化的笔记
        if incremental:
            notes = self.get_unvectorized_notes(limit=limit)
            logger.info(f"📝 增量模式：导出 {len(notes)} 条未向量化笔记")
        else:
            notes = self.get_notes_for_rag(limit=limit)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for note in notes:
                # 构建RAG文档 - 将评论合并到主文本中，提升检索命中率
                rag_text = note['full_text'] or ''
                comments_text = note.get('comments_text', '') or ''
                if comments_text:
                    rag_text += f'\n\n用户评论: {comments_text}'
                
                doc = {
                    'id': note['note_id'],
                    'text': rag_text,
                    'metadata': {
                        'title': note['title'],
                        'author': note['author_name'],
                        'keyword': note['keyword_source'],
                        'city': note['city_category'],
                        'domain': note['domain_category'],
                        'traffic_level': note['traffic_level'],
                        'interaction': note['total_interaction'],
                        'upload_time': note['upload_time']
                    }
                }
                
                f.write(json.dumps(doc, ensure_ascii=False) + '\n')
        
        # 如果是增量模式，标记为已向量化
        if incremental and notes:
            note_ids = [note['note_id'] for note in notes]
            self.mark_as_vectorized(note_ids)
        
        logger.info(f"✅ 导出 {len(notes)} 条笔记到 {output_path}")
        return len(notes)
    
    def export_comments_only(self, output_path: str) -> int:
        """只导出评论内容"""
        import os
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT note_id, content FROM comments")
            comments = cursor.fetchall()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for comment in comments:
                f.write(json.dumps({
                    'note_id': comment['note_id'],
                    'content': comment['content']
                }, ensure_ascii=False) + '\n')
        
        logger.info(f"✅ 导出 {len(comments)} 条评论到 {output_path}")
        return len(comments)


# 便捷函数
def get_note_manager(db_path: str = "datas/notes.db") -> NoteManager:
    """获取NoteManager实例"""
    return NoteManager(db_path)
