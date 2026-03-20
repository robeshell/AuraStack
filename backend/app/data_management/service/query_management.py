# -*- coding: utf-8 -*-
"""查询管理 service 层"""

import json
import os
import uuid

from flask import current_app
from werkzeug.utils import secure_filename

from backend.common.tabular import build_table_response, normalize_table_file_type, read_table_file

from backend.app.data_management.crud.query_management import QueryManagementCRUD
from backend.app.data_management.schema.query_management import EXPORT_FIELD_MAP, IMPORT_HEADER_MAP, build_error_row, parse_bool, parse_int

ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024
ALLOWED_FILE_EXTENSIONS = {
    'pdf', 'doc', 'docx', 'xls', 'xlsx', 'csv', 'txt', 'md',
    'zip', 'rar', '7z', 'json', 'ppt', 'pptx',
}
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024


class QueryManagementServiceError(Exception):
    def __init__(self, message, status_code=400, payload=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.payload = payload or {}


class QueryManagementService:
    def __init__(self, db, query_model):
        self.db = db
        self.QueryManagement = query_model
        self.crud = QueryManagementCRUD(db, query_model)

    def get_image_upload_dir(self):
        upload_dir = os.path.join(current_app.root_path, 'instance', 'uploads', 'query_management')
        os.makedirs(upload_dir, exist_ok=True)
        return upload_dir

    def get_file_upload_dir(self):
        upload_dir = os.path.join(current_app.root_path, 'instance', 'uploads', 'query_management_files')
        os.makedirs(upload_dir, exist_ok=True)
        return upload_dir

    @staticmethod
    def sanitize_image_filename(filename):
        raw_name = str(filename or '').strip()
        safe_name = secure_filename(raw_name)
        if not safe_name:
            raise QueryManagementServiceError('无效的图片文件名', 400)
        return safe_name

    @staticmethod
    def _extract_image_ext(filename):
        safe_name = QueryManagementService.sanitize_image_filename(filename)
        if '.' not in safe_name:
            raise QueryManagementServiceError('仅支持 jpg/png/gif/webp 图片', 400)
        ext = safe_name.rsplit('.', 1)[1].lower()
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            raise QueryManagementServiceError('仅支持 jpg/png/gif/webp 图片', 400)
        return ext

    def save_image(self, file_storage):
        if not file_storage:
            raise QueryManagementServiceError('请先选择图片文件', 400)

        ext = self._extract_image_ext(file_storage.filename)

        file_storage.stream.seek(0, os.SEEK_END)
        file_size = file_storage.stream.tell()
        file_storage.stream.seek(0)

        if file_size <= 0:
            raise QueryManagementServiceError('图片文件不能为空', 400)
        if file_size > MAX_IMAGE_SIZE_BYTES:
            raise QueryManagementServiceError('图片不能超过 5MB', 400)

        final_name = f'{uuid.uuid4().hex}.{ext}'
        save_path = os.path.join(self.get_image_upload_dir(), final_name)

        try:
            file_storage.save(save_path)
            return {
                'message': '上传成功',
                'filename': final_name,
                'url': f'/api/admin/query-management/image/{final_name}',
            }
        except Exception as e:
            raise QueryManagementServiceError(str(e), 500) from e

    def save_file(self, file_storage):
        if not file_storage:
            raise QueryManagementServiceError('请先选择文件', 400)

        safe_name = self.sanitize_image_filename(file_storage.filename)
        if '.' not in safe_name:
            raise QueryManagementServiceError('无效的文件类型', 400)
        ext = safe_name.rsplit('.', 1)[1].lower()
        if ext not in ALLOWED_FILE_EXTENSIONS:
            raise QueryManagementServiceError('仅支持常见文档/压缩包格式', 400)

        file_storage.stream.seek(0, os.SEEK_END)
        file_size = file_storage.stream.tell()
        file_storage.stream.seek(0)

        if file_size <= 0:
            raise QueryManagementServiceError('文件不能为空', 400)
        if file_size > MAX_FILE_SIZE_BYTES:
            raise QueryManagementServiceError('文件不能超过 20MB', 400)

        final_name = f'{uuid.uuid4().hex}_{safe_name}'
        save_path = os.path.join(self.get_file_upload_dir(), final_name)

        try:
            file_storage.save(save_path)
            return {
                'message': '上传成功',
                'filename': final_name,
                'url': f'/api/admin/query-management/file/{final_name}',
            }
        except Exception as e:
            raise QueryManagementServiceError(str(e), 500) from e

    @staticmethod
    def normalize_image_urls(raw_value):
        if raw_value is None:
            return []
        if isinstance(raw_value, list):
            return [str(item).strip() for item in raw_value if str(item).strip()]
        if isinstance(raw_value, str):
            text = raw_value.strip()
            if not text:
                return []
            try:
                parsed = json.loads(text)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]
            except Exception:
                pass
            if any(sep in text for sep in ['\n', ',', '，', ';', '；']):
                normalized = text.replace('，', ',').replace('；', ';').replace('\n', ';')
                chunks = []
                for segment in normalized.split(';'):
                    chunks.extend(segment.split(','))
                return [item.strip() for item in chunks if item.strip()]
            return [text]
        return []

    @staticmethod
    def normalize_file_urls(raw_value):
        return QueryManagementService.normalize_image_urls(raw_value)

    @staticmethod
    def serialize_image_urls(urls):
        return json.dumps(urls, ensure_ascii=False) if urls else None

    def list_items(self, page=1, per_page=20, search='', category='', owner='', is_active=None):
        query = self.crud.query()
        if search:
            query = query.filter(self.db.or_(
                self.QueryManagement.name.ilike(f'%{search}%'),
                self.QueryManagement.query_code.ilike(f'%{search}%'),
                self.QueryManagement.keyword.ilike(f'%{search}%'),
                self.QueryManagement.data_source.ilike(f'%{search}%'),
                self.QueryManagement.owner.ilike(f'%{search}%'),
            ))
        if category:
            query = query.filter(self.QueryManagement.category == category)
        if owner:
            query = query.filter(self.QueryManagement.owner.ilike(f'%{owner}%'))
        if is_active is not None:
            query = query.filter(self.QueryManagement.is_active == is_active)

        pagination = query.order_by(self.QueryManagement.priority.desc(), self.QueryManagement.id.desc()).paginate(
            page=page,
            per_page=per_page,
            error_out=False,
        )
        return {
            'items': [item.to_dict() for item in pagination.items],
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
        }

    def create_item(self, data):
        name = str(data.get('name') or '').strip()
        query_code = str(data.get('query_code') or '').strip()
        if not name:
            raise QueryManagementServiceError('查询名称不能为空', 400)
        if not query_code:
            raise QueryManagementServiceError('查询编码不能为空', 400)
        if self.crud.get_by_code(query_code):
            raise QueryManagementServiceError('查询编码已存在', 400)

        item = self.QueryManagement(
            name=name,
            query_code=query_code,
            category=str(data.get('category') or 'general').strip() or 'general',
            keyword=str(data.get('keyword') or '').strip() or None,
            data_source=str(data.get('data_source') or '').strip() or None,
            owner=str(data.get('owner') or '').strip() or None,
            image_url=None,
            image_urls=None,
            file_url=None,
            file_urls=None,
            priority=parse_int(data.get('priority'), default=0),
            is_active=parse_bool(data.get('is_active'), default=True),
            description=str(data.get('description') or '').strip() or None,
        )
        image_urls = self.normalize_image_urls(data.get('image_urls'))
        if not image_urls:
            image_urls = self.normalize_image_urls(data.get('image_url'))
        item.image_urls = self.serialize_image_urls(image_urls)
        item.image_url = image_urls[0] if image_urls else None
        file_urls = self.normalize_file_urls(data.get('file_urls'))
        if not file_urls:
            file_urls = self.normalize_file_urls(data.get('file_url'))
        item.file_urls = self.serialize_image_urls(file_urls)
        item.file_url = file_urls[0] if file_urls else None
        try:
            self.crud.add(item)
            self.crud.commit()
            return item.to_dict(), 201
        except Exception as e:
            self.crud.rollback()
            raise QueryManagementServiceError(str(e), 500) from e

    def update_item(self, item, data):
        if 'name' in data and not str(data.get('name') or '').strip():
            raise QueryManagementServiceError('查询名称不能为空', 400)

        if 'query_code' in data:
            next_code = str(data.get('query_code') or '').strip()
            if not next_code:
                raise QueryManagementServiceError('查询编码不能为空', 400)
            duplicate = self.crud.query().filter(
                self.QueryManagement.query_code == next_code,
                self.QueryManagement.id != item.id,
            ).first()
            if duplicate:
                raise QueryManagementServiceError('查询编码已存在', 400)

        update_map = {
            'name': lambda val: str(val or '').strip(),
            'query_code': lambda val: str(val or '').strip(),
            'category': lambda val: str(val or '').strip() or 'general',
            'keyword': lambda val: str(val or '').strip() or None,
            'data_source': lambda val: str(val or '').strip() or None,
            'owner': lambda val: str(val or '').strip() or None,
            'priority': lambda val: parse_int(val, default=item.priority or 0),
            'is_active': lambda val: parse_bool(val, default=item.is_active),
            'description': lambda val: str(val or '').strip() or None,
        }
        for field, converter in update_map.items():
            if field in data:
                setattr(item, field, converter(data.get(field)))

        if 'image_urls' in data or 'image_url' in data:
            image_urls = self.normalize_image_urls(data.get('image_urls'))
            if not image_urls:
                image_urls = self.normalize_image_urls(data.get('image_url'))
            item.image_urls = self.serialize_image_urls(image_urls)
            item.image_url = image_urls[0] if image_urls else None
        if 'file_urls' in data or 'file_url' in data:
            file_urls = self.normalize_file_urls(data.get('file_urls'))
            if not file_urls:
                file_urls = self.normalize_file_urls(data.get('file_url'))
            item.file_urls = self.serialize_image_urls(file_urls)
            item.file_url = file_urls[0] if file_urls else None

        try:
            self.crud.commit()
            return item.to_dict()
        except Exception as e:
            self.crud.rollback()
            raise QueryManagementServiceError(str(e), 500) from e

    def delete_item(self, item):
        try:
            self.crud.delete(item)
            self.crud.commit()
            return {'message': '删除成功'}
        except Exception as e:
            self.crud.rollback()
            raise QueryManagementServiceError(str(e), 500) from e

    def export_items(self, data, request_method='POST'):
        if request_method == 'GET':
            ids = []
            fields = str(data.get('fields') or '').strip()
            fields = [item.strip() for item in fields.split(',') if item.strip()] if fields else []
            export_mode = 'filtered'
            filters = {
                'search': data.get('search'),
                'category': data.get('category'),
                'owner': data.get('owner'),
                'is_active': data.get('is_active'),
            }
            file_type = normalize_table_file_type(data.get('file_type'), default='csv')
        else:
            ids = data.get('ids') or []
            fields = data.get('fields') or []
            export_mode = str(data.get('export_mode') or 'selected').strip()
            filters = data.get('filters') or {}
            file_type = normalize_table_file_type(data.get('file_type'), default='csv')

        valid_fields = [field for field in fields if field in EXPORT_FIELD_MAP]
        if not valid_fields:
            valid_fields = list(EXPORT_FIELD_MAP.keys())

        if export_mode == 'filtered':
            query = self.crud.query()
            search = str(filters.get('search') or '').strip()
            category = str(filters.get('category') or '').strip()
            owner = str(filters.get('owner') or '').strip()
            is_active = parse_bool(filters.get('is_active'))

            if search:
                query = query.filter(self.db.or_(
                    self.QueryManagement.name.ilike(f'%{search}%'),
                    self.QueryManagement.query_code.ilike(f'%{search}%'),
                    self.QueryManagement.keyword.ilike(f'%{search}%'),
                    self.QueryManagement.data_source.ilike(f'%{search}%'),
                    self.QueryManagement.owner.ilike(f'%{search}%'),
                ))
            if category:
                query = query.filter(self.QueryManagement.category == category)
            if owner:
                query = query.filter(self.QueryManagement.owner.ilike(f'%{owner}%'))
            if is_active is not None:
                query = query.filter(self.QueryManagement.is_active == is_active)

            items = query.order_by(self.QueryManagement.id.asc()).all()
        else:
            if not isinstance(ids, list) or not ids:
                raise QueryManagementServiceError('请先勾选要导出的查询数据', 400)
            items = self.crud.list_by_ids(ids).order_by(self.QueryManagement.id.asc()).all()

        headers = [EXPORT_FIELD_MAP[field][0] for field in valid_fields]
        rows = [[EXPORT_FIELD_MAP[field][1](item) for field in valid_fields] for item in items]
        try:
            return build_table_response(headers, rows, 'query_management_export', file_type=file_type)
        except RuntimeError as e:
            raise QueryManagementServiceError(str(e), 500) from e

    def download_template(self, file_type_raw):
        file_type = normalize_table_file_type(file_type_raw, default='csv')
        headers = ['查询名称', '查询编码', '查询分类', '关键字', '数据源', '负责人', '图片URL列表', '文件URL列表', '优先级', '状态', '描述']
        rows = [[
            '订单主查询',
            'order_main_query',
            'order',
            '订单,时间范围',
            'orders',
            'admin',
            'https://example.com/1.png,https://example.com/2.png',
            'https://example.com/a.pdf,https://example.com/b.xlsx',
            10,
            '启用',
            '查询模板示例',
        ]]
        try:
            return build_table_response(headers, rows, 'query_management_import_template', file_type=file_type)
        except RuntimeError as e:
            raise QueryManagementServiceError(str(e), 500) from e

    def import_items(self, file_storage):
        if not file_storage:
            raise QueryManagementServiceError('请上传导入文件', 400)

        try:
            fieldnames, rows_with_line, _ = read_table_file(file_storage)
        except ValueError as e:
            raise QueryManagementServiceError(str(e), 400) from e
        except RuntimeError as e:
            raise QueryManagementServiceError(str(e), 500) from e

        if not fieldnames:
            raise QueryManagementServiceError('导入内容为空', 400)

        row_header_map = {}
        for header in fieldnames:
            key = (header or '').strip()
            if key in IMPORT_HEADER_MAP:
                row_header_map[header] = IMPORT_HEADER_MAP[key]

        if 'name' not in row_header_map.values() or 'query_code' not in row_header_map.values():
            raise QueryManagementServiceError('导入文件缺少“查询名称/查询编码”列', 400)

        created = 0
        updated = 0
        errors = []

        try:
            for line, row in rows_with_line:
                mapped = {}
                for key, value in row.items():
                    field = row_header_map.get(key)
                    if field:
                        mapped[field] = value

                name = str(mapped.get('name') or '').strip()
                query_code = str(mapped.get('query_code') or '').strip()
                category = str(mapped.get('category') or 'general').strip() or 'general'
                keyword = str(mapped.get('keyword') or '').strip() or None
                data_source = str(mapped.get('data_source') or '').strip() or None
                owner = str(mapped.get('owner') or '').strip() or None
                image_urls = self.normalize_image_urls(mapped.get('image_urls'))
                if not image_urls:
                    image_urls = self.normalize_image_urls(mapped.get('image_url'))
                file_urls = self.normalize_file_urls(mapped.get('file_urls'))
                if not file_urls:
                    file_urls = self.normalize_file_urls(mapped.get('file_url'))
                priority = parse_int(mapped.get('priority'), default=0)
                is_active = parse_bool(mapped.get('is_active'), default=True)
                description = str(mapped.get('description') or '').strip() or None

                if not name or not query_code:
                    errors.append(build_error_row(line, '查询名称和查询编码不能为空', row))
                    continue

                item = self.crud.get_by_code(query_code)
                if item:
                    item.name = name
                    item.category = category
                    item.keyword = keyword
                    item.data_source = data_source
                    item.owner = owner
                    item.image_urls = self.serialize_image_urls(image_urls)
                    item.image_url = image_urls[0] if image_urls else None
                    item.file_urls = self.serialize_image_urls(file_urls)
                    item.file_url = file_urls[0] if file_urls else None
                    item.priority = priority
                    item.is_active = is_active
                    item.description = description
                    updated += 1
                else:
                    item = self.QueryManagement(
                        name=name,
                        query_code=query_code,
                        category=category,
                        keyword=keyword,
                        data_source=data_source,
                        owner=owner,
                        image_url=image_urls[0] if image_urls else None,
                        image_urls=self.serialize_image_urls(image_urls),
                        file_url=file_urls[0] if file_urls else None,
                        file_urls=self.serialize_image_urls(file_urls),
                        priority=priority,
                        is_active=is_active,
                        description=description,
                    )
                    self.crud.add(item)
                    created += 1

            if errors:
                self.crud.rollback()
                raise QueryManagementServiceError('导入失败，存在错误数据', 400, {
                    'error_rows': errors[:500],
                    'error_count': len(errors),
                })

            self.crud.commit()
            return {'message': '导入成功', 'created': created, 'updated': updated}
        except QueryManagementServiceError:
            raise
        except Exception as e:
            self.crud.rollback()
            raise QueryManagementServiceError(str(e), 500) from e
