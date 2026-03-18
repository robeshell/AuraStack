"""
工具函数模块
"""
import json
import math
import gzip
from io import BytesIO
from functools import wraps
from flask import request, Response, jsonify, session, redirect, url_for


class CustomJSONEncoder(json.JSONEncoder):
    """自定义JSON编码器，处理NaN值"""

    def default(self, obj):
        if isinstance(obj, float) and math.isnan(obj):
            return None
        try:
            return super().default(obj)
        except TypeError:
            return str(obj)


def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            if request.path.startswith('/api/'):
                return jsonify({"error": "未授权访问", "redirect": "/admin/login"}), 401
            return redirect(url_for('admin.login_page'))
        return f(*args, **kwargs)
    return decorated_function


def menu_permission_required(menu_code):
    """菜单权限验证装饰器（基于菜单code）"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get('logged_in'):
                if request.path.startswith('/api/'):
                    return jsonify({"error": "未登录"}), 401
                return redirect(url_for('admin.login_page'))

            username = session.get('username')
            if not username:
                if request.path.startswith('/api/'):
                    return jsonify({"error": "会话异常"}), 401
                return redirect(url_for('admin.login_page'))

            from flask import current_app
            db = current_app.extensions['sqlalchemy']
            models = db.Model.registry._class_registry

            Admin = None
            for name, model in models.items():
                if hasattr(model, '__tablename__') and model.__tablename__ == 'admin_users':
                    Admin = model
                    break

            if not Admin:
                return jsonify({"error": "系统错误"}), 500

            user = Admin.query.filter_by(username=username).first()
            if not user:
                if request.path.startswith('/api/'):
                    return jsonify({"error": "用户不存在"}), 404
                return redirect(url_for('admin.login_page'))

            if not user.has_menu_code_access(menu_code):
                if request.path.startswith('/api/'):
                    return jsonify({"error": f"缺少权限: {menu_code}"}), 403
                return jsonify({"error": "无权限"}), 403

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def gzip_response(f):
    """压缩响应装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        accept_encoding = request.headers.get('Accept-Encoding', '')
        response = f(*args, **kwargs)

        if not isinstance(response, Response):
            from flask import current_app
            response = current_app.make_response(response)

        if 'gzip' not in accept_encoding.lower():
            return response

        data = response.get_data()
        if len(data) < 1024:
            return response

        gzip_buffer = BytesIO()
        with gzip.GzipFile(mode='wb', fileobj=gzip_buffer, compresslevel=6) as gzip_file:
            gzip_file.write(data)

        gzip_data = gzip_buffer.getvalue()
        response.set_data(gzip_data)
        response.headers['Content-Encoding'] = 'gzip'
        response.headers['Content-Length'] = len(gzip_data)
        response.headers['Vary'] = 'Accept-Encoding'

        return response
    return decorated_function
