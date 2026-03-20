"""
应用配置文件
支持开发环境(development)和生产环境(production)
"""
import os
from dotenv import load_dotenv

_env = os.environ.get('FLASK_ENV', 'development')
load_dotenv(f'.env.{_env}')


class Config:
    """基础配置"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-change-in-production'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 管理员账号
    ADMIN_USERNAME = 'admin'
    ADMIN_PASSWORD = 'admin123'

    # CORS配置
    CORS_RESOURCES = {
        r"/api/*": {"origins": "*"}
    }

    # 定时任务调度
    ENABLE_TASK_SCHEDULER = os.environ.get('ENABLE_TASK_SCHEDULER', 'true')
    TASK_SCHEDULER_INTERVAL_SECONDS = int(os.environ.get('TASK_SCHEDULER_INTERVAL_SECONDS', '20'))
    TASK_SCHEDULER_LEASE_SECONDS = int(os.environ.get('TASK_SCHEDULER_LEASE_SECONDS', '1800'))
    RUN_SCHEDULER_IN_WEB = os.environ.get('RUN_SCHEDULER_IN_WEB', 'false')


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    TESTING = False

    # 开发环境数据库 - PostgreSQL
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'postgresql://localhost/aurastack_dev'

    SQLALCHEMY_ECHO = False  # 设为True可以看到SQL语句

    DEFAULT_PORT = 5001


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    TESTING = False

    # 生产环境数据库 - PostgreSQL
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://localhost/aurastack'

    SQLALCHEMY_ECHO = False

    DEFAULT_PORT = 5000

    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD') or 'admin123'


class TestingConfig(Config):
    """测试环境配置"""
    DEBUG = True
    TESTING = True

    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

    DEFAULT_PORT = 5002


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(env_name=None):
    if env_name is None:
        env_name = os.environ.get('FLASK_ENV', 'development')
    return config.get(env_name, config['default'])
