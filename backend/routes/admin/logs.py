# -*- coding: utf-8 -*-
"""
后台管理 - 日志管理模块
登录日志、操作日志（含自动记录）
"""
from flask import jsonify, request, session
from backend.utils import login_required
from backend.log_utils import get_client_ip, get_user_agent, safe_payload
from . import bp


def init_logs_routes(db, models):
    """初始化日志相关路由"""
    Admin = models['Admin']
    LoginLog = models['LoginLog']
    OperationLog = models['OperationLog']

    def has_logs_permission():
        username = session.get('username')
        if not username:
            return False
        user = Admin.query.filter_by(username=username).first()
        return bool(user and user.has_menu_code_access('system_logs'))

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
            if len(segments) >= 4:
                tail = segments[3]
                if tail == 'import':
                    action = 'import'
                elif tail == 'export':
                    action = 'export'
                elif tail == 'logout':
                    module = 'auth'
                    action = 'logout'
                elif tail == 'change-password':
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
