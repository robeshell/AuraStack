"""
应用入口文件
前后端分离架构
"""
from flask import Flask, jsonify, send_from_directory, request
from sqlalchemy import text
from flask_cors import CORS
from flask_compress import Compress
from flask_caching import Cache
from flask_migrate import Migrate
from config import get_config
from backend import db
from backend.models import init_models
from backend.utils import CustomJSONEncoder
from backend.routes.admin import init_admin_routes
from datetime import datetime
import os
import sys

# 获取配置
config_obj = get_config()

# 初始化Flask应用
app = Flask(__name__, static_folder='frontend/dist', static_url_path='')
app.config.from_object(config_obj)
app.config['JSON_AS_ASCII'] = False

# 初始化缓存
app.config['CACHE_TYPE'] = 'SimpleCache'
app.config['CACHE_DEFAULT_TIMEOUT'] = 300
cache = Cache(app)

# 初始化GZIP压缩
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

# 初始化CORS
CORS(app, resources=config_obj.CORS_RESOURCES)

# 设置JSON编码器
app.json_encoder = CustomJSONEncoder

# 初始化数据库
db.init_app(app)

# 在应用上下文中初始化模型
with app.app_context():
    models = init_models(db)

# 初始化数据库迁移
migrate = Migrate(app, db)

# 注册路由蓝图
admin_bp = init_admin_routes(db, models)
app.register_blueprint(admin_bp)


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


if __name__ == '__main__':
    os.makedirs('instance', exist_ok=True)

    port = int(sys.argv[1]) if len(sys.argv) > 1 else config_obj.DEFAULT_PORT
    print(f"\n{'='*50}")
    print(f"AuraStack 启动")
    print(f"{'='*50}")
    print(f"环境: {os.environ.get('FLASK_ENV', 'development')}")
    print(f"端口: {port}")
    print(f"{'='*50}\n")

    app.run(host='0.0.0.0', port=port, debug=config_obj.DEBUG)
