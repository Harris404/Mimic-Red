#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
关键词数据库管理系统
提供完整的关键词生命周期管理功能
"""

import sqlite3
import json
import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from loguru import logger
from contextlib import contextmanager


class KeywordManager:
    """关键词数据库管理器"""
    
    def __init__(self, db_path: str = "datas/keywords.db"):
        self.db_path = db_path
        self._init_database()
        logger.info(f"✅ 关键词数据库已连接: {db_path}")
    
    @staticmethod
    def normalize_keyword(keyword: str) -> str:
        """
        规范化关键词
        - 去除首尾空格
        - 将连续空格替换为单个空格
        
        Args:
            keyword: 原始关键词
            
        Returns:
            规范化后的关键词
        """
        if not keyword:
            return ""
        
        # 去除首尾空格
        keyword = keyword.strip()
        
        # 将连续空格替换为单个空格
        keyword = re.sub(r'\s+', ' ', keyword)
        
        return keyword
    
    @contextmanager
    def _get_connection(self):
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
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS keywords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword TEXT UNIQUE NOT NULL,
                    source TEXT,
                    category TEXT,
                    city TEXT,
                    domain TEXT,
                    
                    relevance_score REAL DEFAULT 0.0,
                    quality_score REAL DEFAULT 0.0,
                    
                    status TEXT DEFAULT 'pending',
                    crawl_count INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    total_notes_found INTEGER DEFAULT 0,
                    avg_notes_per_crawl REAL DEFAULT 0.0,
                    
                    first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_crawl_time DATETIME,
                    last_success_time DATETIME,
                    last_update_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    
                    trending_score REAL DEFAULT 0.0,
                    is_trending BOOLEAN DEFAULT 0,
                    
                    lifecycle_stage TEXT DEFAULT 'new',
                    auto_discovered BOOLEAN DEFAULT 0,
                    parent_keyword TEXT,
                    
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS keyword_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword_id INTEGER,
                    crawl_date DATE,
                    notes_found INTEGER,
                    avg_interaction INTEGER,
                    high_quality_ratio REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (keyword_id) REFERENCES keywords(id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS discovered_tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tag TEXT UNIQUE NOT NULL,
                    discovery_count INTEGER DEFAULT 1,
                    first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                    promoted_to_keyword BOOLEAN DEFAULT 0,
                    notes_count INTEGER DEFAULT 0,
                    source_keyword TEXT
                )
            """)
            
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_keywords_status ON keywords(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_keywords_quality ON keywords(quality_score DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_keywords_trending ON keywords(trending_score DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_keywords_lifecycle ON keywords(lifecycle_stage)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags_count ON discovered_tags(discovery_count DESC)")
    
    def add_keyword(
        self,
        keyword: str,
        source: str = 'manual',
        category: Optional[str] = None,
        city: Optional[str] = None,
        domain: Optional[str] = None,
        relevance_score: float = 0.0,
        status: str = 'pending',
        auto_discovered: bool = False,
        parent_keyword: Optional[str] = None
    ) -> bool:
        keyword = self.normalize_keyword(keyword)
        
        if not keyword:
            logger.warning("⚠️ 关键词为空,跳过添加")
            return False
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO keywords (
                        keyword, source, category, city, domain,
                        relevance_score, status, auto_discovered, parent_keyword
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (keyword, source, category, city, domain, relevance_score, 
                      status, auto_discovered, parent_keyword))
                
                logger.debug(f"✅ 添加关键词: {keyword} (来源: {source})")
                return True
        except sqlite3.IntegrityError:
            logger.debug(f"⚠️ 关键词已存在: {keyword}")
            return False
        except Exception as e:
            logger.error(f"❌ 添加关键词失败: {keyword}, {e}")
            return False
    
    def get_keywords(
        self,
        status: Optional[str] = None,
        lifecycle_stage: Optional[str] = None,
        min_quality: Optional[float] = None,
        limit: Optional[int] = None,
        order_by: str = 'created_at DESC'
    ) -> List[Dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM keywords WHERE 1=1"
            params = []
            
            if status:
                query += " AND status = ?"
                params.append(status)
            
            if lifecycle_stage:
                query += " AND lifecycle_stage = ?"
                params.append(lifecycle_stage)
            
            if min_quality is not None:
                query += " AND quality_score >= ?"
                params.append(min_quality)
            
            query += f" ORDER BY {order_by}"
            
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_keyword_by_name(self, keyword: str) -> Optional[Dict]:
        keyword = self.normalize_keyword(keyword)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM keywords WHERE keyword = ?", (keyword,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def update_after_crawl(
        self,
        keyword: str,
        success: bool,
        notes_found: int = 0,
        avg_interaction: int = 0
    ):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            kw = self.get_keyword_by_name(keyword)
            if not kw:
                logger.warning(f"关键词不存在: {keyword}")
                return
            
            new_crawl_count = kw['crawl_count'] + 1
            new_success_count = kw['success_count'] + (1 if success else 0)
            new_total_notes = kw['total_notes_found'] + notes_found
            new_avg_notes = new_total_notes / new_crawl_count
            
            update_fields = {
                'crawl_count': new_crawl_count,
                'success_count': new_success_count,
                'total_notes_found': new_total_notes,
                'avg_notes_per_crawl': new_avg_notes,
                'last_crawl_time': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            if success:
                update_fields['last_success_time'] = datetime.now().isoformat()
                update_fields['status'] = 'active'
            
            set_clause = ', '.join([f"{k} = ?" for k in update_fields.keys()])
            values = list(update_fields.values()) + [keyword]
            
            cursor.execute(f"""
                UPDATE keywords SET {set_clause}
                WHERE keyword = ?
            """, values)
            
            if success and notes_found > 0:
                cursor.execute("""
                    INSERT INTO keyword_history (
                        keyword_id, crawl_date, notes_found, avg_interaction
                    ) VALUES (?, ?, ?, ?)
                """, (kw['id'], datetime.now().date().isoformat(), 
                      notes_found, avg_interaction))
            
            logger.info(f"{'✅' if success else '❌'} 更新关键词: {keyword} (笔记数: {notes_found})")
    
    def add_discovered_tag(
        self,
        tag: str,
        notes_count: int = 0,
        source_keyword: Optional[str] = None
    ):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO discovered_tags (tag, notes_count, source_keyword)
                    VALUES (?, ?, ?)
                """, (tag, notes_count, source_keyword))
                logger.debug(f"🔍 发现新标签: {tag}")
        except sqlite3.IntegrityError:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE discovered_tags 
                    SET discovery_count = discovery_count + 1,
                        last_seen = CURRENT_TIMESTAMP,
                        notes_count = notes_count + ?
                    WHERE tag = ?
                """, (notes_count, tag))
                logger.debug(f"🔄 更新标签计数: {tag}")
    
    def get_discovered_tags(
        self,
        min_count: int = 1,
        promoted: bool = False,
        order_by: str = 'discovery_count DESC',
        limit: Optional[int] = None
    ) -> List[Dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT * FROM discovered_tags 
                WHERE discovery_count >= ? AND promoted_to_keyword = ?
                ORDER BY {}
            """.format(order_by)
            
            params = [min_count, 1 if promoted else 0]
            
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def promote_tag_to_keyword(self, tag_id: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM discovered_tags WHERE id = ?", (tag_id,))
            tag = cursor.fetchone()
            
            if not tag:
                return False
            
            success = self.add_keyword(
                tag['tag'],
                source='auto_discovered',
                status='pending',
                auto_discovered=True
            )
            
            if success:
                cursor.execute("""
                    UPDATE discovered_tags 
                    SET promoted_to_keyword = 1
                    WHERE id = ?
                """, (tag_id,))
                logger.info(f"🌟 标签晋升为关键词: {tag['tag']}")
            
            return success
    
    def get_statistics(self) -> Dict:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) as total FROM keywords")
            total = cursor.fetchone()['total']
            
            cursor.execute("SELECT COUNT(*) as count FROM keywords WHERE status = 'active'")
            active = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM keywords WHERE status = 'pending'")
            pending = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM keywords WHERE lifecycle_stage = 'dead'")
            archived = cursor.fetchone()['count']
            
            cursor.execute("SELECT AVG(quality_score) as avg FROM keywords WHERE quality_score > 0")
            avg_quality = cursor.fetchone()['avg'] or 0.0
            
            cursor.execute("""
                SELECT lifecycle_stage, COUNT(*) as count 
                FROM keywords 
                GROUP BY lifecycle_stage
            """)
            lifecycle_dist = {row['lifecycle_stage']: row['count'] for row in cursor.fetchall()}
            
            return {
                'total': total,
                'active': active,
                'pending': pending,
                'archived': archived,
                'avg_quality': round(avg_quality, 2),
                'lifecycle_distribution': lifecycle_dist
            }
    
    def keyword_exists(self, keyword: str) -> bool:
        return self.get_keyword_by_name(keyword) is not None
    
    def update_keyword(self, keyword_id: int, updates: Dict):
        updates['updated_at'] = datetime.now().isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
            values = list(updates.values()) + [keyword_id]
            
            cursor.execute(f"""
                UPDATE keywords SET {set_clause}
                WHERE id = ?
            """, values)
    
    def archive_keyword(self, keyword_id: int):
        self.update_keyword(keyword_id, {
            'status': 'archived',
            'lifecycle_stage': 'dead'
        })
    
    def get_all_keywords(self) -> List[Dict]:
        return self.get_keywords(limit=None)
