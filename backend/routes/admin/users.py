# -*- coding: utf-8 -*-
"""
后台管理 - 用户管理模块
"""
from flask import jsonify, request, session
from backend.utils import login_required
from . import bp


def init_users_routes(db, models):
    """初始化用户管理相关路由"""
    Admin = models['Admin']
    Role = models['Role']

    def has_permission(code):
        username = session.get('username')
        if not username:
            return False
        user = Admin.query.filter_by(username=username).first()
        return bool(user and user.has_menu_code_access(code))

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
