# -*- coding: utf-8 -*-
"""查询管理模型定义"""

from datetime import datetime
import json


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
        image_url = db.Column(db.String(500))
        image_urls = db.Column(db.Text)
        file_url = db.Column(db.String(500))
        file_urls = db.Column(db.Text)
        priority = db.Column(db.Integer, default=0)
        is_active = db.Column(db.Boolean, default=True)
        description = db.Column(db.Text)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

        def to_dict(self):
            def parse_json_url_list(raw):
                if not raw:
                    return []
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if str(item).strip()]
                except Exception:
                    return []
                return []

            parsed_image_urls = []
            parsed_file_urls = []
            raw_image_urls = self.image_urls
            raw_file_urls = self.file_urls
            parsed_image_urls = parse_json_url_list(raw_image_urls)
            parsed_file_urls = parse_json_url_list(raw_file_urls)
            if not parsed_image_urls and self.image_url:
                parsed_image_urls = [self.image_url]
            if not parsed_file_urls and self.file_url:
                parsed_file_urls = [self.file_url]

            return {
                'id': self.id,
                'name': self.name,
                'query_code': self.query_code,
                'category': self.category,
                'keyword': self.keyword,
                'data_source': self.data_source,
                'owner': self.owner,
                'image_url': self.image_url or (parsed_image_urls[0] if parsed_image_urls else None),
                'image_urls': parsed_image_urls,
                'file_url': self.file_url or (parsed_file_urls[0] if parsed_file_urls else None),
                'file_urls': parsed_file_urls,
                'priority': self.priority,
                'is_active': self.is_active,
                'description': self.description,
                'created_at': self.created_at.isoformat() if self.created_at else None,
                'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            }

    return {'QueryManagement': QueryManagement}
