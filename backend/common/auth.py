# -*- coding: utf-8 -*-
"""认证与权限装饰器"""

from functools import wraps
from flask import jsonify, redirect, request, session, url_for


def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            if request.path.startswith('/api/'):
                return jsonify({'error': '未授权访问', 'redirect': '/admin/login'}), 401
            return redirect(url_for('admin.login_page'))
        return f(*args, **kwargs)

    return decorated_function


def menu_permission_required(menu_code):
    """菜单权限验证装饰器（基于菜单 code）"""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get('logged_in'):
                if request.path.startswith('/api/'):
                    return jsonify({'error': '未登录'}), 401
                return redirect(url_for('admin.login_page'))

            username = session.get('username')
            if not username:
                if request.path.startswith('/api/'):
                    return jsonify({'error': '会话异常'}), 401
                return redirect(url_for('admin.login_page'))

            from flask import current_app

            db = current_app.extensions['sqlalchemy']
            models = db.Model.registry._class_registry

            Admin = None
            for _, model in models.items():
                if hasattr(model, '__tablename__') and model.__tablename__ == 'admin_users':
                    Admin = model
                    break

            if not Admin:
                return jsonify({'error': '系统错误'}), 500

            user = Admin.query.filter_by(username=username).first()
            if not user:
                if request.path.startswith('/api/'):
                    return jsonify({'error': '用户不存在'}), 404
                return redirect(url_for('admin.login_page'))

            if not user.has_menu_code_access(menu_code):
                if request.path.startswith('/api/'):
                    return jsonify({'error': f'缺少权限: {menu_code}'}), 403
                return jsonify({'error': '无权限'}), 403

            return f(*args, **kwargs)

        return decorated_function

    return decorator
