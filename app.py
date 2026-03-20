"""
应用入口文件
前后端分离架构
"""
from datetime import datetime
import os
import sys

from flask import Flask, jsonify, request, send_from_directory
from flask_caching import Cache
from flask_compress import Compress
from flask_cors import CORS
from flask_migrate import Migrate
from sqlalchemy import text

from backend import db
from backend.app import init_app_routes, init_models
from backend.common.json_encoder import CustomJSONEncoder
from backend.common.scheduler import init_scheduled_task_runner
from config import get_config

_APP_CACHE = {}


def _is_truthy(value):
    return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}


def _register_builtin_routes(app):
    @app.after_request
    def add_header(response):
        """为静态资源添加缓存头"""
        static_extensions = ('.js', '.css', '.png', '.jpg', '.jpeg',
                             '.gif', '.svg', '.ico', '.woff', '.woff2', '.ttf', '.otf')
        if request.path.endswith(static_extensions):
            response.headers['Cache-Control'] = 'public, max-age=604800'
            response.headers.pop('Expires', None)
            response.headers.pop('Pragma', None)
        return response

    @app.route('/health')
    def health_check():
        """健康检查端点"""
        try:
            db.session.execute(text('SELECT 1'))
            return jsonify({
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "database": "connected"
            })
        except Exception as e:
            return jsonify({
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }), 500

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_frontend(path):
        """服务前端 SPA"""
        frontend_dist = os.path.join(app.root_path, 'frontend', 'dist')
        if path and os.path.exists(os.path.join(frontend_dist, path)):
            return send_from_directory(frontend_dist, path)
        index_path = os.path.join(frontend_dist, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(frontend_dist, 'index.html')
        return jsonify({"message": "AuraStack API", "status": "running"}), 200


def create_app(env_name=None, start_scheduler=None, scheduler_force=False):
    resolved_env = env_name or os.environ.get('FLASK_ENV', 'development')
    cache_key = resolved_env
    cached_app = _APP_CACHE.get(cache_key)
    if cached_app is not None:
        cached_models = cached_app.extensions.get('app_models', {})
        if start_scheduler is None:
            start_scheduler = _is_truthy(cached_app.config.get('RUN_SCHEDULER_IN_WEB', 'false'))
        if start_scheduler:
            init_scheduled_task_runner(cached_app, db, cached_models, force=scheduler_force)
        return cached_app

    config_obj = get_config(resolved_env)

    app = Flask(__name__, static_folder='frontend/dist', static_url_path='')
    app.config.from_object(config_obj)
    app.config['JSON_AS_ASCII'] = False

    app.config['CACHE_TYPE'] = 'SimpleCache'
    app.config['CACHE_DEFAULT_TIMEOUT'] = 300
    Cache(app)

    app.config['COMPRESS_MIMETYPES'] = [
        'text/html',
        'text/css',
        'text/xml',
        'application/json',
        'application/javascript',
        'text/javascript',
    ]
    app.config['COMPRESS_LEVEL'] = 6
    app.config['COMPRESS_MIN_SIZE'] = 500
    Compress(app)

    CORS(app, resources=config_obj.CORS_RESOURCES)
    app.json_encoder = CustomJSONEncoder

    db.init_app(app)

    with app.app_context():
        models = init_models(db)

    Migrate(app, db, directory='backend/migrations')
    app.register_blueprint(init_app_routes(db, models))
    app.extensions['app_models'] = models

    if start_scheduler is None:
        start_scheduler = _is_truthy(app.config.get('RUN_SCHEDULER_IN_WEB', 'false'))
    if start_scheduler:
        init_scheduled_task_runner(app, db, models, force=scheduler_force)

    _register_builtin_routes(app)
    _APP_CACHE[cache_key] = app
    return app


# Flask CLI / WSGI 默认使用该实例，不自动启调度器，避免多 worker 重复执行任务。
app = create_app(start_scheduler=False)
models = app.extensions.get('app_models', {})


if __name__ == '__main__':
    os.makedirs('instance', exist_ok=True)

    runtime_app = create_app(start_scheduler=True)
    port = int(sys.argv[1]) if len(sys.argv) > 1 else runtime_app.config.get('DEFAULT_PORT', 5001)

    print(f"\n{'='*50}")
    print("AuraStack 启动")
    print(f"{'='*50}")
    print(f"环境: {os.environ.get('FLASK_ENV', 'development')}")
    print(f"端口: {port}")
    print(f"{'='*50}\n")

    runtime_app.run(host='0.0.0.0', port=port, debug=runtime_app.config.get('DEBUG', False))
