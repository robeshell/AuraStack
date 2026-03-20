# -*- coding: utf-8 -*-
"""查询管理 schema 层"""

import json


def export_image_urls(item):
    raw = getattr(item, 'image_urls', None)
    urls = []
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                urls = [str(v).strip() for v in parsed if str(v).strip()]
        except Exception:
            urls = []
    if not urls and getattr(item, 'image_url', None):
        urls = [item.image_url]
    return ','.join(urls)


def export_file_urls(item):
    raw = getattr(item, 'file_urls', None)
    urls = []
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                urls = [str(v).strip() for v in parsed if str(v).strip()]
        except Exception:
            urls = []
    if not urls and getattr(item, 'file_url', None):
        urls = [item.file_url]
    return ','.join(urls)


EXPORT_FIELD_MAP = {
    'id': ('ID', lambda item: item.id),
    'name': ('查询名称', lambda item: item.name),
    'query_code': ('查询编码', lambda item: item.query_code),
    'category': ('查询分类', lambda item: item.category or ''),
    'keyword': ('关键字', lambda item: item.keyword or ''),
    'data_source': ('数据源', lambda item: item.data_source or ''),
    'owner': ('负责人', lambda item: item.owner or ''),
    'image_url': ('图片URL', lambda item: item.image_url or ''),
    'image_urls': ('图片URL列表', export_image_urls),
    'file_url': ('文件URL', lambda item: item.file_url or ''),
    'file_urls': ('文件URL列表', export_file_urls),
    'priority': ('优先级', lambda item: item.priority if item.priority is not None else 0),
    'is_active': ('状态', lambda item: '启用' if item.is_active else '停用'),
    'description': ('描述', lambda item: item.description or ''),
    'created_at': ('创建时间', lambda item: item.created_at.strftime('%Y-%m-%d %H:%M:%S') if item.created_at else ''),
    'updated_at': ('更新时间', lambda item: item.updated_at.strftime('%Y-%m-%d %H:%M:%S') if item.updated_at else ''),
}

IMPORT_HEADER_MAP = {
    '查询名称': 'name',
    '查询编码': 'query_code',
    '查询分类': 'category',
    '关键字': 'keyword',
    '数据源': 'data_source',
    '负责人': 'owner',
    '图片URL列表': 'image_urls',
    '图片URL': 'image_url',
    '图片': 'image_url',
    '文件URL列表': 'file_urls',
    '文件URL': 'file_url',
    '文件': 'file_url',
    '优先级': 'priority',
    '状态': 'is_active',
    '描述': 'description',
    'name': 'name',
    'query_code': 'query_code',
    'category': 'category',
    'keyword': 'keyword',
    'data_source': 'data_source',
    'owner': 'owner',
    'image_urls': 'image_urls',
    'image_url': 'image_url',
    'file_urls': 'file_urls',
    'file_url': 'file_url',
    'priority': 'priority',
    'is_active': 'is_active',
    'description': 'description',
}


class QueryManagementSchemaError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


def parse_bool(value, default=None):
    if value is None or value == '':
        return default
    if isinstance(value, bool):
        return value
    raw = str(value).strip().lower()
    if raw in {'1', 'true', 'yes', 'on', '是', '启用'}:
        return True
    if raw in {'0', 'false', 'no', 'off', '否', '停用'}:
        return False
    return default


def parse_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def build_error_row(line, reason, row):
    return {
        'line': line,
        'reason': reason,
        'row': {k: ('' if v is None else str(v)) for k, v in (row or {}).items()},
    }
