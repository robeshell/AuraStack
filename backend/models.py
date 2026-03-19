"""
数据库模型定义 - 框架系统模型
包含 RBAC（用户/角色/菜单）和审计日志
"""
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash


def init_models(db):
    """初始化所有模型类"""

    # RBAC 中间表
    user_roles = db.Table('user_roles',
        db.Column('user_id', db.Integer, db.ForeignKey('admin_users.id', ondelete='CASCADE'), primary_key=True),
        db.Column('role_id', db.Integer, db.ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True)
    )

    role_menus = db.Table('role_menus',
        db.Column('role_id', db.Integer, db.ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
        db.Column('menu_id', db.Integer, db.ForeignKey('menus.id', ondelete='CASCADE'), primary_key=True)
    )

    class Role(db.Model):
        """角色模型"""
        __tablename__ = 'roles'
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(100), nullable=False)
        code = db.Column(db.String(50), nullable=False, unique=True)
        description = db.Column(db.Text)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)

        menus = db.relationship('Menu', secondary='role_menus',
                                backref=db.backref('roles', lazy='dynamic'))

        def to_dict(self, include_menus=False):
            result = {
                'id': self.id,
                'name': self.name,
                'code': self.code,
                'description': self.description,
                'created_at': self.created_at.isoformat() if self.created_at else None
            }
            if include_menus:
                sorted_menus = sorted(self.menus, key=lambda m: (m.sort_order or 0, m.id))
                result['menu_ids'] = [m.id for m in sorted_menus]
                result['menus'] = [{
                    'id': m.id,
                    'name': m.name,
                    'code': m.code,
                    'parent_id': m.parent_id,
                    'menu_type': m.menu_type,
                } for m in sorted_menus]
            return result

    class Admin(db.Model):
        """管理员用户模型"""
        __tablename__ = 'admin_users'

        id = db.Column(db.Integer, primary_key=True)
        username = db.Column(db.String(50), unique=True, nullable=False)
        password_hash = db.Column(db.String(200), nullable=False)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)

        roles = db.relationship('Role', secondary=user_roles,
                                backref=db.backref('users', lazy='dynamic'))

        def set_password(self, password):
            self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

        def check_password(self, password):
            return check_password_hash(self.password_hash, password)

        def has_menu_access(self, menu_id):
            if any(role.code == 'super_admin' for role in self.roles):
                return True
            for role in self.roles:
                for menu in role.menus:
                    if menu.id == menu_id:
                        return True
            return False

        def has_menu_code_access(self, menu_code):
            if any(role.code == 'super_admin' for role in self.roles):
                return True
            for role in self.roles:
                for menu in role.menus:
                    if menu.code == menu_code:
                        return True
            return False

        def get_all_menu_ids(self):
            menu_ids = set()
            for role in self.roles:
                for menu in role.menus:
                    menu_ids.add(menu.id)
            return list(menu_ids)

        def get_all_menu_codes(self):
            menu_codes = set()
            for role in self.roles:
                for menu in role.menus:
                    menu_codes.add(menu.code)
            return list(menu_codes)

        def to_dict(self):
            return {
                'id': self.id,
                'username': self.username,
                'created_at': self.created_at.isoformat() if self.created_at else None,
                'roles': [r.to_dict() for r in self.roles],
                'menu_codes': self.get_all_menu_codes()
            }

    class Menu(db.Model):
        """菜单模型"""
        __tablename__ = 'menus'

        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(100), nullable=False)
        code = db.Column(db.String(50), nullable=False, unique=True)
        icon = db.Column(db.String(100))
        path = db.Column(db.String(200))
        component = db.Column(db.String(200))
        parent_id = db.Column(db.Integer, db.ForeignKey('menus.id', ondelete='CASCADE'))
        sort_order = db.Column(db.Integer, default=0)
        is_visible = db.Column(db.Boolean, default=True)
        is_active = db.Column(db.Boolean, default=True)
        menu_type = db.Column(db.String(20), default='menu')  # menu/button
        description = db.Column(db.Text)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

        children = db.relationship('Menu', backref=db.backref('parent', remote_side=[id]),
                                   cascade='all, delete-orphan', lazy='dynamic')

        def to_dict(self, include_children=False):
            data = {
                'id': self.id,
                'name': self.name,
                'code': self.code,
                'icon': self.icon,
                'path': self.path,
                'component': self.component,
                'parent_id': self.parent_id,
                'sort_order': self.sort_order,
                'is_visible': self.is_visible,
                'is_active': self.is_active,
                'menu_type': self.menu_type,
                'description': self.description,
                'created_at': self.created_at.isoformat() if self.created_at else None,
                'updated_at': self.updated_at.isoformat() if self.updated_at else None
            }
            if include_children:
                data['children'] = [child.to_dict(True) for child in self.children.order_by('sort_order')]
            return data

    class DictType(db.Model):
        """数据字典类型模型"""
        __tablename__ = 'dict_types'

        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(100), nullable=False)
        code = db.Column(db.String(100), nullable=False, unique=True)
        description = db.Column(db.Text)
        sort_order = db.Column(db.Integer, default=0)
        is_active = db.Column(db.Boolean, default=True)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

        items = db.relationship(
            'DictItem',
            backref=db.backref('dict_type'),
            cascade='all, delete-orphan',
            lazy='dynamic'
        )

        def to_dict(self, include_items=False):
            data = {
                'id': self.id,
                'name': self.name,
                'code': self.code,
                'description': self.description,
                'sort_order': self.sort_order,
                'is_active': self.is_active,
                'item_count': self.items.count(),
                'created_at': self.created_at.isoformat() if self.created_at else None,
                'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            }
            if include_items:
                data['items'] = [
                    item.to_dict(include_type=False)
                    for item in self.items.order_by(DictItem.sort_order.asc(), DictItem.id.asc()).all()
                ]
            return data

    class DictItem(db.Model):
        """数据字典项模型"""
        __tablename__ = 'dict_items'
        __table_args__ = (
            db.UniqueConstraint('dict_type_id', 'value', name='uq_dict_items_type_value'),
        )

        id = db.Column(db.Integer, primary_key=True)
        dict_type_id = db.Column(db.Integer, db.ForeignKey('dict_types.id', ondelete='CASCADE'), nullable=False)
        label = db.Column(db.String(100), nullable=False)
        value = db.Column(db.String(100), nullable=False)
        color = db.Column(db.String(30))
        sort_order = db.Column(db.Integer, default=0)
        is_default = db.Column(db.Boolean, default=False)
        is_active = db.Column(db.Boolean, default=True)
        description = db.Column(db.Text)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

        def to_dict(self, include_type=True):
            data = {
                'id': self.id,
                'dict_type_id': self.dict_type_id,
                'label': self.label,
                'value': self.value,
                'color': self.color,
                'sort_order': self.sort_order,
                'is_default': self.is_default,
                'is_active': self.is_active,
                'description': self.description,
                'created_at': self.created_at.isoformat() if self.created_at else None,
                'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            }
            if include_type and self.dict_type:
                data['dict_type_code'] = self.dict_type.code
                data['dict_type_name'] = self.dict_type.name
            return data

    class QueryManagement(db.Model):
        """查询管理模型（表单与 CRUD 模板演示）"""
        __tablename__ = 'query_managements'

        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(120), nullable=False)
        query_code = db.Column(db.String(120), nullable=False, unique=True)
        category = db.Column(db.String(50), default='general')
        keyword = db.Column(db.String(200))
        data_source = db.Column(db.String(100))
        owner = db.Column(db.String(100))
        priority = db.Column(db.Integer, default=0)
        is_active = db.Column(db.Boolean, default=True)
        description = db.Column(db.Text)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

        def to_dict(self):
            return {
                'id': self.id,
                'name': self.name,
                'query_code': self.query_code,
                'category': self.category,
                'keyword': self.keyword,
                'data_source': self.data_source,
                'owner': self.owner,
                'priority': self.priority,
                'is_active': self.is_active,
                'description': self.description,
                'created_at': self.created_at.isoformat() if self.created_at else None,
                'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            }

    class LoginLog(db.Model):
        """登录日志模型"""
        __tablename__ = 'login_logs'

        id = db.Column(db.Integer, primary_key=True)
        username = db.Column(db.String(100), nullable=False)
        user_id = db.Column(db.Integer, db.ForeignKey('admin_users.id', ondelete='SET NULL'))
        status = db.Column(db.String(20), nullable=False, default='success')
        ip = db.Column(db.String(64))
        user_agent = db.Column(db.String(500))
        message = db.Column(db.String(500))
        created_at = db.Column(db.DateTime, default=datetime.utcnow)

        def to_dict(self):
            return {
                'id': self.id,
                'username': self.username,
                'user_id': self.user_id,
                'status': self.status,
                'ip': self.ip,
                'user_agent': self.user_agent,
                'message': self.message,
                'created_at': self.created_at.isoformat() if self.created_at else None
            }

    class OperationLog(db.Model):
        """操作日志模型"""
        __tablename__ = 'operation_logs'

        id = db.Column(db.Integer, primary_key=True)
        username = db.Column(db.String(100), nullable=False)
        user_id = db.Column(db.Integer, db.ForeignKey('admin_users.id', ondelete='SET NULL'))
        module = db.Column(db.String(100), nullable=False)
        action = db.Column(db.String(50), nullable=False)
        method = db.Column(db.String(10), nullable=False)
        path = db.Column(db.String(255), nullable=False)
        target_id = db.Column(db.String(100))
        payload = db.Column(db.Text)
        ip = db.Column(db.String(64))
        user_agent = db.Column(db.String(500))
        status_code = db.Column(db.Integer)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)

        def to_dict(self):
            return {
                'id': self.id,
                'username': self.username,
                'user_id': self.user_id,
                'module': self.module,
                'action': self.action,
                'method': self.method,
                'path': self.path,
                'target_id': self.target_id,
                'payload': self.payload,
                'ip': self.ip,
                'user_agent': self.user_agent,
                'status_code': self.status_code,
                'created_at': self.created_at.isoformat() if self.created_at else None
            }

    return {
        'Admin': Admin,
        'Role': Role,
        'Menu': Menu,
        'DictType': DictType,
        'DictItem': DictItem,
        'QueryManagement': QueryManagement,
        'LoginLog': LoginLog,
        'OperationLog': OperationLog,
    }
