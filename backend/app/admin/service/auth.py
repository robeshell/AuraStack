# -*- coding: utf-8 -*-
"""认证模块 service 层"""

from backend.app.admin.crud.auth import AuthCRUD
from backend.app.admin.schema.auth import validate_change_password_payload


class AuthServiceError(Exception):
    def __init__(self, message, status_code=400, payload=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.payload = payload or {}


class AuthService:
    def __init__(self, db, admin_model, login_log_model, operation_log_model):
        self.db = db
        self.Admin = admin_model
        self.LoginLog = login_log_model
        self.OperationLog = operation_log_model
        self.crud = AuthCRUD(db, admin_model, login_log_model, operation_log_model)

    def login(self, username, password, session_obj, client_ip, user_agent):
        user = self.crud.get_admin_by_username(username)

        if user and user.check_password(password):
            session_obj['logged_in'] = True
            session_obj['username'] = username
            try:
                self.crud.add_login_log(self.LoginLog(
                    username=username,
                    user_id=user.id,
                    status='success',
                    ip=client_ip,
                    user_agent=user_agent,
                    message='登录成功',
                ))
                self.crud.commit()
            except Exception:
                self.crud.rollback()

            return {
                'message': '登录成功',
                'user': user.to_dict(),
            }, 200

        try:
            self.crud.add_login_log(self.LoginLog(
                username=username or '',
                user_id=user.id if user else None,
                status='failed',
                ip=client_ip,
                user_agent=user_agent,
                message='用户名或密码错误',
            ))
            self.crud.commit()
        except Exception:
            self.crud.rollback()

        raise AuthServiceError('用户名或密码错误', 401)

    def logout(self, username, session_obj, client_ip, user_agent):
        user = self.crud.get_admin_by_username(username) if username else None
        try:
            self.crud.add_operation_log(self.OperationLog(
                username=username or 'unknown',
                user_id=user.id if user else None,
                module='auth',
                action='logout',
                method='POST',
                path='/api/admin/logout',
                target_id=None,
                payload=None,
                ip=client_ip,
                user_agent=user_agent,
                status_code=200,
            ))
            self.crud.commit()
        except Exception:
            self.crud.rollback()

        session_obj.clear()
        return {'message': '已退出登录'}

    def change_password(self, username, data):
        error = validate_change_password_payload(data)
        if error:
            raise AuthServiceError(error, 400)

        old_password = data.get('old_password')
        new_password = data.get('new_password')
        admin = self.crud.get_admin_by_username(username)

        if not admin:
            raise AuthServiceError('用户不存在', 404)
        if not admin.check_password(old_password):
            raise AuthServiceError('旧密码错误', 400)

        try:
            admin.set_password(new_password)
            self.crud.commit()
            return {'message': '密码修改成功'}
        except Exception as e:
            self.crud.rollback()
            raise AuthServiceError(str(e), 500) from e

    def get_current_user(self, username):
        user = self.crud.get_admin_by_username(username)
        if not user:
            raise AuthServiceError('用户不存在', 404)
        return {'user': user.to_dict()}
