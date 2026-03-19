# -*- coding: utf-8 -*-
"""请求元信息工具"""

import json
from flask import request


def get_client_ip():
    """获取客户端 IP"""
    xff = request.headers.get('X-Forwarded-For', '')
    if xff:
        return xff.split(',')[0].strip()
    real_ip = request.headers.get('X-Real-IP')
    if real_ip:
        return real_ip.strip()
    return request.remote_addr


def get_user_agent():
    """获取客户端 UA"""
    return request.headers.get('User-Agent', '')[:500]


def safe_payload(payload):
    """序列化请求体并限制长度"""
    if payload is None:
        return None
    try:
        text = json.dumps(payload, ensure_ascii=False)
    except Exception:
        text = str(payload)
    if len(text) > 2000:
        return text[:2000] + '...(truncated)'
    return text
