"""论文服务 - Supabase 版本

处理论文的增删改查、搜索、收藏、标记已读等业务逻辑。
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional


class PaperService:
    """论文服务"""

    def __init__(self, db):
        self.db = db

    def get_paper_by_id(self, paper_id) -> Optional[dict]:
        """获取论文详情"""
        papers = self.db.client.select('papers', id=str(paper_id))
        return papers[0] if papers else None

    def get_papers_by_user(self, user_id, limit: int = 100) -> list[dict]:
        """获取用户推送的论文"""
        # Get user_papers associations
        user_papers = self.db.client.select('user_papers', user_id=str(user_id), order='pushed_at.desc', limit=limit)
        
        # Get paper details
        result = []
        for up in user_papers:
            papers = self.db.client.select('papers', id=up['paper_id'])
            if papers:
                paper = papers[0]
                paper['is_bookmarked'] = up.get('is_bookmarked', False)
                paper['is_read'] = up.get('is_read', False)
                paper['pushed_at'] = up.get('pushed_at')
                result.append(paper)
        
        return result

    def search_papers(self, keywords: list[str], limit: int = 50) -> list[dict]:
        """搜索论文（根据关键词）"""
        if not keywords:
            return []
        
        # Build OR query for all keywords
        keyword_conditions = []
        for kw in keywords:
            keyword_conditions.append(f'title.ilike.%{kw}%')
            keyword_conditions.append(f'abstract.ilike.%{kw}%')
        
        or_filter = ','.join(keyword_conditions)
        papers = self.db.client.select_or('papers', or_filters=or_filter, order='published_at.desc', limit=limit)
        return papers

    def get_bookmarked_papers(self, user_id, limit: int = 100) -> list[dict]:
        """获取用户收藏的论文"""
        user_papers = self.db.client.select('user_papers', user_id=str(user_id), is_bookmarked='true', order='updated_at.desc', limit=limit)
        
        result = []
        for up in user_papers:
            papers = self.db.client.select('papers', id=up['paper_id'])
            if papers:
                paper = papers[0]
                paper['is_bookmarked'] = True
                paper['is_read'] = up.get('is_read', False)
                paper['bookmarked_at'] = up.get('updated_at')
                result.append(paper)
        
        return result

    def bookmark_paper(self, user_id, paper_id) -> dict:
        """收藏论文"""
        # Check if exists
        existing = self.db.client.select('user_papers', user_id=str(user_id), paper_id=str(paper_id))
        
        if existing:
            # Update
            self.db.client.update('user_papers', {'is_bookmarked': True}, id=existing[0]['id'])
            return existing[0]
        else:
            # Create
            data = {
                'id': str(uuid.uuid4()),
                'user_id': str(user_id),
                'paper_id': str(paper_id),
                'is_bookmarked': True,
                'is_read': False,
            }
            result = self.db.client.insert('user_papers', data)
            return result[0]

    def unbookmark_paper(self, user_id, paper_id) -> bool:
        """取消收藏"""
        existing = self.db.client.select('user_papers', user_id=str(user_id), paper_id=str(paper_id))
        if not existing:
            return False
        
        self.db.client.update('user_papers', {'is_bookmarked': False}, id=existing[0]['id'])
        return True

    def mark_as_read(self, user_id, paper_id) -> bool:
        """标记论文为已读"""
        existing = self.db.client.select('user_papers', user_id=str(user_id), paper_id=str(paper_id))
        if not existing:
            return False
        
        self.db.client.update('user_papers', {'is_read': True}, id=existing[0]['id'])
        return True

    def get_statistics(self, user_id) -> dict:
        """获取用户统计信息"""
        total = self.db.client.count('user_papers', user_id=str(user_id))
        bookmarked = self.db.client.count('user_papers', user_id=str(user_id), is_bookmarked='true')
        read = self.db.client.count('user_papers', user_id=str(user_id), is_read='true')
        
        return {
            'total_papers': total,
            'bookmarked_papers': bookmarked,
            'read_papers': read,
        }
