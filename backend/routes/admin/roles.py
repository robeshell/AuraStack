# -*- coding: utf-8 -*-
"""
后台管理 - 角色管理模块
"""
from flask import jsonify, request, session
from backend.utils import login_required
from backend.common.tabular import build_table_response, normalize_table_file_type, read_table_file
from . import bp


def init_roles_routes(db, models):
    """初始化角色管理相关路由"""
    Role = models['Role']
    Menu = models['Menu']
    Admin = models['Admin']
    export_field_map = {
        'id': ('ID', lambda item: item.id),
        'name': ('角色名称', lambda item: item.name),
        'code': ('角色编码', lambda item: item.code),
        'description': ('描述', lambda item: item.description or ''),
        'menu_codes': ('菜单编码', lambda item: ','.join([menu.code for menu in item.menus])),
        'menu_names': ('菜单名称', lambda item: ','.join([menu.name for menu in item.menus])),
        'created_at': ('创建时间', lambda item: item.created_at.strftime('%Y-%m-%d %H:%M:%S') if item.created_at else ''),
    }
    import_header_map = {
        '角色名称': 'name',
        '角色编码': 'code',
        '描述': 'description',
        '菜单编码': 'menu_codes',
    }

    def has_permission(code):
        username = session.get('username')
        if not username:
            return False
        user = Admin.query.filter_by(username=username).first()
        return bool(user and user.has_menu_code_access(code))

    def parse_codes(raw_value):
        if raw_value is None:
            return []
        text = str(raw_value).strip()
        if not text:
            return []
        normalized = text.replace('，', ',')
        return [item.strip() for item in normalized.split(',') if item.strip()]

    def build_error_row(line, reason, row):
        return {
            'line': line,
            'reason': reason,
            'row': {k: ('' if v is None else str(v)) for k, v in (row or {}).items()}
        }

    @bp.route('/api/admin/roles', methods=['GET', 'POST'])
    @login_required
    def manage_roles():
        if request.method == 'GET':
            if not has_permission('system_roles'):
                return jsonify({'error': '无权限查看角色列表'}), 403
            roles = Role.query.all()
            return jsonify([r.to_dict(include_menus=True) for r in roles])

        if not has_permission('system_roles_add'):
            return jsonify({'error': '无权限新增角色'}), 403

        data = request.json
        if not data.get('name'):
            return jsonify({'error': '角色名称不能为空'}), 400
        if not data.get('code'):
            return jsonify({'error': '角色编码不能为空'}), 400

        if Role.query.filter_by(code=data['code']).first():
            return jsonify({'error': '角色编码已存在'}), 400

        new_role = Role(
            name=data['name'],
            code=data['code'],
            description=data.get('description')
        )

        if 'menu_ids' in data:
            menus = Menu.query.filter(Menu.id.in_(data['menu_ids'])).all()
            new_role.menus = menus

        db.session.add(new_role)
        db.session.commit()
        return jsonify(new_role.to_dict(include_menus=True)), 201

    @bp.route('/api/admin/roles/<int:role_id>', methods=['PUT', 'DELETE'])
    @login_required
    def update_role(role_id):
        role = Role.query.get_or_404(role_id)

        if request.method == 'DELETE':
            username = session.get('username')
            current_user = Admin.query.filter_by(username=username).first()
            if not current_user or not current_user.has_menu_code_access('system_roles_delete'):
                return jsonify({'error': '无权限删除角色'}), 403

            db.session.delete(role)
            db.session.commit()
            return jsonify({'message': '删除成功'})

        username = session.get('username')
        current_user = Admin.query.filter_by(username=username).first()
        if not current_user or not current_user.has_menu_code_access('system_roles_edit'):
            return jsonify({'error': '无权限编辑角色'}), 403

        data = request.json
        if 'name' in data:
            role.name = data['name']
        if 'code' in data:
            role.code = data['code']
        if 'description' in data:
            role.description = data['description']

        if 'menu_ids' in data:
            menus = Menu.query.filter(Menu.id.in_(data['menu_ids'])).all()
            role.menus = menus

        db.session.commit()
        return jsonify(role.to_dict(include_menus=True))

    @bp.route('/api/admin/roles/export', methods=['POST'])
    @login_required
    def export_roles():
        if not has_permission('system_roles'):
            return jsonify({'error': '无权限导出角色'}), 403

        data = request.get_json() or {}
        ids = data.get('ids') or []
        fields = data.get('fields') or []
        export_mode = (data.get('export_mode') or 'selected').strip()
        filters = data.get('filters') or {}
        file_type = normalize_table_file_type(data.get('file_type'), default='csv')

        valid_fields = [field for field in fields if field in export_field_map]
        if not valid_fields:
            valid_fields = list(export_field_map.keys())

        if export_mode == 'filtered':
            query = Role.query
            search = str(filters.get('search') or '').strip()
            if search:
                query = query.filter(db.or_(
                    Role.name.ilike(f'%{search}%'),
                    Role.code.ilike(f'%{search}%')
                ))
            items = query.order_by(Role.id.asc()).all()
        else:
            if not isinstance(ids, list) or not ids:
                return jsonify({'error': '请先勾选要导出的角色数据'}), 400
            items = Role.query.filter(Role.id.in_(ids)).order_by(Role.id.asc()).all()

        headers = [export_field_map[field][0] for field in valid_fields]
        rows = [[export_field_map[field][1](item) for field in valid_fields] for item in items]
        try:
            return build_table_response(headers, rows, 'roles_export', file_type=file_type)
        except RuntimeError as e:
            return jsonify({'error': str(e)}), 500

    @bp.route('/api/admin/roles/template', methods=['GET'])
    @login_required
    def download_roles_template():
        if not has_permission('system_roles'):
            return jsonify({'error': '无权限下载角色导入模板'}), 403

        file_type = normalize_table_file_type(request.args.get('file_type'), default='csv')
        headers = ['角色名称', '角色编码', '描述', '菜单编码']
        rows = [['示例角色', 'demo_role', '示例描述', 'dashboard,system_users']]
        try:
            return build_table_response(headers, rows, 'roles_import_template', file_type=file_type)
        except RuntimeError as e:
            return jsonify({'error': str(e)}), 500

    @bp.route('/api/admin/roles/import', methods=['POST'])
    @login_required
    def import_roles():
        if not has_permission('system_roles_edit'):
            return jsonify({'error': '无权限导入角色'}), 403

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

        if 'name' not in row_header_map.values() or 'code' not in row_header_map.values():
            return jsonify({'error': '导入文件缺少“角色名称/角色编码”列'}), 400

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
                code = str(mapped.get('code') or '').strip()
                description = str(mapped.get('description') or '').strip() or None
                menu_codes = parse_codes(mapped.get('menu_codes'))

                if not name or not code:
                    errors.append(build_error_row(line, '角色名称和编码不能为空', row))
                    continue

                menus = []
                if menu_codes:
                    menus = Menu.query.filter(Menu.code.in_(menu_codes)).all()
                    found_codes = {menu.code for menu in menus}
                    missing_codes = [item for item in menu_codes if item not in found_codes]
                    if missing_codes:
                        errors.append(build_error_row(line, f'菜单编码不存在: {", ".join(missing_codes)}', row))
                        continue

                item = Role.query.filter_by(code=code).first()
                if item:
                    item.name = name
                    item.description = description
                    if menu_codes:
                        item.menus = menus
                    updated += 1
                else:
                    item = Role(name=name, code=code, description=description)
                    item.menus = menus
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
