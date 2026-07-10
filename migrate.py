#!/usr/bin/env python3
"""数据库迁移管理脚本

使用方法:
    python migrate.py upgrade    # 升级到最新版本
    python migrate.py downgrade  # 回滚到上一个版本
    python migrate.py current    # 查看当前版本
    python migrate.py history    # 查看迁移历史
"""
import subprocess
import sys


def run_command(cmd: list[str]) -> int:
    """执行命令"""
    print(f"执行: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd="backend")
    return result.returncode


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    if command == "upgrade":
        # 升级到最新版本
        returncode = run_command(["alembic", "upgrade", "head"])
        if returncode == 0:
            print("✅ 数据库升级成功")
        else:
            print("❌ 数据库升级失败")
            sys.exit(1)

    elif command == "downgrade":
        # 回滚到上一个版本
        returncode = run_command(["alembic", "downgrade", "-1"])
        if returncode == 0:
            print("✅ 数据库回滚成功")
        else:
            print("❌ 数据库回滚失败")
            sys.exit(1)

    elif command == "current":
        # 查看当前版本
        run_command(["alembic", "current"])

    elif command == "history":
        # 查看迁移历史
        run_command(["alembic", "history"])

    elif command == "generate":
        # 自动生成迁移脚本
        if len(sys.argv) < 3:
            print("请提供迁移描述，例如: python migrate.py generate '添加用户头像字段'")
            sys.exit(1)
        message = sys.argv[2]
        returncode = run_command(["alembic", "revision", "--autogenerate", "-m", message])
        if returncode == 0:
            print("✅ 迁移脚本生成成功")
        else:
            print("❌ 迁移脚本生成失败")
            sys.exit(1)

    else:
        print(f"未知命令: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
