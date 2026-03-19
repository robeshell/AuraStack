# -*- coding: utf-8 -*-
"""查询管理 API 层"""

from flask import jsonify, request, session

from backend.common.auth import login_required
from backend.app.data_management.model.query_management import get_admin_model, get_query_management_model
from backend.app.data_management.schema.query_management import parse_bool
from backend.app.data_management.service.query_management import QueryManagementService, QueryManagementServiceError


def init_query_management_api(bp, db, models):
    Admin = get_admin_model(models)
    service = QueryManagementService(db, get_query_management_model(models))

    def has_permission(code):
        username = session.get('username')
        if not username:
            return False
        user = Admin.query.filter_by(username=username).first()
        return bool(user and user.has_menu_code_access(code))

    def handle_service_error(error):
        body = {'error': error.message}
        body.update(error.payload)
        return jsonify(body), error.status_code

    @bp.route('/api/admin/query-management', methods=['GET', 'POST'])
    @login_required
    def manage_query_management_list():
        if request.method == 'GET':
            if not has_permission('system_query_management'):
                return jsonify({'error': '无权限查看查询管理列表'}), 403

            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 20, type=int)
            search = (request.args.get('search') or '').strip()
            category = (request.args.get('category') or '').strip()
            owner = (request.args.get('owner') or '').strip()
            is_active = parse_bool(request.args.get('is_active'))
            return jsonify(service.list_items(
                page=page,
                per_page=per_page,
                search=search,
                category=category,
                owner=owner,
                is_active=is_active,
            ))

        if not has_permission('system_query_management_add'):
            return jsonify({'error': '无权限新增查询配置'}), 403

        try:
            payload, status = service.create_item(request.get_json() or {})
            return jsonify(payload), status
        except QueryManagementServiceError as e:
            return handle_service_error(e)

    @bp.route('/api/admin/query-management/<int:item_id>', methods=['GET', 'PUT', 'DELETE'])
    @login_required
    def manage_query_management_detail(item_id):
        item = service.crud.get_or_404(item_id)

        if request.method == 'GET':
            if not has_permission('system_query_management'):
                return jsonify({'error': '无权限查看查询配置'}), 403
            return jsonify(item.to_dict())

        if request.method == 'PUT':
            if not has_permission('system_query_management_edit'):
                return jsonify({'error': '无权限编辑查询配置'}), 403
            try:
                return jsonify(service.update_item(item, request.get_json() or {}))
            except QueryManagementServiceError as e:
                return handle_service_error(e)

        if not has_permission('system_query_management_delete'):
            return jsonify({'error': '无权限删除查询配置'}), 403

        try:
            return jsonify(service.delete_item(item))
        except QueryManagementServiceError as e:
            return handle_service_error(e)

    @bp.route('/api/admin/query-management/export', methods=['GET', 'POST'])
    @login_required
    def export_query_management():
        if not has_permission('system_query_management'):
            return jsonify({'error': '无权限导出查询配置'}), 403

        try:
            payload = request.args if request.method == 'GET' else (request.get_json() or {})
            return service.export_items(payload, request_method=request.method)
        except QueryManagementServiceError as e:
            return handle_service_error(e)

    @bp.route('/api/admin/query-management/template', methods=['GET'])
    @login_required
    def download_query_management_template():
        if not has_permission('system_query_management'):
            return jsonify({'error': '无权限下载查询管理导入模板'}), 403

        try:
            return service.download_template(request.args.get('file_type'))
        except QueryManagementServiceError as e:
            return handle_service_error(e)

    @bp.route('/api/admin/query-management/import', methods=['POST'])
    @login_required
    def import_query_management():
        if not has_permission('system_query_management_edit'):
            return jsonify({'error': '无权限导入查询配置'}), 403

        try:
            return jsonify(service.import_items(request.files.get('file')))
        except QueryManagementServiceError as e:
            return handle_service_error(e)
