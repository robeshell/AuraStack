# -*- coding: utf-8 -*-
"""Data Management model 层入口"""

from .entities_query_management import build_query_management_model


def build_data_management_models(db):
    return build_query_management_model(db)
