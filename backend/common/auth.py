# -*- coding: utf-8 -*-
"""认证与权限装饰器"""

from functools import wraps
from flask import current_app, jsonify, redirect, request, session, url_for


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


def _get_admin_model():
    db = current_app.extensions.get('sqlalchemy')
    if not db:
        return None

    models = db.Model.registry._class_registry
    for _, model in models.items():
        if hasattr(model, '__tablename__') and model.__tablename__ == 'admin_users':
            return model
    return None


def get_current_admin_user():
    username = session.get('username')
    if not username:
        return None

    admin_model = _get_admin_model()
    if not admin_model:
        return None
    return admin_model.query.filter_by(username=username).first()


def has_menu_permission(menu_code):
    user = get_current_admin_user()
    return bool(user and user.has_menu_code_access(menu_code))


def has_any_menu_permission(*menu_codes):
    return any(has_menu_permission(code) for code in menu_codes if code)


def menu_permission_required(menu_code):
    """菜单权限验证装饰器（基于菜单 code）"""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get('logged_in'):
                if request.path.startswith('/api/'):
                    return jsonify({'error': '未登录'}), 401
                return redirect(url_for('admin.login_page'))

            if not session.get('username'):
                if request.path.startswith('/api/'):
                    return jsonify({'error': '会话异常'}), 401
                return redirect(url_for('admin.login_page'))

            user = get_current_admin_user()
            if user is None and _get_admin_model() is None:
                return jsonify({'error': '系统错误'}), 500

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
