#!/usr/bin/env python3
"""
数据库迁移通用工具类
"""
import os
import sys
from datetime import datetime

try:
    import psycopg2
except ImportError:
    print("错误: psycopg2 未安装")
    print("请安装: pip install psycopg2-binary")
    sys.exit(1)


class MigrationBase:
    """迁移包装基类"""

    def __init__(self, migration_name, description=""):
        self.migration_name = migration_name
        self.description = description
        self.conn = None

    def get_db_connection(self):
        """获取数据库连接"""
        flask_env = os.environ.get('FLASK_ENV', 'development')
        database_url = os.environ.get(
            'DATABASE_URL') if flask_env == 'production' else os.environ.get('DEV_DATABASE_URL')

        if not database_url:
            try:
                root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                if root_path not in sys.path:
                    sys.path.insert(0, root_path)

                from config import get_config
                config_obj = get_config(flask_env)
                database_url = config_obj.SQLALCHEMY_DATABASE_URI
                print(f"使用 {flask_env} 环境配置")
            except Exception as e:
                print(f"无法获取数据库连接信息: {e}")
                sys.exit(1)

        try:
            return psycopg2.connect(database_url)
        except Exception as e:
            print(f"数据库连接失败: {e}")
            sys.exit(1)

    def init_migration_table(self):
        """确保迁移记录表存在"""
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS database_migrations (
                    id SERIAL PRIMARY KEY,
                    migration_name VARCHAR(255) NOT NULL UNIQUE,
                    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    success BOOLEAN DEFAULT TRUE,
                    error_message TEXT
                )
            """)
            self.conn.commit()
        finally:
            cursor.close()

    def check_executed(self):
        """检查迁移是否已成功执行"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT 1 FROM database_migrations WHERE migration_name = %s AND success = TRUE",
            (self.migration_name,)
        )
        exists = cursor.fetchone() is not None
        cursor.close()
        return exists

    def record_result(self, success=True, error_message=None):
        """记录迁移结果"""
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO database_migrations (migration_name, executed_at, success, error_message)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (migration_name) DO UPDATE
                SET executed_at = EXCLUDED.executed_at,
                    success = EXCLUDED.success,
                    error_message = EXCLUDED.error_message
            """, (self.migration_name, datetime.now(), success, error_message))
            self.conn.commit()
        finally:
            cursor.close()

    def run(self, up_func, down_func):
        """运行迁移逻辑"""
        print(f"\n{'='*60}")
        print(f"数据库迁移: {self.migration_name}")
        if self.description:
            print(f"描述: {self.description}")
        print(f"{'='*60}\n")

        is_rollback = len(sys.argv) > 1 and sys.argv[1] == 'rollback'
        self.conn = self.get_db_connection()

        try:
            self.init_migration_table()

            if is_rollback:
                print("警告: 准备回滚迁移...")
                confirm = input("请输入 'YES' 确认回滚: ")
                if confirm == 'YES':
                    success = down_func(self.conn)
                    if success:
                        cursor = self.conn.cursor()
                        cursor.execute(
                            "DELETE FROM database_migrations WHERE migration_name = %s",
                            (self.migration_name,)
                        )
                        self.conn.commit()
                        print("\n回滚成功")
                    return 0 if success else 1
                else:
                    print("回滚已取消")
                    return 0
            else:
                if self.check_executed():
                    print("此迁移已执行过，将再次执行（幂等操作）")

                print("开始执行迁移...")
                success = up_func(self.conn)
                self.record_result(success=success)

                if success:
                    print("\n迁移执行完成！")
                return 0 if success else 1

        except Exception as e:
            print(f"\n执行过程中发生异常: {e}")
            if self.conn:
                self.conn.rollback()
            if not is_rollback:
                self.record_result(success=False, error_message=str(e))
            return 1
        finally:
            self.conn.close()
            print("数据库连接已关闭\n")
