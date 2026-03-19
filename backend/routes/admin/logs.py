# -*- coding: utf-8 -*-
"""
后台管理 - 日志管理模块
登录日志、操作日志（含自动记录）
"""
from datetime import datetime
from flask import jsonify, request, session
from backend.utils import login_required
from backend.log_utils import get_client_ip, get_user_agent, safe_payload
from backend.common.tabular import build_table_response, normalize_table_file_type, read_table_file
from . import bp


def init_logs_routes(db, models):
    """初始化日志相关路由"""
    Admin = models['Admin']
    LoginLog = models['LoginLog']
    OperationLog = models['OperationLog']
    login_export_field_map = {
        'id': ('ID', lambda item: item.id),
        'username': ('用户名', lambda item: item.username),
        'status': ('状态', lambda item: item.status),
        'ip': ('IP 地址', lambda item: item.ip or ''),
        'user_agent': ('User-Agent', lambda item: item.user_agent or ''),
        'message': ('说明', lambda item: item.message or ''),
        'created_at': ('时间', lambda item: item.created_at.strftime('%Y-%m-%d %H:%M:%S') if item.created_at else ''),
    }
    operation_export_field_map = {
        'id': ('ID', lambda item: item.id),
        'username': ('用户名', lambda item: item.username),
        'module': ('模块', lambda item: item.module),
        'action': ('操作', lambda item: item.action),
        'method': ('方法', lambda item: item.method),
        'path': ('路径', lambda item: item.path),
        'target_id': ('目标ID', lambda item: item.target_id or ''),
        'status_code': ('状态码', lambda item: item.status_code if item.status_code is not None else ''),
        'ip': ('IP 地址', lambda item: item.ip or ''),
        'user_agent': ('User-Agent', lambda item: item.user_agent or ''),
        'payload': ('请求体', lambda item: item.payload or ''),
        'created_at': ('时间', lambda item: item.created_at.strftime('%Y-%m-%d %H:%M:%S') if item.created_at else ''),
    }

    def has_logs_permission():
        username = session.get('username')
        if not username:
            return False
        user = Admin.query.filter_by(username=username).first()
        return bool(user and user.has_menu_code_access('system_logs'))

    def parse_datetime(raw_value, default=None):
        if raw_value is None:
            return default
        text = str(raw_value).strip()
        if not text:
            return default
        normalized = text.replace('T', ' ').replace('Z', '')
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            return None

    def parse_int(raw_value, default=0):
        try:
            return int(raw_value)
        except (TypeError, ValueError):
            return default

    def build_error_row(line, reason, row):
        return {
            'line': line,
            'reason': reason,
            'row': {k: ('' if v is None else str(v)) for k, v in (row or {}).items()}
        }

    def resolve_module_and_action(path, method):
        segments = [seg for seg in path.strip('/').split('/') if seg]
        module = 'system'
        action = {
            'POST': 'create',
            'PUT': 'update',
            'DELETE': 'delete'
        }.get(method, method.lower())

        if len(segments) >= 3 and segments[0] == 'api' and segments[1] == 'admin':
            module = segments[2]
            if 'import' in segments:
                action = 'import'
            elif 'export' in segments:
                action = 'export'
            elif 'logout' in segments:
                module = 'auth'
                action = 'logout'
            elif 'change-password' in segments:
                module = 'auth'
                action = 'change_password'
        return module, action

    @bp.after_request
    def auto_record_operation_log(response):
        """自动记录后台写操作日志"""
        try:
            if request.method not in ['POST', 'PUT', 'DELETE']:
                return response
            if not request.path.startswith('/api/admin/'):
                return response
            if request.path.startswith('/api/admin/logs'):
                return response
            if request.path == '/api/admin/login':
                return response

            username = session.get('username')
            if not username:
                return response

            user = Admin.query.filter_by(username=username).first()
            if not user:
                return response

            module, action = resolve_module_and_action(request.path, request.method)

            path_segments = [seg for seg in request.path.strip('/').split('/') if seg]
            target_id = None
            if path_segments and path_segments[-1].isdigit():
                target_id = path_segments[-1]

            item = OperationLog(
                username=username,
                user_id=user.id,
                module=module,
                action=action,
                method=request.method,
                path=request.path,
                target_id=target_id,
                payload=safe_payload(request.get_json(silent=True)),
                ip=get_client_ip(),
                user_agent=get_user_agent(),
                status_code=response.status_code
            )
            db.session.add(item)
            db.session.commit()
        except Exception:
            db.session.rollback()
        return response

    @bp.route('/api/admin/logs/login', methods=['GET'])
    @login_required
    def get_login_logs():
        """登录日志列表"""
        try:
            if not has_logs_permission():
                return jsonify({"error": "无权限访问"}), 403

            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 20, type=int)
            username = request.args.get('username', '', type=str).strip()
            status = request.args.get('status', '', type=str).strip()

            query = LoginLog.query
            if username:
                query = query.filter(LoginLog.username.ilike(f'%{username}%'))
            if status:
                query = query.filter(LoginLog.status == status)

            pagination = query.order_by(LoginLog.id.desc()).paginate(
                page=page, per_page=per_page, error_out=False)

            return jsonify({
                'items': [item.to_dict() for item in pagination.items],
                'total': pagination.total,
                'page': page,
                'per_page': per_page
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @bp.route('/api/admin/logs/operation', methods=['GET'])
    @login_required
    def get_operation_logs():
        """操作日志列表"""
        try:
            if not has_logs_permission():
                return jsonify({"error": "无权限访问"}), 403

            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 20, type=int)
            username = request.args.get('username', '', type=str).strip()
            module = request.args.get('module', '', type=str).strip()
            action = request.args.get('action', '', type=str).strip()

            query = OperationLog.query
            if username:
                query = query.filter(OperationLog.username.ilike(f'%{username}%'))
            if module:
                query = query.filter(OperationLog.module == module)
            if action:
                query = query.filter(OperationLog.action == action)

            pagination = query.order_by(OperationLog.id.desc()).paginate(
                page=page, per_page=per_page, error_out=False)

            return jsonify({
                'items': [item.to_dict() for item in pagination.items],
                'total': pagination.total,
                'page': page,
                'per_page': per_page
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @bp.route('/api/admin/logs/login/export', methods=['POST'])
    @login_required
    def export_login_logs():
        if not has_logs_permission():
            return jsonify({'error': '无权限导出日志'}), 403

        data = request.get_json() or {}
        ids = data.get('ids') or []
        fields = data.get('fields') or []
        export_mode = (data.get('export_mode') or 'selected').strip()
        filters = data.get('filters') or {}
        file_type = normalize_table_file_type(data.get('file_type'), default='csv')

        valid_fields = [field for field in fields if field in login_export_field_map]
        if not valid_fields:
            valid_fields = list(login_export_field_map.keys())

        if export_mode == 'filtered':
            query = LoginLog.query
            username = str(filters.get('username') or '').strip()
            status = str(filters.get('status') or '').strip()
            if username:
                query = query.filter(LoginLog.username.ilike(f'%{username}%'))
            if status:
                query = query.filter(LoginLog.status == status)
            items = query.order_by(LoginLog.id.asc()).all()
        else:
            if not isinstance(ids, list) or not ids:
                return jsonify({'error': '请先勾选要导出的日志数据'}), 400
            items = LoginLog.query.filter(LoginLog.id.in_(ids)).order_by(LoginLog.id.asc()).all()

        if not items:
            return jsonify({'error': '未找到可导出的日志数据'}), 404

        headers = [login_export_field_map[field][0] for field in valid_fields]
        rows = [[login_export_field_map[field][1](item) for field in valid_fields] for item in items]
        try:
            return build_table_response(headers, rows, 'login_logs_export', file_type=file_type)
        except RuntimeError as e:
            return jsonify({'error': str(e)}), 500

    @bp.route('/api/admin/logs/login/template', methods=['GET'])
    @login_required
    def download_login_logs_template():
        if not has_logs_permission():
            return jsonify({'error': '无权限下载日志模板'}), 403

        file_type = normalize_table_file_type(request.args.get('file_type'), default='csv')
        headers = ['用户名', '状态', 'IP 地址', 'User-Agent', '说明', '时间']
        rows = [['demo_user', 'success', '127.0.0.1', 'Mozilla/5.0', '导入示例', '2026-01-01 10:00:00']]
        try:
            return build_table_response(headers, rows, 'login_logs_import_template', file_type=file_type)
        except RuntimeError as e:
            return jsonify({'error': str(e)}), 500

    @bp.route('/api/admin/logs/login/import', methods=['POST'])
    @login_required
    def import_login_logs():
        if not has_logs_permission():
            return jsonify({'error': '无权限导入日志'}), 403

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

        header_map = {
            '用户名': 'username',
            '状态': 'status',
            'IP 地址': 'ip',
            'User-Agent': 'user_agent',
            '说明': 'message',
            '时间': 'created_at',
        }
        row_header_map = {}
        for header in fieldnames:
            key = (header or '').strip()
            if key in header_map:
                row_header_map[header] = header_map[key]

        if 'username' not in row_header_map.values():
            return jsonify({'error': '导入文件缺少“用户名”列'}), 400

        created = 0
        errors = []

        try:
            for line, row in rows_with_line:
                mapped = {}
                for key, value in row.items():
                    field = row_header_map.get(key)
                    if field:
                        mapped[field] = value

                username = str(mapped.get('username') or '').strip()
                if not username:
                    errors.append(build_error_row(line, '用户名不能为空', row))
                    continue

                raw_status = str(mapped.get('status') or '').strip().lower()
                status = 'success'
                if raw_status in {'failed', 'fail', '失败'}:
                    status = 'failed'

                user = Admin.query.filter_by(username=username).first()
                item = LoginLog(
                    username=username,
                    user_id=user.id if user else None,
                    status=status,
                    ip=str(mapped.get('ip') or '').strip() or None,
                    user_agent=str(mapped.get('user_agent') or '').strip() or None,
                    message=str(mapped.get('message') or '').strip() or None,
                    created_at=parse_datetime(mapped.get('created_at'), default=datetime.utcnow()) or datetime.utcnow(),
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
            return jsonify({'message': '导入成功', 'created': created, 'updated': 0})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    @bp.route('/api/admin/logs/operation/export', methods=['POST'])
    @login_required
    def export_operation_logs():
        if not has_logs_permission():
            return jsonify({'error': '无权限导出日志'}), 403

        data = request.get_json() or {}
        ids = data.get('ids') or []
        fields = data.get('fields') or []
        export_mode = (data.get('export_mode') or 'selected').strip()
        filters = data.get('filters') or {}
        file_type = normalize_table_file_type(data.get('file_type'), default='csv')

        valid_fields = [field for field in fields if field in operation_export_field_map]
        if not valid_fields:
            valid_fields = list(operation_export_field_map.keys())

        if export_mode == 'filtered':
            query = OperationLog.query
            username = str(filters.get('username') or '').strip()
            module = str(filters.get('module') or '').strip()
            action = str(filters.get('action') or '').strip()
            if username:
                query = query.filter(OperationLog.username.ilike(f'%{username}%'))
            if module:
                query = query.filter(OperationLog.module == module)
            if action:
                query = query.filter(OperationLog.action == action)
            items = query.order_by(OperationLog.id.asc()).all()
        else:
            if not isinstance(ids, list) or not ids:
                return jsonify({'error': '请先勾选要导出的日志数据'}), 400
            items = OperationLog.query.filter(OperationLog.id.in_(ids)).order_by(OperationLog.id.asc()).all()

        if not items:
            return jsonify({'error': '未找到可导出的日志数据'}), 404

        headers = [operation_export_field_map[field][0] for field in valid_fields]
        rows = [[operation_export_field_map[field][1](item) for field in valid_fields] for item in items]
        try:
            return build_table_response(headers, rows, 'operation_logs_export', file_type=file_type)
        except RuntimeError as e:
            return jsonify({'error': str(e)}), 500

    @bp.route('/api/admin/logs/operation/template', methods=['GET'])
    @login_required
    def download_operation_logs_template():
        if not has_logs_permission():
            return jsonify({'error': '无权限下载日志模板'}), 403

        file_type = normalize_table_file_type(request.args.get('file_type'), default='csv')
        headers = ['用户名', '模块', '操作', '方法', '路径', '目标ID', '状态码', 'IP 地址', 'User-Agent', '请求体', '时间']
        rows = [['demo_user', 'users', 'create', 'POST', '/api/admin/users', '', '200', '127.0.0.1', 'Mozilla/5.0', '{"username":"demo"}', '2026-01-01 10:00:00']]
        try:
            return build_table_response(headers, rows, 'operation_logs_import_template', file_type=file_type)
        except RuntimeError as e:
            return jsonify({'error': str(e)}), 500

    @bp.route('/api/admin/logs/operation/import', methods=['POST'])
    @login_required
    def import_operation_logs():
        if not has_logs_permission():
            return jsonify({'error': '无权限导入日志'}), 403

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

        header_map = {
            '用户名': 'username',
            '模块': 'module',
            '操作': 'action',
            '方法': 'method',
            '路径': 'path',
            '目标ID': 'target_id',
            '状态码': 'status_code',
            'IP 地址': 'ip',
            'User-Agent': 'user_agent',
            '请求体': 'payload',
            '时间': 'created_at',
        }
        row_header_map = {}
        for header in fieldnames:
            key = (header or '').strip()
            if key in header_map:
                row_header_map[header] = header_map[key]

        for required_field in ['username', 'module', 'action', 'method', 'path']:
            if required_field not in row_header_map.values():
                return jsonify({'error': f'导入文件缺少必填列: {required_field}'}), 400

        created = 0
        errors = []

        try:
            for line, row in rows_with_line:
                mapped = {}
                for key, value in row.items():
                    field = row_header_map.get(key)
                    if field:
                        mapped[field] = value

                username = str(mapped.get('username') or '').strip()
                module = str(mapped.get('module') or '').strip()
                action = str(mapped.get('action') or '').strip()
                method = str(mapped.get('method') or '').strip().upper()
                path = str(mapped.get('path') or '').strip()

                if not username or not module or not action or not method or not path:
                    errors.append(build_error_row(line, '必填字段不能为空', row))
                    continue

                user = Admin.query.filter_by(username=username).first()
                item = OperationLog(
                    username=username,
                    user_id=user.id if user else None,
                    module=module,
                    action=action,
                    method=method,
                    path=path,
                    target_id=str(mapped.get('target_id') or '').strip() or None,
                    payload=str(mapped.get('payload') or '').strip() or None,
                    ip=str(mapped.get('ip') or '').strip() or None,
                    user_agent=str(mapped.get('user_agent') or '').strip() or None,
                    status_code=parse_int(mapped.get('status_code'), default=200),
                    created_at=parse_datetime(mapped.get('created_at'), default=datetime.utcnow()) or datetime.utcnow(),
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
            return jsonify({'message': '导入成功', 'created': created, 'updated': 0})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
