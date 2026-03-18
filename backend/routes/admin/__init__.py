# -*- coding: utf-8 -*-
"""
后台管理路由模块 - 主入口
"""
from flask import Blueprint

bp = Blueprint('admin', __name__)


def init_admin_routes(db, models):
    """初始化后台管理路由"""
    from . import auth, users, roles, menus, logs

    auth.init_auth_routes(db, models)
    users.init_users_routes(db, models)
    roles.init_roles_routes(db, models)
    menus.init_menus_routes(db, models)
    logs.init_logs_routes(db, models)

    return bp
