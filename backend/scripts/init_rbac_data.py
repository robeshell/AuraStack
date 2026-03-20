#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RBAC系统数据初始化脚本
初始化：菜单、角色、管理员账号及权限关联
"""
import sys
import os
import argparse

# 添加项目根目录到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)

print("正在导入模块...")
try:
    from app import app, db, models
    print("模块导入成功")
except Exception as e:
    print(f"模块导入失败: {e}")
    sys.exit(1)


def sync_postgres_id_sequence(table_name):
    """同步 PostgreSQL 表的主键序列到当前最大 id"""
    if db.engine.dialect.name != 'postgresql':
        return
    db.session.execute(db.text(f"""
        SELECT setval(
            pg_get_serial_sequence('{table_name}', 'id'),
            COALESCE((SELECT MAX(id) FROM {table_name}), 0) + 1,
            false
        )
    """))
    db.session.commit()
    print(f"  已同步序列: {table_name}.id")


def clear_rbac_data():
    """清空RBAC相关数据"""
    Admin = models['Admin']
    Role = models['Role']
    Menu = models['Menu']

    print("清空现有RBAC数据...")
    try:
        db.session.execute(db.text('DELETE FROM user_roles'))
        print("  清空用户-角色关联")

        db.session.execute(db.text('DELETE FROM role_menus'))
        print("  清空角色-菜单关联")

        Admin.query.delete()
        print("  清空管理员账号")

        Role.query.delete()
        print("  清空角色")

        Menu.query.delete()
        print("  清空菜单")

        db.session.commit()
        print("数据清空完成\n")
    except Exception as e:
        db.session.rollback()
        print(f"  清空失败: {e}")
        raise


def migrate_component_center_menu_code(Menu):
    """将旧菜单编码 data_management 迁移为 component_center，避免重命名后重复菜单"""
    legacy_menu = Menu.query.filter_by(code='data_management').first()
    current_menu = Menu.query.filter_by(code='component_center').first()

    if not legacy_menu:
        return

    if current_menu and current_menu.id != legacy_menu.id:
        # 把新编码菜单下可能挂载的子菜单迁回旧菜单，保持层级稳定
        Menu.query.filter_by(parent_id=current_menu.id).update({'parent_id': legacy_menu.id})

        # 迁移角色-菜单关系，避免删除重复菜单后丢权限
        db.session.execute(
            db.text(
                """
                INSERT INTO role_menus (role_id, menu_id)
                SELECT DISTINCT rm.role_id, :legacy_menu_id
                FROM role_menus rm
                WHERE rm.menu_id = :current_menu_id
                AND NOT EXISTS (
                    SELECT 1
                    FROM role_menus x
                    WHERE x.role_id = rm.role_id
                      AND x.menu_id = :legacy_menu_id
                )
                """
            ),
            {'legacy_menu_id': legacy_menu.id, 'current_menu_id': current_menu.id},
        )
        db.session.execute(
            db.text("DELETE FROM role_menus WHERE menu_id = :current_menu_id"),
            {'current_menu_id': current_menu.id},
        )
        # 先把重复记录改成临时编码，避免唯一键冲突，再删除
        current_menu.code = f'component_center_legacy_{current_menu.id}'
        db.session.flush()
        db.session.delete(current_menu)
        print("  已合并重复菜单: [data_management] + [component_center]")

    legacy_menu.code = 'component_center'
    legacy_menu.name = '组件示例中心'
    print("  菜单编码迁移: [data_management] -> [component_center]")
    db.session.flush()


def migrate_list_page_menu_codes(Menu):
    """将旧的 query_management 菜单/按钮编码迁移为 list_page，避免重复菜单"""
    code_mappings = [
        ('system_query_management', 'system_list_page'),
        ('system_query_management_add', 'system_list_page_add'),
        ('system_query_management_edit', 'system_list_page_edit'),
        ('system_query_management_delete', 'system_list_page_delete'),
    ]

    for old_code, new_code in code_mappings:
        legacy_menu = Menu.query.filter_by(code=old_code).first()
        current_menu = Menu.query.filter_by(code=new_code).first()

        if not legacy_menu:
            continue

        if current_menu and current_menu.id != legacy_menu.id:
            Menu.query.filter_by(parent_id=legacy_menu.id).update({'parent_id': current_menu.id})
            db.session.execute(
                db.text(
                    """
                    INSERT INTO role_menus (role_id, menu_id)
                    SELECT DISTINCT rm.role_id, :current_menu_id
                    FROM role_menus rm
                    WHERE rm.menu_id = :legacy_menu_id
                    AND NOT EXISTS (
                        SELECT 1
                        FROM role_menus x
                        WHERE x.role_id = rm.role_id
                          AND x.menu_id = :current_menu_id
                    )
                    """
                ),
                {'legacy_menu_id': legacy_menu.id, 'current_menu_id': current_menu.id},
            )
            db.session.execute(
                db.text("DELETE FROM role_menus WHERE menu_id = :legacy_menu_id"),
                {'legacy_menu_id': legacy_menu.id},
            )
            legacy_menu.code = f'legacy_{old_code}_{legacy_menu.id}'
            db.session.flush()
            db.session.delete(legacy_menu)
            print(f"  已合并重复菜单编码: [{old_code}] + [{new_code}]")
            continue

        legacy_menu.code = new_code
        print(f"  菜单编码迁移: [{old_code}] -> [{new_code}]")
        db.session.flush()


def init_menus():
    """初始化菜单数据"""
    Menu = models['Menu']

    migrate_component_center_menu_code(Menu)
    migrate_list_page_menu_codes(Menu)

    menus_data = [
        # 一级菜单
        {'id': 1, 'name': '首页', 'code': 'dashboard', 'icon': 'IconHome', 'path': '/dashboard', 'component': 'admin/dashboard',
            'parent_id': None, 'sort_order': 1, 'menu_type': 'menu', 'is_visible': True, 'is_active': True},
        {'id': 2, 'name': '系统管理', 'code': 'system', 'icon': 'IconSetting', 'path': None, 'component': None,
            'parent_id': None, 'sort_order': 99, 'menu_type': 'menu', 'is_visible': True, 'is_active': True},
        {'id': 3, 'name': '组件示例中心', 'code': 'component_center', 'icon': 'IconApps', 'path': None, 'component': None,
            'parent_id': None, 'sort_order': 2, 'menu_type': 'menu', 'is_visible': True, 'is_active': True},

        # 系统管理子菜单
        {'id': 21, 'name': '用户管理', 'code': 'system_users', 'icon': 'IconUser', 'path': '/system/users', 'component': 'admin/users',
            'parent_id': 2, 'sort_order': 1, 'menu_type': 'menu', 'is_visible': True, 'is_active': True},
        {'id': 22, 'name': '角色权限', 'code': 'system_roles', 'icon': 'IconIdCard', 'path': '/system/roles', 'component': 'admin/roles',
            'parent_id': 2, 'sort_order': 2, 'menu_type': 'menu', 'is_visible': True, 'is_active': True},
        {'id': 23, 'name': '菜单管理', 'code': 'system_menus', 'icon': 'IconApps', 'path': '/system/menus', 'component': 'admin/menus',
            'parent_id': 2, 'sort_order': 3, 'menu_type': 'menu', 'is_visible': True, 'is_active': True},
        {'id': 24, 'name': '日志管理', 'code': 'system_logs', 'icon': 'IconFile', 'path': '/system/logs', 'component': 'admin/logs',
            'parent_id': 2, 'sort_order': 4, 'menu_type': 'menu', 'is_visible': True, 'is_active': True},
        {'id': 25, 'name': '数据字典', 'code': 'system_dicts', 'icon': 'IconList', 'path': '/system/dicts', 'component': 'admin/dicts',
            'parent_id': 2, 'sort_order': 5, 'menu_type': 'menu', 'is_visible': True, 'is_active': True},

        # ── 组件示例中心：分类父节点 ──────────────────────────────────────
        {'id': 40, 'name': '管理系统', 'code': 'cc_admin', 'icon': 'IconDesktop', 'path': None, 'component': None,
            'parent_id': 3, 'sort_order': 1, 'menu_type': 'menu', 'is_visible': True, 'is_active': True},
        {'id': 41, 'name': '数据可视化', 'code': 'cc_dataviz', 'icon': 'IconPieChartStroked', 'path': None, 'component': None,
            'parent_id': 3, 'sort_order': 2, 'menu_type': 'menu', 'is_visible': True, 'is_active': True},
        {'id': 42, 'name': '3D / 创意', 'code': 'cc_3d', 'icon': 'IconBox', 'path': None, 'component': None,
            'parent_id': 3, 'sort_order': 3, 'menu_type': 'menu', 'is_visible': True, 'is_active': True},
        {'id': 44, 'name': 'AI 应用', 'code': 'cc_ai', 'icon': 'IconSend', 'path': None, 'component': None,
            'parent_id': 3, 'sort_order': 4, 'menu_type': 'menu', 'is_visible': True, 'is_active': True},
        {'id': 45, 'name': '编辑器 / 低代码', 'code': 'cc_editor', 'icon': 'IconEdit2', 'path': None, 'component': None,
            'parent_id': 3, 'sort_order': 5, 'menu_type': 'menu', 'is_visible': True, 'is_active': True},
        {'id': 46, 'name': '工程 / 工具类', 'code': 'cc_devtools', 'icon': 'IconLayers', 'path': None, 'component': None,
            'parent_id': 3, 'sort_order': 6, 'menu_type': 'menu', 'is_visible': True, 'is_active': True},

        # ── 管理系统 (parent_id=40) ───────────────────────────────────
        {'id': 31, 'name': '列表页', 'code': 'system_list_page', 'icon': 'IconFile', 'path': '/component-center/list-page', 'component': 'component_center/list_page',
            'parent_id': 40, 'sort_order': 1, 'menu_type': 'menu', 'is_visible': True, 'is_active': True},
        {'id': 33, 'name': '统计列表页', 'code': 'system_stats_list_page', 'icon': 'IconBarChart', 'path': '/component-center/stats-list-page', 'component': 'component_center/stats_list_page',
            'parent_id': 40, 'sort_order': 2, 'menu_type': 'menu', 'is_visible': True, 'is_active': True},
        {'id': 34, 'name': '卡片列表页', 'code': 'system_card_list_page', 'icon': 'IconGridSquare', 'path': '/component-center/card-list-page', 'component': 'component_center/card_list_page',
            'parent_id': 40, 'sort_order': 3, 'menu_type': 'menu', 'is_visible': True, 'is_active': True},
        {'id': 35, 'name': '树形列表页', 'code': 'system_tree_list_page', 'icon': 'IconBranch', 'path': '/component-center/tree-list-page', 'component': 'component_center/tree_list_page',
            'parent_id': 40, 'sort_order': 4, 'menu_type': 'menu', 'is_visible': True, 'is_active': True},
        {'id': 36, 'name': '动态表单页', 'code': 'system_dynamic_form_page', 'icon': 'IconCode', 'path': '/component-center/dynamic-form-page', 'component': 'component_center/dynamic_form_page',
            'parent_id': 40, 'sort_order': 5, 'menu_type': 'menu', 'is_visible': True, 'is_active': True},

        # ── 管理系统页面 (parent_id=40，新增) ────────────────────────────
        {'id': 401, 'name': '拖拽看板页', 'code': 'cc_admin_kanban_page', 'icon': 'IconKanban', 'path': '/component-center/admin/kanban', 'component': 'component_center/admin/kanban_page',
            'parent_id': 40, 'sort_order': 6, 'menu_type': 'menu', 'is_visible': True, 'is_active': True},
        {'id': 402, 'name': '详情标签页', 'code': 'cc_admin_detail_tabs_page', 'icon': 'IconIdCard', 'path': '/component-center/admin/detail-tabs', 'component': 'component_center/admin/detail_tabs_page',
            'parent_id': 40, 'sort_order': 7, 'menu_type': 'menu', 'is_visible': True, 'is_active': True},
        {'id': 403, 'name': '甘特图页', 'code': 'cc_admin_gantt_page', 'icon': 'IconHistogram', 'path': '/component-center/admin/gantt', 'component': 'component_center/admin/gantt_page',
            'parent_id': 40, 'sort_order': 8, 'menu_type': 'menu', 'is_visible': True, 'is_active': True},

        # ── 数据可视化 (parent_id=41) ─────────────────────────────────
        {'id': 37, 'name': '数据大屏', 'code': 'system_dashboard_page', 'icon': 'IconHistogram', 'path': '/component-center/dashboard-page', 'component': 'component_center/dashboard_page',
            'parent_id': 41, 'sort_order': 1, 'menu_type': 'menu', 'is_visible': True, 'is_active': True},
        {'id': 32, 'name': '定时任务', 'code': 'system_scheduled_tasks', 'icon': 'IconSetting', 'path': '/system/scheduled-tasks', 'component': 'admin/scheduled_tasks',
            'parent_id': 2, 'sort_order': 6, 'menu_type': 'menu', 'is_visible': True, 'is_active': True},

        # 用户管理按钮权限
        {'id': 211, 'name': '新增用户', 'code': 'system_users_add', 'icon': None, 'path': None, 'component': None,
            'parent_id': 21, 'sort_order': 1, 'menu_type': 'button', 'is_visible': False, 'is_active': True},
        {'id': 212, 'name': '编辑用户', 'code': 'system_users_edit', 'icon': None, 'path': None, 'component': None,
            'parent_id': 21, 'sort_order': 2, 'menu_type': 'button', 'is_visible': False, 'is_active': True},
        {'id': 213, 'name': '删除用户', 'code': 'system_users_delete', 'icon': None, 'path': None, 'component': None,
            'parent_id': 21, 'sort_order': 3, 'menu_type': 'button', 'is_visible': False, 'is_active': True},

        # 角色管理按钮权限
        {'id': 221, 'name': '新增角色', 'code': 'system_roles_add', 'icon': None, 'path': None, 'component': None,
            'parent_id': 22, 'sort_order': 1, 'menu_type': 'button', 'is_visible': False, 'is_active': True},
        {'id': 222, 'name': '编辑角色', 'code': 'system_roles_edit', 'icon': None, 'path': None, 'component': None,
            'parent_id': 22, 'sort_order': 2, 'menu_type': 'button', 'is_visible': False, 'is_active': True},
        {'id': 223, 'name': '删除角色', 'code': 'system_roles_delete', 'icon': None, 'path': None, 'component': None,
            'parent_id': 22, 'sort_order': 3, 'menu_type': 'button', 'is_visible': False, 'is_active': True},

        # 菜单管理按钮权限
        {'id': 231, 'name': '新增菜单', 'code': 'system_menus_add', 'icon': None, 'path': None, 'component': None,
            'parent_id': 23, 'sort_order': 1, 'menu_type': 'button', 'is_visible': False, 'is_active': True},
        {'id': 232, 'name': '编辑菜单', 'code': 'system_menus_edit', 'icon': None, 'path': None, 'component': None,
            'parent_id': 23, 'sort_order': 2, 'menu_type': 'button', 'is_visible': False, 'is_active': True},
        {'id': 233, 'name': '删除菜单', 'code': 'system_menus_delete', 'icon': None, 'path': None, 'component': None,
            'parent_id': 23, 'sort_order': 3, 'menu_type': 'button', 'is_visible': False, 'is_active': True},

        # 日志管理按钮权限
        {'id': 241, 'name': '查看日志', 'code': 'system_logs_view', 'icon': None, 'path': None, 'component': None,
            'parent_id': 24, 'sort_order': 1, 'menu_type': 'button', 'is_visible': False, 'is_active': True},

        # 数据字典按钮权限
        {'id': 251, 'name': '新增字典', 'code': 'system_dicts_add', 'icon': None, 'path': None, 'component': None,
            'parent_id': 25, 'sort_order': 1, 'menu_type': 'button', 'is_visible': False, 'is_active': True},
        {'id': 252, 'name': '编辑字典', 'code': 'system_dicts_edit', 'icon': None, 'path': None, 'component': None,
            'parent_id': 25, 'sort_order': 2, 'menu_type': 'button', 'is_visible': False, 'is_active': True},
        {'id': 253, 'name': '删除字典', 'code': 'system_dicts_delete', 'icon': None, 'path': None, 'component': None,
            'parent_id': 25, 'sort_order': 3, 'menu_type': 'button', 'is_visible': False, 'is_active': True},

        # 列表页按钮权限
        {'id': 311, 'name': '新增记录', 'code': 'system_list_page_add', 'icon': None, 'path': None, 'component': None,
            'parent_id': 31, 'sort_order': 1, 'menu_type': 'button', 'is_visible': False, 'is_active': True},
        {'id': 312, 'name': '编辑记录', 'code': 'system_list_page_edit', 'icon': None, 'path': None, 'component': None,
            'parent_id': 31, 'sort_order': 2, 'menu_type': 'button', 'is_visible': False, 'is_active': True},
        {'id': 313, 'name': '删除记录', 'code': 'system_list_page_delete', 'icon': None, 'path': None, 'component': None,
            'parent_id': 31, 'sort_order': 3, 'menu_type': 'button', 'is_visible': False, 'is_active': True},

        # 统计列表页按钮权限
        {'id': 331, 'name': '新增记录', 'code': 'system_stats_list_page_add', 'icon': None, 'path': None, 'component': None,
            'parent_id': 33, 'sort_order': 1, 'menu_type': 'button', 'is_visible': False, 'is_active': True},
        {'id': 332, 'name': '编辑记录', 'code': 'system_stats_list_page_edit', 'icon': None, 'path': None, 'component': None,
            'parent_id': 33, 'sort_order': 2, 'menu_type': 'button', 'is_visible': False, 'is_active': True},
        {'id': 333, 'name': '删除记录', 'code': 'system_stats_list_page_delete', 'icon': None, 'path': None, 'component': None,
            'parent_id': 33, 'sort_order': 3, 'menu_type': 'button', 'is_visible': False, 'is_active': True},

        # 卡片列表页按钮权限
        {'id': 341, 'name': '新增卡片', 'code': 'system_card_list_page_add', 'icon': None, 'path': None, 'component': None,
            'parent_id': 34, 'sort_order': 1, 'menu_type': 'button', 'is_visible': False, 'is_active': True},
        {'id': 342, 'name': '编辑卡片', 'code': 'system_card_list_page_edit', 'icon': None, 'path': None, 'component': None,
            'parent_id': 34, 'sort_order': 2, 'menu_type': 'button', 'is_visible': False, 'is_active': True},
        {'id': 343, 'name': '删除卡片', 'code': 'system_card_list_page_delete', 'icon': None, 'path': None, 'component': None,
            'parent_id': 34, 'sort_order': 3, 'menu_type': 'button', 'is_visible': False, 'is_active': True},

        # 树形列表页按钮权限
        {'id': 351, 'name': '新增节点', 'code': 'system_tree_list_page_add', 'icon': None, 'path': None, 'component': None,
            'parent_id': 35, 'sort_order': 1, 'menu_type': 'button', 'is_visible': False, 'is_active': True},
        {'id': 352, 'name': '编辑节点', 'code': 'system_tree_list_page_edit', 'icon': None, 'path': None, 'component': None,
            'parent_id': 35, 'sort_order': 2, 'menu_type': 'button', 'is_visible': False, 'is_active': True},
        {'id': 353, 'name': '删除节点', 'code': 'system_tree_list_page_delete', 'icon': None, 'path': None, 'component': None,
            'parent_id': 35, 'sort_order': 3, 'menu_type': 'button', 'is_visible': False, 'is_active': True},

        # 动态表单页按钮权限
        {'id': 361, 'name': '新增记录', 'code': 'system_dynamic_form_page_add', 'icon': None, 'path': None, 'component': None,
            'parent_id': 36, 'sort_order': 1, 'menu_type': 'button', 'is_visible': False, 'is_active': True},
        {'id': 362, 'name': '编辑记录', 'code': 'system_dynamic_form_page_edit', 'icon': None, 'path': None, 'component': None,
            'parent_id': 36, 'sort_order': 2, 'menu_type': 'button', 'is_visible': False, 'is_active': True},
        {'id': 363, 'name': '删除记录', 'code': 'system_dynamic_form_page_delete', 'icon': None, 'path': None, 'component': None,
            'parent_id': 36, 'sort_order': 3, 'menu_type': 'button', 'is_visible': False, 'is_active': True},

        # 详情标签页按钮权限
        {'id': 4021, 'name': '新增成员', 'code': 'cc_admin_detail_tabs_add', 'icon': None, 'path': None, 'component': None,
            'parent_id': 402, 'sort_order': 1, 'menu_type': 'button', 'is_visible': False, 'is_active': True},
        {'id': 4022, 'name': '编辑成员', 'code': 'cc_admin_detail_tabs_edit', 'icon': None, 'path': None, 'component': None,
            'parent_id': 402, 'sort_order': 2, 'menu_type': 'button', 'is_visible': False, 'is_active': True},
        {'id': 4023, 'name': '删除成员', 'code': 'cc_admin_detail_tabs_delete', 'icon': None, 'path': None, 'component': None,
            'parent_id': 402, 'sort_order': 3, 'menu_type': 'button', 'is_visible': False, 'is_active': True},

        # 甘特图页按钮权限
        {'id': 4031, 'name': '新建任务', 'code': 'cc_admin_gantt_add', 'icon': None, 'path': None, 'component': None,
            'parent_id': 403, 'sort_order': 1, 'menu_type': 'button', 'is_visible': False, 'is_active': True},
        {'id': 4032, 'name': '编辑任务', 'code': 'cc_admin_gantt_edit', 'icon': None, 'path': None, 'component': None,
            'parent_id': 403, 'sort_order': 2, 'menu_type': 'button', 'is_visible': False, 'is_active': True},
        {'id': 4033, 'name': '删除任务', 'code': 'cc_admin_gantt_delete', 'icon': None, 'path': None, 'component': None,
            'parent_id': 403, 'sort_order': 3, 'menu_type': 'button', 'is_visible': False, 'is_active': True},

        # 看板页按钮权限
        {'id': 4011, 'name': '新建卡片/列', 'code': 'cc_admin_kanban_add', 'icon': None, 'path': None, 'component': None,
            'parent_id': 401, 'sort_order': 1, 'menu_type': 'button', 'is_visible': False, 'is_active': True},
        {'id': 4012, 'name': '编辑卡片/列', 'code': 'cc_admin_kanban_edit', 'icon': None, 'path': None, 'component': None,
            'parent_id': 401, 'sort_order': 2, 'menu_type': 'button', 'is_visible': False, 'is_active': True},
        {'id': 4013, 'name': '删除卡片/列', 'code': 'cc_admin_kanban_delete', 'icon': None, 'path': None, 'component': None,
            'parent_id': 401, 'sort_order': 3, 'menu_type': 'button', 'is_visible': False, 'is_active': True},

        # 定时任务按钮权限
        {'id': 321, 'name': '新增任务', 'code': 'system_scheduled_tasks_add', 'icon': None, 'path': None, 'component': None,
            'parent_id': 32, 'sort_order': 1, 'menu_type': 'button', 'is_visible': False, 'is_active': True},
        {'id': 322, 'name': '编辑任务', 'code': 'system_scheduled_tasks_edit', 'icon': None, 'path': None, 'component': None,
            'parent_id': 32, 'sort_order': 2, 'menu_type': 'button', 'is_visible': False, 'is_active': True},
        {'id': 323, 'name': '删除任务', 'code': 'system_scheduled_tasks_delete', 'icon': None, 'path': None, 'component': None,
            'parent_id': 32, 'sort_order': 3, 'menu_type': 'button', 'is_visible': False, 'is_active': True},
        {'id': 324, 'name': '执行任务', 'code': 'system_scheduled_tasks_run', 'icon': None, 'path': None, 'component': None,
            'parent_id': 32, 'sort_order': 4, 'menu_type': 'button', 'is_visible': False, 'is_active': True},
    ]

    print("初始化菜单数据...")

    existing_ids = {m.id for m in Menu.query.all()}

    added_count = 0
    updated_count = 0
    for menu_data in menus_data:
        existing = Menu.query.filter_by(code=menu_data['code']).first()
        if existing:
            for field in ['name', 'icon', 'path', 'component', 'parent_id',
                          'sort_order', 'menu_type', 'is_visible', 'is_active']:
                setattr(existing, field, menu_data.get(field))
            updated_count += 1
            print(f"  更新菜单: [{menu_data['code']}] {menu_data['name']}")
            continue

        menu_id = menu_data['id'] if menu_data['id'] not in existing_ids else None

        menu = Menu(
            name=menu_data['name'],
            code=menu_data['code'],
            icon=menu_data.get('icon'),
            path=menu_data.get('path'),
            component=menu_data.get('component'),
            parent_id=menu_data.get('parent_id'),
            sort_order=menu_data['sort_order'],
            menu_type=menu_data['menu_type'],
            is_visible=menu_data['is_visible'],
            is_active=menu_data['is_active']
        )
        if menu_id:
            menu.id = menu_id

        db.session.add(menu)
        db.session.flush()
        added_count += 1
        existing_ids.add(menu.id)
        print(f"  创建菜单: [{menu_data['code']}] {menu_data['name']} (ID: {menu.id})")

    # 下线历史试验页菜单：保留数据但不在导航展示
    retired_codes = ['component_center_templates', 'component_center_scenarios']
    for code in retired_codes:
        retired_menu = Menu.query.filter_by(code=code).first()
        if retired_menu and (retired_menu.is_active or retired_menu.is_visible):
            retired_menu.is_active = False
            retired_menu.is_visible = False
            updated_count += 1
            print(f"  下线菜单: [{code}]")

    if added_count > 0 or updated_count > 0:
        db.session.commit()
        print(f"菜单同步完成，新增 {added_count} 项，更新 {updated_count} 项\n")
    else:
        print("菜单无变更\n")

    # 兼容显式写入固定 id 后序列未自动推进的问题
    sync_postgres_id_sequence('menus')


def refresh_super_admin_permissions():
    """刷新超级管理员权限（授予全部菜单）"""
    Role = models['Role']
    Menu = models['Menu']

    print("刷新超级管理员权限...")
    admin_role = Role.query.filter_by(code='super_admin').first()
    if not admin_role:
        admin_role = Role(
            name='超级管理员',
            code='super_admin',
            description='拥有所有权限的超级管理员'
        )
        db.session.add(admin_role)
        db.session.flush()
        print("  创建角色: 超级管理员")

    all_menus = Menu.query.all()
    admin_role.menus = all_menus
    print(f"  超级管理员刷新为 {len(all_menus)} 个菜单权限")

    db.session.commit()
    return admin_role


def init_roles():
    """初始化角色"""
    print("初始化角色...")
    admin_role = refresh_super_admin_permissions()
    print("角色初始化完成\n")
    return admin_role


def init_admin_user(admin_role):
    """初始化管理员账号"""
    Admin = models['Admin']

    print("初始化管理员账号...")

    admin_user = Admin.query.filter_by(username='admin').first()
    if not admin_user:
        admin_user = Admin(username='admin')
        admin_user.set_password('admin123')
        db.session.add(admin_user)
        db.session.flush()
        print("  创建用户: admin")
        print("  默认密码: admin123")
    else:
        print("  用户已存在: admin")

    if admin_role not in admin_user.roles:
        admin_user.roles.append(admin_role)
        print("  分配角色: 超级管理员")

    db.session.commit()
    print("管理员账号初始化完成\n")


def main():
    parser = argparse.ArgumentParser(description="RBAC 初始化/增量同步脚本")
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="仅做菜单增量同步 + 超级管理员权限刷新（不清空数据）",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("RBAC系统同步")
    print("=" * 60 + "\n")

    with app.app_context():
        try:
            if args.incremental:
                print("模式: 增量同步\n")
                init_menus()
                admin_role = refresh_super_admin_permissions()
                init_admin_user(admin_role)
            else:
                print("模式: 全量重建\n")
                clear_rbac_data()
                init_menus()
                admin_role = init_roles()
                init_admin_user(admin_role)

            print("=" * 60)
            print("同步完成！")
            print("=" * 60)
            print("\n登录信息：")
            print("  用户名: admin")
            print("  密码: admin123")

        except Exception as e:
            db.session.rollback()
            print(f"\n初始化失败: {e}")
            import traceback
            traceback.print_exc()
            raise SystemExit(1)


if __name__ == '__main__':
    main()
