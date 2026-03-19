# -*- coding: utf-8 -*-
"""
后台管理 - 认证模块
登录、登出、修改密码
"""
from flask import jsonify, request, session, redirect, url_for
from backend.utils import login_required
from backend.log_utils import get_client_ip, get_user_agent
from . import bp


def init_auth_routes(db, models):
    """初始化认证相关路由"""
    Admin = models['Admin']
    LoginLog = models['LoginLog']
    OperationLog = models['OperationLog']

    @bp.route('/admin/login')
    def login_page():
        """登录页面（SPA入口，重定向到前端）"""
        if session.get('logged_in'):
            return redirect('/admin')
        return redirect('/')

    @bp.route('/api/admin/login', methods=['POST'])
    def login():
        """登录接口"""
        data = request.get_json() or {}
        username = data.get('username')
        password = data.get('password')

        user = Admin.query.filter_by(username=username).first()

        if user and user.check_password(password):
            session['logged_in'] = True
            session['username'] = username
            try:
                db.session.add(LoginLog(
                    username=username,
                    user_id=user.id,
                    status='success',
                    ip=get_client_ip(),
                    user_agent=get_user_agent(),
                    message='登录成功'
                ))
                db.session.commit()
            except Exception:
                db.session.rollback()
            return jsonify({
                "message": "登录成功",
                "user": user.to_dict()
            })
        else:
            try:
                db.session.add(LoginLog(
                    username=username or '',
                    user_id=user.id if user else None,
                    status='failed',
                    ip=get_client_ip(),
                    user_agent=get_user_agent(),
                    message='用户名或密码错误'
                ))
                db.session.commit()
            except Exception:
                db.session.rollback()
            return jsonify({"error": "用户名或密码错误"}), 401

    @bp.route('/api/admin/logout', methods=['POST'])
    def logout():
        """登出接口"""
        username = session.get('username') or ''
        user = Admin.query.filter_by(username=username).first() if username else None
        try:
            db.session.add(OperationLog(
                username=username or 'unknown',
                user_id=user.id if user else None,
                module='auth',
                action='logout',
                method='POST',
                path='/api/admin/logout',
                target_id=None,
                payload=None,
                ip=get_client_ip(),
                user_agent=get_user_agent(),
                status_code=200
            ))
            db.session.commit()
        except Exception:
            db.session.rollback()
        session.clear()
        return jsonify({"message": "已退出登录"})

    @bp.route('/api/admin/change-password', methods=['POST'])
    @login_required
    def change_password():
        """修改密码接口"""
        try:
            data = request.get_json()
            old_password = data.get('old_password')
            new_password = data.get('new_password')

            if not old_password or not new_password:
                return jsonify({"error": "请填写完整信息"}), 400

            if len(new_password) < 6:
                return jsonify({"error": "新密码长度至少6位"}), 400

            username = session.get('username')
            admin = Admin.query.filter_by(username=username).first()

            if not admin:
                return jsonify({"error": "用户不存在"}), 404

            if not admin.check_password(old_password):
                return jsonify({"error": "旧密码错误"}), 401

            admin.set_password(new_password)
            db.session.commit()

            return jsonify({"message": "密码修改成功"})

        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    @bp.route('/api/admin/me', methods=['GET'])
    @login_required
    def get_current_user():
        """获取当前登录用户信息"""
        username = session.get('username')
        user = Admin.query.filter_by(username=username).first()
        if not user:
            return jsonify({'error': '用户不存在'}), 404
        return jsonify({'user': user.to_dict()})
