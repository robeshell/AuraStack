# -*- coding: utf-8 -*-
"""日志模块 model 入口"""


def get_admin_model(models):
    return models['Admin']


def get_login_log_model(models):
    return models['LoginLog']


def get_operation_log_model(models):
    return models['OperationLog']
