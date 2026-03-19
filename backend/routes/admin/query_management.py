# -*- coding: utf-8 -*-
"""
后台管理 - 查询管理模块
"""
from flask import jsonify, request, session
from backend.utils import login_required
from backend.common.tabular import build_table_response, normalize_table_file_type, read_table_file
from . import bp


def init_query_management_routes(db, models):
    """初始化查询管理相关路由"""
    Admin = models['Admin']
    QueryManagement = models['QueryManagement']

    export_field_map = {
        'id': ('ID', lambda item: item.id),
        'name': ('查询名称', lambda item: item.name),
        'query_code': ('查询编码', lambda item: item.query_code),
        'category': ('查询分类', lambda item: item.category or ''),
        'keyword': ('关键字', lambda item: item.keyword or ''),
        'data_source': ('数据源', lambda item: item.data_source or ''),
        'owner': ('负责人', lambda item: item.owner or ''),
        'priority': ('优先级', lambda item: item.priority if item.priority is not None else 0),
        'is_active': ('状态', lambda item: '启用' if item.is_active else '停用'),
        'description': ('描述', lambda item: item.description or ''),
        'created_at': ('创建时间', lambda item: item.created_at.strftime('%Y-%m-%d %H:%M:%S') if item.created_at else ''),
        'updated_at': ('更新时间', lambda item: item.updated_at.strftime('%Y-%m-%d %H:%M:%S') if item.updated_at else ''),
    }

    import_header_map = {
        '查询名称': 'name',
        '查询编码': 'query_code',
        '查询分类': 'category',
        '关键字': 'keyword',
        '数据源': 'data_source',
        '负责人': 'owner',
        '优先级': 'priority',
        '状态': 'is_active',
        '描述': 'description',
        # 兼容英文模板
        'name': 'name',
        'query_code': 'query_code',
        'category': 'category',
        'keyword': 'keyword',
        'data_source': 'data_source',
        'owner': 'owner',
        'priority': 'priority',
        'is_active': 'is_active',
        'description': 'description',
    }

    def has_permission(code):
        username = session.get('username')
        if not username:
            return False
        user = Admin.query.filter_by(username=username).first()
        return bool(user and user.has_menu_code_access(code))

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

    @bp.route('/api/admin/query-management', methods=['GET', 'POST'])
    @login_required
    def manage_query_management_list():
        if request.method == 'GET':
            if not has_permission('system_query_management'):
                return jsonify({'error': '无权限查看查询管理列表'}), 403

            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 20, type=int)
            search = (request.args.get('search') or '').strip()
            category = (request.args.get('category') or '').strip()
            owner = (request.args.get('owner') or '').strip()
            is_active = parse_bool(request.args.get('is_active'))

            query = QueryManagement.query
            if search:
                query = query.filter(db.or_(
                    QueryManagement.name.ilike(f'%{search}%'),
                    QueryManagement.query_code.ilike(f'%{search}%'),
                    QueryManagement.keyword.ilike(f'%{search}%'),
                    QueryManagement.data_source.ilike(f'%{search}%'),
                    QueryManagement.owner.ilike(f'%{search}%'),
                ))
            if category:
                query = query.filter(QueryManagement.category == category)
            if owner:
                query = query.filter(QueryManagement.owner.ilike(f'%{owner}%'))
            if is_active is not None:
                query = query.filter(QueryManagement.is_active == is_active)

            pagination = query.order_by(QueryManagement.priority.desc(), QueryManagement.id.desc()).paginate(
                page=page,
                per_page=per_page,
                error_out=False,
            )
            return jsonify({
                'items': [item.to_dict() for item in pagination.items],
                'total': pagination.total,
                'page': page,
                'per_page': per_page,
            })

        if not has_permission('system_query_management_add'):
            return jsonify({'error': '无权限新增查询配置'}), 403

        data = request.get_json() or {}
        name = str(data.get('name') or '').strip()
        query_code = str(data.get('query_code') or '').strip()

        if not name:
            return jsonify({'error': '查询名称不能为空'}), 400
        if not query_code:
            return jsonify({'error': '查询编码不能为空'}), 400
        if QueryManagement.query.filter_by(query_code=query_code).first():
            return jsonify({'error': '查询编码已存在'}), 400

        item = QueryManagement(
            name=name,
            query_code=query_code,
            category=str(data.get('category') or 'general').strip() or 'general',
            keyword=str(data.get('keyword') or '').strip() or None,
            data_source=str(data.get('data_source') or '').strip() or None,
            owner=str(data.get('owner') or '').strip() or None,
            priority=parse_int(data.get('priority'), default=0),
            is_active=parse_bool(data.get('is_active'), default=True),
            description=str(data.get('description') or '').strip() or None,
        )

        try:
            db.session.add(item)
            db.session.commit()
            return jsonify(item.to_dict()), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    @bp.route('/api/admin/query-management/<int:item_id>', methods=['GET', 'PUT', 'DELETE'])
    @login_required
    def manage_query_management_detail(item_id):
        item = QueryManagement.query.get_or_404(item_id)

        if request.method == 'GET':
            if not has_permission('system_query_management'):
                return jsonify({'error': '无权限查看查询配置'}), 403
            return jsonify(item.to_dict())

        if request.method == 'PUT':
            if not has_permission('system_query_management_edit'):
                return jsonify({'error': '无权限编辑查询配置'}), 403

            data = request.get_json() or {}
            if 'name' in data and not str(data.get('name') or '').strip():
                return jsonify({'error': '查询名称不能为空'}), 400

            if 'query_code' in data:
                next_code = str(data.get('query_code') or '').strip()
                if not next_code:
                    return jsonify({'error': '查询编码不能为空'}), 400
                duplicate = QueryManagement.query.filter(
                    QueryManagement.query_code == next_code,
                    QueryManagement.id != item.id,
                ).first()
                if duplicate:
                    return jsonify({'error': '查询编码已存在'}), 400

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

            try:
                db.session.commit()
                return jsonify(item.to_dict())
            except Exception as e:
                db.session.rollback()
                return jsonify({'error': str(e)}), 500

        if not has_permission('system_query_management_delete'):
            return jsonify({'error': '无权限删除查询配置'}), 403

        try:
            db.session.delete(item)
            db.session.commit()
            return jsonify({'message': '删除成功'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    @bp.route('/api/admin/query-management/export', methods=['GET', 'POST'])
    @login_required
    def export_query_management():
        if not has_permission('system_query_management'):
            return jsonify({'error': '无权限导出查询配置'}), 403

        if request.method == 'GET':
            data = request.args or {}
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
            data = request.get_json() or {}
            ids = data.get('ids') or []
            fields = data.get('fields') or []
            export_mode = str(data.get('export_mode') or 'selected').strip()
            filters = data.get('filters') or {}
            file_type = normalize_table_file_type(data.get('file_type'), default='csv')

        valid_fields = [field for field in fields if field in export_field_map]
        if not valid_fields:
            valid_fields = list(export_field_map.keys())

        if export_mode == 'filtered':
            query = QueryManagement.query
            search = str(filters.get('search') or '').strip()
            category = str(filters.get('category') or '').strip()
            owner = str(filters.get('owner') or '').strip()
            is_active = parse_bool(filters.get('is_active'))

            if search:
                query = query.filter(db.or_(
                    QueryManagement.name.ilike(f'%{search}%'),
                    QueryManagement.query_code.ilike(f'%{search}%'),
                    QueryManagement.keyword.ilike(f'%{search}%'),
                    QueryManagement.data_source.ilike(f'%{search}%'),
                    QueryManagement.owner.ilike(f'%{search}%'),
                ))
            if category:
                query = query.filter(QueryManagement.category == category)
            if owner:
                query = query.filter(QueryManagement.owner.ilike(f'%{owner}%'))
            if is_active is not None:
                query = query.filter(QueryManagement.is_active == is_active)

            items = query.order_by(QueryManagement.id.asc()).all()
        else:
            if not isinstance(ids, list) or not ids:
                return jsonify({'error': '请先勾选要导出的查询数据'}), 400
            items = QueryManagement.query.filter(QueryManagement.id.in_(ids)).order_by(QueryManagement.id.asc()).all()

        headers = [export_field_map[field][0] for field in valid_fields]
        rows = [[export_field_map[field][1](item) for field in valid_fields] for item in items]
        try:
            return build_table_response(headers, rows, 'query_management_export', file_type=file_type)
        except RuntimeError as e:
            return jsonify({'error': str(e)}), 500

    @bp.route('/api/admin/query-management/template', methods=['GET'])
    @login_required
    def download_query_management_template():
        if not has_permission('system_query_management'):
            return jsonify({'error': '无权限下载查询管理导入模板'}), 403

        file_type = normalize_table_file_type(request.args.get('file_type'), default='csv')
        headers = ['查询名称', '查询编码', '查询分类', '关键字', '数据源', '负责人', '优先级', '状态', '描述']
        rows = [['订单主查询', 'order_main_query', 'order', '订单,时间范围', 'orders', 'admin', 10, '启用', '查询模板示例']]
        try:
            return build_table_response(headers, rows, 'query_management_import_template', file_type=file_type)
        except RuntimeError as e:
            return jsonify({'error': str(e)}), 500

    @bp.route('/api/admin/query-management/import', methods=['POST'])
    @login_required
    def import_query_management():
        if not has_permission('system_query_management_edit'):
            return jsonify({'error': '无权限导入查询配置'}), 403

        file = request.files.get('file')
        if not file:
            return jsonify({'error': '请上传导入文件'}), 400

        try:
            fieldnames, rows_with_line, _ = read_table_file(file)
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        except RuntimeError as e:
            return jsonify({'error': str(e)}), 500

        if not fieldnames:
            return jsonify({'error': '导入内容为空'}), 400

        row_header_map = {}
        for header in fieldnames:
            key = (header or '').strip()
            if key in import_header_map:
                row_header_map[header] = import_header_map[key]

        if 'name' not in row_header_map.values() or 'query_code' not in row_header_map.values():
            return jsonify({'error': '导入文件缺少“查询名称/查询编码”列'}), 400

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
                priority = parse_int(mapped.get('priority'), default=0)
                is_active = parse_bool(mapped.get('is_active'), default=True)
                description = str(mapped.get('description') or '').strip() or None

                if not name or not query_code:
                    errors.append(build_error_row(line, '查询名称和查询编码不能为空', row))
                    continue

                item = QueryManagement.query.filter_by(query_code=query_code).first()
                if item:
                    item.name = name
                    item.category = category
                    item.keyword = keyword
                    item.data_source = data_source
                    item.owner = owner
                    item.priority = priority
                    item.is_active = is_active
                    item.description = description
                    updated += 1
                else:
                    item = QueryManagement(
                        name=name,
                        query_code=query_code,
                        category=category,
                        keyword=keyword,
                        data_source=data_source,
                        owner=owner,
                        priority=priority,
                        is_active=is_active,
                        description=description,
                    )
                    db.session.add(item)
                    created += 1

            if errors:
                db.session.rollback()
                return jsonify({
                    'error': '导入失败，存在错误数据',
                    'error_rows': errors[:500],
                    'error_count': len(errors),
                }), 400

            db.session.commit()
            return jsonify({'message': '导入成功', 'created': created, 'updated': updated})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
