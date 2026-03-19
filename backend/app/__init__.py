# -*- coding: utf-8 -*-
"""业务应用分层入口"""

from backend.app.admin import build_admin_models
from backend.app.data_management import build_data_management_models
from backend.app.router import init_app_routes


def init_models(db):
    models = {}
    models.update(build_admin_models(db))
    models.update(build_data_management_models(db))
    return models


__all__ = ['init_models', 'init_app_routes']
