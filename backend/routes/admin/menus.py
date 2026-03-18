# -*- coding: utf-8 -*-
"""
后台管理 - 菜单管理模块
"""
from flask import jsonify, request, session
from backend.utils import login_required, menu_permission_required
from . import bp


def init_menus_routes(db, models):
    """初始化菜单管理相关路由"""
    Menu = models['Menu']

    @bp.route('/api/admin/menus', methods=['GET', 'POST'])
    @login_required
    @menu_permission_required('system_menus_add')
    def manage_menus():
        if request.method == 'GET':
            format_type = request.args.get('format', 'tree')
            search = request.args.get('search', '').strip()

            query = Menu.query
            if search:
                query = query.filter(db.or_(
                    Menu.name.ilike(f'%{search}%'),
                    Menu.code.ilike(f'%{search}%')
                ))

            if format_type == 'tree':
                root_menus = query.filter(Menu.parent_id.is_(None)).order_by(Menu.sort_order).all()
                return jsonify([menu.to_dict(include_children=True) for menu in root_menus])
            else:
                menus = query.order_by(Menu.sort_order).all()
                return jsonify([menu.to_dict(include_children=False) for menu in menus])

        data = request.json
        if not data.get('name') or not data.get('code'):
            return jsonify({'error': '菜单名称和编码不能为空'}), 400

        if Menu.query.filter_by(code=data['code']).first():
            return jsonify({'error': f'菜单编码 {data["code"]} 已存在'}), 400

        new_menu = Menu(
            name=data['name'],
            code=data['code'],
            icon=data.get('icon'),
            path=data.get('path'),
            component=data.get('component'),
            parent_id=data.get('parent_id'),
            sort_order=data.get('sort_order', 0),
            is_visible=data.get('is_visible', True),
            is_active=data.get('is_active', True),
            menu_type=data.get('menu_type', 'menu'),
            description=data.get('description')
        )

        db.session.add(new_menu)
        try:
            db.session.commit()
            return jsonify(new_menu.to_dict()), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    @bp.route('/api/admin/menus/<int:menu_id>', methods=['GET', 'PUT', 'DELETE'])
    @login_required
    def manage_menu(menu_id):
        menu = Menu.query.get_or_404(menu_id)

        if request.method == 'GET':
            return jsonify(menu.to_dict(include_children=True))

        if request.method == 'PUT':
            username = session.get('username')
            Admin = models['Admin']
            current_user = Admin.query.filter_by(username=username).first()
            if not current_user or not current_user.has_menu_code_access('system_menus_edit'):
                return jsonify({'error': '无权限编辑菜单'}), 403

            data = request.json

            if data.get('code') and data['code'] != menu.code:
                if Menu.query.filter_by(code=data['code']).first():
                    return jsonify({'error': f'菜单编码 {data["code"]} 已存在'}), 400

            for field in ['name', 'code', 'icon', 'path', 'component', 'parent_id',
                          'sort_order', 'is_visible', 'is_active', 'menu_type', 'description']:
                if field in data:
                    setattr(menu, field, data[field])

            try:
                db.session.commit()
                return jsonify(menu.to_dict())
            except Exception as e:
                db.session.rollback()
                return jsonify({'error': str(e)}), 500

        if request.method == 'DELETE':
            username = session.get('username')
            Admin = models['Admin']
            current_user = Admin.query.filter_by(username=username).first()
            if not current_user or not current_user.has_menu_code_access('system_menus_delete'):
                return jsonify({'error': '无权限删除菜单'}), 403

            if menu.children.count() > 0:
                return jsonify({'error': '该菜单下还有子菜单，无法删除'}), 400

            try:
                db.session.delete(menu)
                db.session.commit()
                return jsonify({'message': '删除成功'})
            except Exception as e:
                db.session.rollback()
                return jsonify({'error': str(e)}), 500

    @bp.route('/api/admin/my-menus', methods=['GET'])
    @login_required
    def get_my_menus():
        """获取当前用户的菜单权限（前端动态路由用）"""
        username = session.get('username')
        Admin = models['Admin']
        user = Admin.query.filter_by(username=username).first()

        if not user:
            return jsonify([])

        menu_ids = set()
        for role in user.roles:
            for menu in role.menus:
                if menu.is_active and menu.is_visible:
                    menu_ids.add(menu.id)
                    current = menu.parent
                    while current:
                        menu_ids.add(current.id)
                        current = current.parent

        menus = Menu.query.filter(Menu.id.in_(menu_ids)).order_by(Menu.sort_order).all()

        menu_dict = {m.id: m.to_dict(include_children=False) for m in menus}
        for menu in menus:
            if menu.parent_id and menu.parent_id in menu_dict:
                if 'children' not in menu_dict[menu.parent_id]:
                    menu_dict[menu.parent_id]['children'] = []
                menu_dict[menu.parent_id]['children'].append(menu_dict[menu.id])

        root_menus = [menu_dict[m.id] for m in menus if not m.parent_id]
        return jsonify(root_menus)
