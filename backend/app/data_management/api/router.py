# -*- coding: utf-8 -*-
"""Query Management 路由装配"""

from backend.app.data_management.api.query_management import init_query_management_api


def register_data_management_routes(bp, db, models):
    init_query_management_api(bp, db, models)
