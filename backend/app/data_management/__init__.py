# -*- coding: utf-8 -*-
"""Data Management 大模块"""

from backend.app.data_management.api import register_data_management_routes
from backend.app.data_management.model import build_data_management_models

__all__ = ['register_data_management_routes', 'build_data_management_models']
