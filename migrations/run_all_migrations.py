#!/usr/bin/env python3
"""
运行所有数据库迁移
"""
import os
import sys
import glob

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)


def run_all_migrations():
    """按顺序执行所有迁移文件"""
    migration_files = sorted(glob.glob(os.path.join(current_dir, '[0-9]*.py')))

    if not migration_files:
        print("没有找到迁移文件")
        return

    print(f"找到 {len(migration_files)} 个迁移文件\n")

    for migration_file in migration_files:
        filename = os.path.basename(migration_file)
        print(f"执行: {filename}")
        result = os.system(f"python {migration_file}")
        if result != 0:
            print(f"迁移失败: {filename}")
            sys.exit(1)

    print("\n所有迁移执行完成！")


if __name__ == '__main__':
    run_all_migrations()
