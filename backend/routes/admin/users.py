# -*- coding: utf-8 -*-
"""
后台管理 - 用户管理模块
"""
from flask import jsonify, request, session
from backend.utils import login_required
from backend.common.tabular import build_table_response, normalize_table_file_type, read_table_file
from . import bp


def init_users_routes(db, models):
    """初始化用户管理相关路由"""
    Admin = models['Admin']
    Role = models['Role']
    export_field_map = {
        'id': ('ID', lambda item: item.id),
        'username': ('用户名', lambda item: item.username),
        'role_names': ('角色名称', lambda item: ','.join([role.name for role in item.roles])),
        'role_codes': ('角色编码', lambda item: ','.join([role.code for role in item.roles])),
        'created_at': ('创建时间', lambda item: item.created_at.strftime('%Y-%m-%d %H:%M:%S') if item.created_at else ''),
    }
    import_header_map = {
        '用户名': 'username',
        '密码': 'password',
        '角色编码': 'role_codes',
    }

    def has_permission(code):
        username = session.get('username')
        if not username:
            return False
        user = Admin.query.filter_by(username=username).first()
        return bool(user and user.has_menu_code_access(code))

    def parse_role_codes(raw_value):
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

    @bp.route('/api/admin/users', methods=['GET', 'POST'])
    @login_required
    def manage_users():
        if request.method == 'GET':
            if not has_permission('system_users'):
                return jsonify({'error': '无权限查看用户列表'}), 403

            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 20, type=int)
            search = request.args.get('search', '').strip()

            query = Admin.query
            if search:
                query = query.filter(Admin.username.ilike(f'%{search}%'))

            pagination = query.order_by(Admin.id.desc()).paginate(page=page, per_page=per_page)
            return jsonify({
                'items': [u.to_dict() for u in pagination.items],
                'total': pagination.total
            })

        if not has_permission('system_users_add'):
            return jsonify({'error': '无权限新增用户'}), 403

        data = request.json
        if not data.get('username') or not data.get('password'):
            return jsonify({'error': '用户名和密码不能为空'}), 400

        if Admin.query.filter_by(username=data['username']).first():
            return jsonify({'error': '用户名已存在'}), 400

        new_user = Admin(username=data['username'])
        new_user.set_password(data['password'])

        if 'role_ids' in data:
            roles = Role.query.filter(Role.id.in_(data['role_ids'])).all()
            new_user.roles = roles

        db.session.add(new_user)
        db.session.commit()
        return jsonify(new_user.to_dict()), 201

    @bp.route('/api/admin/users/<int:user_id>', methods=['PUT', 'DELETE'])
    @login_required
    def update_user(user_id):
        user = Admin.query.get_or_404(user_id)

        if request.method == 'DELETE':
            username = session.get('username')
            current_user = Admin.query.filter_by(username=username).first()
            if not current_user or not current_user.has_menu_code_access('system_users_delete'):
                return jsonify({'error': '无权限删除用户'}), 403

            if user.username == username:
                return jsonify({'error': '不能删除当前登录账号'}), 400

            db.session.delete(user)
            db.session.commit()
            return jsonify({'message': '删除成功'})

        username = session.get('username')
        current_user = Admin.query.filter_by(username=username).first()
        if not current_user or not current_user.has_menu_code_access('system_users_edit'):
            return jsonify({'error': '无权限编辑用户'}), 403

        data = request.json
        if 'password' in data and data['password']:
            user.set_password(data['password'])

        if 'role_ids' in data:
            roles = Role.query.filter(Role.id.in_(data['role_ids'])).all()
            user.roles = roles

        db.session.commit()
        return jsonify(user.to_dict())

    @bp.route('/api/admin/users/export', methods=['POST'])
    @login_required
    def export_users():
        if not has_permission('system_users'):
            return jsonify({'error': '无权限导出用户'}), 403

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
            query = Admin.query
            search = str(filters.get('search') or '').strip()
            if search:
                query = query.filter(Admin.username.ilike(f'%{search}%'))
            items = query.order_by(Admin.id.asc()).all()
        else:
            if not isinstance(ids, list) or not ids:
                return jsonify({'error': '请先勾选要导出的用户数据'}), 400
            items = Admin.query.filter(Admin.id.in_(ids)).order_by(Admin.id.asc()).all()

        if not items:
            return jsonify({'error': '未找到可导出的用户数据'}), 404

        headers = [export_field_map[field][0] for field in valid_fields]
        rows = [[export_field_map[field][1](item) for field in valid_fields] for item in items]
        try:
            return build_table_response(headers, rows, 'users_export', file_type=file_type)
        except RuntimeError as e:
            return jsonify({'error': str(e)}), 500

    @bp.route('/api/admin/users/template', methods=['GET'])
    @login_required
    def download_users_template():
        if not has_permission('system_users'):
            return jsonify({'error': '无权限下载用户导入模板'}), 403

        file_type = normalize_table_file_type(request.args.get('file_type'), default='csv')
        headers = ['用户名', '密码', '角色编码']
        rows = [['demo_user', '123456', 'super_admin']]
        try:
            return build_table_response(headers, rows, 'users_import_template', file_type=file_type)
        except RuntimeError as e:
            return jsonify({'error': str(e)}), 500

    @bp.route('/api/admin/users/import', methods=['POST'])
    @login_required
    def import_users():
        if not has_permission('system_users_edit'):
            return jsonify({'error': '无权限导入用户'}), 403

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

        if 'username' not in row_header_map.values():
            return jsonify({'error': '导入文件缺少“用户名”列'}), 400

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

                username = str(mapped.get('username') or '').strip()
                password = str(mapped.get('password') or '').strip()
                role_codes = parse_role_codes(mapped.get('role_codes'))

                if not username:
                    errors.append(build_error_row(line, '用户名不能为空', row))
                    continue

                roles = []
                if role_codes:
                    roles = Role.query.filter(Role.code.in_(role_codes)).all()
                    found_codes = {role.code for role in roles}
                    missing_codes = [code for code in role_codes if code not in found_codes]
                    if missing_codes:
                        errors.append(build_error_row(line, f'角色编码不存在: {", ".join(missing_codes)}', row))
                        continue

                item = Admin.query.filter_by(username=username).first()
                if item:
                    if password:
                        item.set_password(password)
                    if role_codes:
                        item.roles = roles
                    updated += 1
                else:
                    if not password:
                        errors.append(build_error_row(line, '新增用户必须提供密码', row))
                        continue
                    item = Admin(username=username)
                    item.set_password(password)
                    item.roles = roles
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
