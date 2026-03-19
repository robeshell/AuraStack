# -*- coding: utf-8 -*-
"""
后台管理 - 菜单管理模块
"""
from flask import jsonify, request, session
from backend.utils import login_required
from backend.common.tabular import build_table_response, normalize_table_file_type, read_table_file
from . import bp


def init_menus_routes(db, models):
    """初始化菜单管理相关路由"""
    Menu = models['Menu']
    Admin = models['Admin']
    export_field_map = {
        'id': ('ID', lambda item: item.id),
        'name': ('菜单名称', lambda item: item.name),
        'code': ('菜单编码', lambda item: item.code),
        'menu_type': ('类型', lambda item: item.menu_type),
        'path': ('路径', lambda item: item.path or ''),
        'component': ('组件', lambda item: item.component or ''),
        'icon': ('图标', lambda item: item.icon or ''),
        'parent_code': ('父级编码', lambda item: item.parent.code if item.parent else ''),
        'sort_order': ('排序', lambda item: item.sort_order if item.sort_order is not None else 0),
        'is_visible': ('是否显示', lambda item: '是' if item.is_visible else '否'),
        'is_active': ('是否启用', lambda item: '是' if item.is_active else '否'),
        'description': ('描述', lambda item: item.description or ''),
    }
    import_header_map = {
        '菜单名称': 'name',
        '菜单编码': 'code',
        '类型': 'menu_type',
        '路径': 'path',
        '组件': 'component',
        '图标': 'icon',
        '父级编码': 'parent_code',
        '排序': 'sort_order',
        '是否显示': 'is_visible',
        '是否启用': 'is_active',
        '描述': 'description',
    }

    def sync_menu_id_sequence():
        """修复 PostgreSQL 自增序列与当前最大 ID 不一致的问题"""
        if db.engine.dialect.name != 'postgresql':
            return
        db.session.execute(db.text("""
            SELECT setval(
                pg_get_serial_sequence('menus', 'id'),
                COALESCE((SELECT MAX(id) FROM menus), 0) + 1,
                false
            )
        """))

    def build_menu_entity(data):
        return Menu(
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

    def has_permission(code):
        username = session.get('username')
        if not username:
            return False
        user = Admin.query.filter_by(username=username).first()
        return bool(user and user.has_menu_code_access(code))

    def parse_bool(value, default=None):
        if value is None or value == '':
            return default
        if isinstance(value, bool):
            return value
        raw = str(value).strip().lower()
        if raw in {'1', 'true', 'yes', 'on', '是', '启用'}:
            return True
        if raw in {'0', 'false', 'no', 'off', '否', '停用'}:
            return False
        return default

    def parse_int(value, default=0):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def build_error_row(line, reason, row):
        return {
            'line': line,
            'reason': reason,
            'row': {k: ('' if v is None else str(v)) for k, v in (row or {}).items()}
        }

    @bp.route('/api/admin/menus', methods=['GET', 'POST'])
    @login_required
    def manage_menus():
        if request.method == 'GET':
            if not has_permission('system_menus'):
                return jsonify({'error': '无权限查看菜单列表'}), 403

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

        if not has_permission('system_menus_add'):
            return jsonify({'error': '无权限新增菜单'}), 403

        data = request.json
        if not data.get('name') or not data.get('code'):
            return jsonify({'error': '菜单名称和编码不能为空'}), 400

        if Menu.query.filter_by(code=data['code']).first():
            return jsonify({'error': f'菜单编码 {data["code"]} 已存在'}), 400

        # 兼容历史种子数据导致的序列漂移，先尝试同步序列
        try:
            sync_menu_id_sequence()
            new_menu = build_menu_entity(data)
            db.session.add(new_menu)
            db.session.commit()
            return jsonify(new_menu.to_dict()), 201
        except Exception as e:
            db.session.rollback()
            # 极端并发情况下兜底重试一次
            if 'menus_pkey' in str(e):
                try:
                    sync_menu_id_sequence()
                    new_menu = build_menu_entity(data)
                    db.session.add(new_menu)
                    db.session.commit()
                    return jsonify(new_menu.to_dict()), 201
                except Exception as retry_error:
                    db.session.rollback()
                    return jsonify({'error': str(retry_error)}), 500
            return jsonify({'error': str(e)}), 500

    @bp.route('/api/admin/menus/<int:menu_id>', methods=['GET', 'PUT', 'DELETE'])
    @login_required
    def manage_menu(menu_id):
        menu = Menu.query.get_or_404(menu_id)

        if request.method == 'GET':
            return jsonify(menu.to_dict(include_children=True))

        if request.method == 'PUT':
            username = session.get('username')
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

    @bp.route('/api/admin/menus/export', methods=['POST'])
    @login_required
    def export_menus():
        if not has_permission('system_menus'):
            return jsonify({'error': '无权限导出菜单'}), 403

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
            query = Menu.query
            search = str(filters.get('search') or '').strip()
            if search:
                query = query.filter(db.or_(
                    Menu.name.ilike(f'%{search}%'),
                    Menu.code.ilike(f'%{search}%')
                ))
            items = query.order_by(Menu.sort_order.asc(), Menu.id.asc()).all()
        else:
            if not isinstance(ids, list) or not ids:
                return jsonify({'error': '请先勾选要导出的菜单数据'}), 400
            items = Menu.query.filter(Menu.id.in_(ids)).order_by(Menu.sort_order.asc(), Menu.id.asc()).all()

        if not items:
            return jsonify({'error': '未找到可导出的菜单数据'}), 404

        headers = [export_field_map[field][0] for field in valid_fields]
        rows = [[export_field_map[field][1](item) for field in valid_fields] for item in items]
        try:
            return build_table_response(headers, rows, 'menus_export', file_type=file_type)
        except RuntimeError as e:
            return jsonify({'error': str(e)}), 500

    @bp.route('/api/admin/menus/template', methods=['GET'])
    @login_required
    def download_menus_template():
        if not has_permission('system_menus'):
            return jsonify({'error': '无权限下载菜单导入模板'}), 403

        file_type = normalize_table_file_type(request.args.get('file_type'), default='csv')
        headers = ['菜单名称', '菜单编码', '类型', '路径', '组件', '图标', '父级编码', '排序', '是否显示', '是否启用', '描述']
        rows = [['示例菜单', 'demo_menu', 'menu', '/demo/menu', 'DemoMenu', 'IconApps', '', 99, '是', '是', '示例描述']]
        try:
            return build_table_response(headers, rows, 'menus_import_template', file_type=file_type)
        except RuntimeError as e:
            return jsonify({'error': str(e)}), 500

    @bp.route('/api/admin/menus/import', methods=['POST'])
    @login_required
    def import_menus():
        if not has_permission('system_menus_edit'):
            return jsonify({'error': '无权限导入菜单'}), 403

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

        if 'name' not in row_header_map.values() or 'code' not in row_header_map.values():
            return jsonify({'error': '导入文件缺少“菜单名称/菜单编码”列'}), 400

        created = 0
        updated = 0
        pending_parent = []
        menu_cache = {menu.code: menu for menu in Menu.query.all()}
        errors = []

        try:
            for line, row in rows_with_line:
                mapped = {}
                for key, value in row.items():
                    field = row_header_map.get(key)
                    if field:
                        mapped[field] = value

                name = str(mapped.get('name') or '').strip()
                code = str(mapped.get('code') or '').strip()
                if not name or not code:
                    errors.append(build_error_row(line, '菜单名称和编码不能为空', row))
                    continue

                item = menu_cache.get(code)
                if item:
                    updated += 1
                else:
                    item = Menu(code=code)
                    db.session.add(item)
                    menu_cache[code] = item
                    created += 1

                menu_type = str(mapped.get('menu_type') or item.menu_type or 'menu').strip() or 'menu'
                if menu_type not in {'directory', 'menu', 'button'}:
                    errors.append(build_error_row(line, f'类型无效: {menu_type}', row))
                    continue

                item.name = name
                item.menu_type = menu_type
                item.path = str(mapped.get('path') or '').strip() or None
                item.component = str(mapped.get('component') or '').strip() or None
                item.icon = str(mapped.get('icon') or '').strip() or None
                item.sort_order = parse_int(mapped.get('sort_order'), default=item.sort_order or 0)
                item.is_visible = parse_bool(mapped.get('is_visible'), default=item.is_visible if item.is_visible is not None else True)
                item.is_active = parse_bool(mapped.get('is_active'), default=item.is_active if item.is_active is not None else True)
                item.description = str(mapped.get('description') or '').strip() or None

                parent_code = str(mapped.get('parent_code') or '').strip()
                pending_parent.append((item, parent_code, line, row))

            db.session.flush()

            for item, parent_code, source_line, source_row in pending_parent:
                if not parent_code:
                    item.parent_id = None
                    continue
                parent = menu_cache.get(parent_code)
                if not parent:
                    errors.append(build_error_row(source_line, f'父级编码不存在: {parent_code}', source_row))
                    continue
                if parent.code == item.code:
                    errors.append(build_error_row(source_line, '父级编码不能等于自身编码', source_row))
                    continue
                item.parent_id = parent.id

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
