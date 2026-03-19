# -*- coding: utf-8 -*-
"""一级模块路由装配入口"""

from flask import Blueprint

from backend.app.admin import register_admin_routes
from backend.app.data_management import register_data_management_routes


bp = Blueprint('admin', __name__)


def init_app_routes(db, models):
    register_admin_routes(bp, db, models)
    register_data_management_routes(bp, db, models)
    return bp
