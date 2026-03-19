# -*- coding: utf-8 -*-
"""
后台管理 - 数据字典模块
"""
from flask import jsonify, request, session
from backend.utils import login_required
from backend.common.tabular import build_table_response, normalize_table_file_type, read_table_file
from . import bp


def init_dicts_routes(db, models):
    """初始化数据字典相关路由"""
    Admin = models['Admin']
    DictType = models['DictType']
    DictItem = models['DictItem']
    csv_header_to_field = {
        '字典标签': 'label',
        '字典值': 'value',
        '标签颜色': 'color',
        '排序': 'sort_order',
        '是否默认': 'is_default',
        '是否启用': 'is_active',
        '备注': 'description',
    }
    # 兼容历史英文模板，优先推荐使用中文表头
    legacy_csv_header_to_field = {
        'label': 'label',
        'value': 'value',
        'color': 'color',
        'sort_order': 'sort_order',
        'is_default': 'is_default',
        'is_active': 'is_active',
        'description': 'description',
    }

    def has_permission(code):
        username = session.get('username')
        if not username:
            return False
        user = Admin.query.filter_by(username=username).first()
        return bool(user and user.has_menu_code_access(code))

    def parse_bool(value):
        if value is None or value == '':
            return None
        if isinstance(value, bool):
            return value
        value = str(value).strip().lower()
        if value in {'1', 'true', 'yes', 'on', '是', '启用'}:
            return True
        if value in {'0', 'false', 'no', 'off', '否', '停用'}:
            return False
        return None

    def parse_int(value, default=0):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @bp.route('/api/admin/dicts/options', methods=['GET'])
    @login_required
    def get_dict_options():
        """按字典编码批量获取启用中的字典项（用于业务表单下拉）"""
        raw_codes = (request.args.get('codes') or '').strip()
        if not raw_codes:
            return jsonify({'error': 'codes 参数不能为空'}), 400

        codes = []
        seen = set()
        for code in [c.strip() for c in raw_codes.split(',') if c.strip()]:
            if code in seen:
                continue
            seen.add(code)
            codes.append(code)

        dict_types = DictType.query.filter(
            DictType.code.in_(codes),
            DictType.is_active.is_(True)
        ).all()
        type_map = {item.code: item for item in dict_types}

        result = {}
        for code in codes:
            dict_type = type_map.get(code)
            if not dict_type:
                result[code] = []
                continue

            items = DictItem.query.filter(
                DictItem.dict_type_id == dict_type.id,
                DictItem.is_active.is_(True)
            ).order_by(DictItem.sort_order.asc(), DictItem.id.asc()).all()

            result[code] = [{
                'label': item.label,
                'value': item.value,
                'color': item.color,
                'is_default': item.is_default,
            } for item in items]

        return jsonify(result)

    @bp.route('/api/admin/dicts', methods=['GET', 'POST'])
    @login_required
    def manage_dict_types():
        if request.method == 'GET':
            if not has_permission('system_dicts'):
                return jsonify({'error': '无权限查看数据字典'}), 403

            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 20, type=int)
            search = request.args.get('search', '').strip()
            is_active = parse_bool(request.args.get('is_active'))

            query = DictType.query
            if search:
                query = query.filter(db.or_(
                    DictType.name.ilike(f'%{search}%'),
                    DictType.code.ilike(f'%{search}%')
                ))
            if is_active is not None:
                query = query.filter(DictType.is_active == is_active)

            pagination = query.order_by(
                DictType.sort_order.asc(),
                DictType.id.asc()
            ).paginate(page=page, per_page=per_page, error_out=False)

            return jsonify({
                'items': [item.to_dict() for item in pagination.items],
                'total': pagination.total,
                'page': page,
                'per_page': per_page,
            })

        if not has_permission('system_dicts_add'):
            return jsonify({'error': '无权限新增数据字典'}), 403

        data = request.get_json() or {}
        name = (data.get('name') or '').strip()
        code = (data.get('code') or '').strip()

        if not name:
            return jsonify({'error': '字典名称不能为空'}), 400
        if not code:
            return jsonify({'error': '字典编码不能为空'}), 400
        if DictType.query.filter_by(code=code).first():
            return jsonify({'error': '字典编码已存在'}), 400

        item = DictType(
            name=name,
            code=code,
            description=data.get('description'),
            sort_order=data.get('sort_order', 0),
            is_active=data.get('is_active', True)
        )
        try:
            db.session.add(item)
            db.session.commit()
            return jsonify(item.to_dict()), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    @bp.route('/api/admin/dicts/<int:dict_id>', methods=['GET', 'PUT', 'DELETE'])
    @login_required
    def manage_dict_type(dict_id):
        item = DictType.query.get_or_404(dict_id)

        if request.method == 'GET':
            if not has_permission('system_dicts'):
                return jsonify({'error': '无权限查看数据字典'}), 403
            include_items = parse_bool(request.args.get('include_items')) is True
            return jsonify(item.to_dict(include_items=include_items))

        if request.method == 'PUT':
            if not has_permission('system_dicts_edit'):
                return jsonify({'error': '无权限编辑数据字典'}), 403

            data = request.get_json() or {}
            if 'name' in data and not str(data.get('name') or '').strip():
                return jsonify({'error': '字典名称不能为空'}), 400
            if 'code' in data:
                new_code = str(data.get('code') or '').strip()
                if not new_code:
                    return jsonify({'error': '字典编码不能为空'}), 400
                duplicate = DictType.query.filter(
                    DictType.code == new_code,
                    DictType.id != item.id
                ).first()
                if duplicate:
                    return jsonify({'error': '字典编码已存在'}), 400

            for field in ['name', 'code', 'description', 'sort_order', 'is_active']:
                if field in data:
                    setattr(item, field, data[field])

            try:
                db.session.commit()
                return jsonify(item.to_dict())
            except Exception as e:
                db.session.rollback()
                return jsonify({'error': str(e)}), 500

        if not has_permission('system_dicts_delete'):
            return jsonify({'error': '无权限删除数据字典'}), 403

        if item.items.count() > 0:
            return jsonify({'error': '该字典下仍有字典项，请先清空后再删除'}), 400

        try:
            db.session.delete(item)
            db.session.commit()
            return jsonify({'message': '删除成功'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    @bp.route('/api/admin/dicts/<int:dict_id>/items', methods=['GET', 'POST'])
    @login_required
    def manage_dict_items(dict_id):
        dict_type = DictType.query.get_or_404(dict_id)

        if request.method == 'GET':
            if not has_permission('system_dicts'):
                return jsonify({'error': '无权限查看字典项'}), 403

            search = request.args.get('search', '').strip()
            is_active = parse_bool(request.args.get('is_active'))

            query = DictItem.query.filter_by(dict_type_id=dict_type.id)
            if search:
                query = query.filter(db.or_(
                    DictItem.label.ilike(f'%{search}%'),
                    DictItem.value.ilike(f'%{search}%')
                ))
            if is_active is not None:
                query = query.filter(DictItem.is_active == is_active)

            items = query.order_by(DictItem.sort_order.asc(), DictItem.id.asc()).all()
            return jsonify({
                'items': [item.to_dict() for item in items],
                'total': len(items),
                'dict_type': dict_type.to_dict(include_items=False),
            })

        if not has_permission('system_dicts_add'):
            return jsonify({'error': '无权限新增字典项'}), 403

        data = request.get_json() or {}
        label = (data.get('label') or '').strip()
        value = (data.get('value') or '').strip()

        if not label:
            return jsonify({'error': '字典标签不能为空'}), 400
        if not value:
            return jsonify({'error': '字典值不能为空'}), 400

        if DictItem.query.filter_by(dict_type_id=dict_type.id, value=value).first():
            return jsonify({'error': '同一字典下字典值不能重复'}), 400

        if data.get('is_default'):
            DictItem.query.filter_by(dict_type_id=dict_type.id, is_default=True).update({'is_default': False})

        item = DictItem(
            dict_type_id=dict_type.id,
            label=label,
            value=value,
            color=data.get('color'),
            sort_order=data.get('sort_order', 0),
            is_default=data.get('is_default', False),
            is_active=data.get('is_active', True),
            description=data.get('description')
        )
        try:
            db.session.add(item)
            db.session.commit()
            return jsonify(item.to_dict()), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    @bp.route('/api/admin/dicts/<int:dict_id>/items/export', methods=['GET'])
    @login_required
    def export_dict_items(dict_id):
        dict_type = DictType.query.get_or_404(dict_id)
        if not has_permission('system_dicts'):
            return jsonify({'error': '无权限导出字典项'}), 403
        file_type = normalize_table_file_type(request.args.get('file_type'), default='csv')

        items = DictItem.query.filter_by(dict_type_id=dict_type.id).order_by(
            DictItem.sort_order.asc(),
            DictItem.id.asc()
        ).all()

        headers = ['字典标签', '字典值', '标签颜色', '排序', '是否默认', '是否启用', '备注']
        rows = [[
            item.label,
            item.value,
            item.color or '',
            item.sort_order if item.sort_order is not None else 0,
            '是' if item.is_default else '否',
            '是' if item.is_active else '否',
            item.description or '',
        ] for item in items]
        try:
            return build_table_response(headers, rows, f'dict_{dict_type.code}_items', file_type=file_type)
        except RuntimeError as e:
            return jsonify({'error': str(e)}), 500

    @bp.route('/api/admin/dicts/<int:dict_id>/items/template', methods=['GET'])
    @login_required
    def download_dict_items_template(dict_id):
        dict_type = DictType.query.get_or_404(dict_id)
        if not has_permission('system_dicts'):
            return jsonify({'error': '无权限下载模板'}), 403
        file_type = normalize_table_file_type(request.args.get('file_type'), default='csv')
        headers = ['字典标签', '字典值', '标签颜色', '排序', '是否默认', '是否启用', '备注']
        rows = [['示例标签', 'sample_value', '#1677ff', 0, '否', '是', '可选']]
        try:
            return build_table_response(headers, rows, f'dict_{dict_type.code}_import_template', file_type=file_type)
        except RuntimeError as e:
            return jsonify({'error': str(e)}), 500

    @bp.route('/api/admin/dicts/<int:dict_id>/items/import', methods=['POST'])
    @login_required
    def import_dict_items(dict_id):
        dict_type = DictType.query.get_or_404(dict_id)
        if not has_permission('system_dicts_edit'):
            return jsonify({'error': '无权限导入字典项'}), 403

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

        header_map = {}
        for header in fieldnames:
            normalized = (header or '').strip()
            if normalized in csv_header_to_field:
                header_map[header] = csv_header_to_field[normalized]
            elif normalized in legacy_csv_header_to_field:
                header_map[header] = legacy_csv_header_to_field[normalized]

        if 'label' not in header_map.values() or 'value' not in header_map.values():
            return jsonify({'error': '导入文件缺少必填列：字典标签、字典值'}), 400

        created = 0
        updated = 0
        try:
            for line_number, row in rows_with_line:
                mapped_row = {}
                for key, val in row.items():
                    field = header_map.get(key)
                    if field:
                        mapped_row[field] = val

                label = (mapped_row.get('label') or '').strip()
                value = (mapped_row.get('value') or '').strip()
                if not label or not value:
                    return jsonify({'error': f'第 {line_number} 行“字典标签/字典值”不能为空'}), 400

                is_default = parse_bool(mapped_row.get('is_default'))
                is_active = parse_bool(mapped_row.get('is_active'))
                item = DictItem.query.filter_by(dict_type_id=dict_type.id, value=value).first()

                if item:
                    item.label = label
                    item.color = (mapped_row.get('color') or '').strip() or None
                    item.sort_order = parse_int(mapped_row.get('sort_order'), default=item.sort_order or 0)
                    item.description = (mapped_row.get('description') or '').strip() or None
                    if is_default is not None:
                        item.is_default = is_default
                    if is_active is not None:
                        item.is_active = is_active
                    updated += 1
                else:
                    item = DictItem(
                        dict_type_id=dict_type.id,
                        label=label,
                        value=value,
                        color=(mapped_row.get('color') or '').strip() or None,
                        sort_order=parse_int(mapped_row.get('sort_order'), default=0),
                        is_default=is_default is True,
                        is_active=True if is_active is None else is_active,
                        description=(mapped_row.get('description') or '').strip() or None
                    )
                    db.session.add(item)
                    created += 1

                if item.is_default:
                    DictItem.query.filter(
                        DictItem.dict_type_id == dict_type.id,
                        DictItem.value != item.value,
                        DictItem.is_default.is_(True)
                    ).update({'is_default': False})

            db.session.commit()
            return jsonify({
                'message': '导入成功',
                'created': created,
                'updated': updated,
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    @bp.route('/api/admin/dicts/items/<int:item_id>', methods=['GET', 'PUT', 'DELETE'])
    @login_required
    def manage_dict_item(item_id):
        item = DictItem.query.get_or_404(item_id)

        if request.method == 'GET':
            if not has_permission('system_dicts'):
                return jsonify({'error': '无权限查看字典项'}), 403
            return jsonify(item.to_dict())

        if request.method == 'PUT':
            if not has_permission('system_dicts_edit'):
                return jsonify({'error': '无权限编辑字典项'}), 403

            data = request.get_json() or {}
            target_type_id = data.get('dict_type_id', item.dict_type_id)
            target_type = DictType.query.get(target_type_id)
            if not target_type:
                return jsonify({'error': '字典类型不存在'}), 404

            target_value = str(data.get('value', item.value) or '').strip()
            if not target_value:
                return jsonify({'error': '字典值不能为空'}), 400

            duplicate = DictItem.query.filter(
                DictItem.dict_type_id == target_type_id,
                DictItem.value == target_value,
                DictItem.id != item.id
            ).first()
            if duplicate:
                return jsonify({'error': '同一字典下字典值不能重复'}), 400

            if 'label' in data and not str(data.get('label') or '').strip():
                return jsonify({'error': '字典标签不能为空'}), 400

            if data.get('is_default'):
                DictItem.query.filter(
                    DictItem.dict_type_id == target_type_id,
                    DictItem.id != item.id,
                    DictItem.is_default.is_(True)
                ).update({'is_default': False})

            for field in ['dict_type_id', 'label', 'value', 'color', 'sort_order', 'is_default', 'is_active', 'description']:
                if field in data:
                    setattr(item, field, data[field])

            try:
                db.session.commit()
                return jsonify(item.to_dict())
            except Exception as e:
                db.session.rollback()
                return jsonify({'error': str(e)}), 500

        if not has_permission('system_dicts_delete'):
            return jsonify({'error': '无权限删除字典项'}), 403

        try:
            db.session.delete(item)
            db.session.commit()
            return jsonify({'message': '删除成功'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
