# -*- coding: utf-8 -*-
"""查询管理模型定义"""

from datetime import datetime


def build_query_management_model(db):
    class QueryManagement(db.Model):
        __tablename__ = 'query_managements'

        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(120), nullable=False)
        query_code = db.Column(db.String(120), nullable=False, unique=True)
        category = db.Column(db.String(50), default='general')
        keyword = db.Column(db.String(200))
        data_source = db.Column(db.String(100))
        owner = db.Column(db.String(100))
        priority = db.Column(db.Integer, default=0)
        is_active = db.Column(db.Boolean, default=True)
        description = db.Column(db.Text)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

        def to_dict(self):
            return {
                'id': self.id,
                'name': self.name,
                'query_code': self.query_code,
                'category': self.category,
                'keyword': self.keyword,
                'data_source': self.data_source,
                'owner': self.owner,
                'priority': self.priority,
                'is_active': self.is_active,
                'description': self.description,
                'created_at': self.created_at.isoformat() if self.created_at else None,
                'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            }

    return {'QueryManagement': QueryManagement}
