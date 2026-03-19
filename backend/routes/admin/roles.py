# -*- coding: utf-8 -*-
"""
后台管理 - 角色管理模块
"""
from flask import jsonify, request, session
from backend.utils import login_required
from . import bp


def init_roles_routes(db, models):
    """初始化角色管理相关路由"""
    Role = models['Role']
    Menu = models['Menu']
    Admin = models['Admin']

    def has_permission(code):
        username = session.get('username')
        if not username:
            return False
        user = Admin.query.filter_by(username=username).first()
        return bool(user and user.has_menu_code_access(code))

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
