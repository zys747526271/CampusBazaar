"""本地一键启动：``python -m backend.dev``。

流程：加载配置 → 执行 Alembic 迁移 → 幂等灌入演示数据 → 启动服务与定时任务。
失败时给出可读原因（端口占用 / 依赖缺失 / 数据库不可写），而不是堆栈。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from backend import create_app
from backend.config import ROOT_DIR

BANNER = """
  ______                             ____                  __
 / ____/___ _____ ___  __  _______ / __ )____ _____  ____/ /___ ______
/ /   / __ `/ __ `__ \\/ / / / ___/ / __  / __ `/ __ \\/ __  / __ `/ ___/
/ /___/ /_/ / / / / / / /_/ / /   / /_/ / /_/ / /_/ / /_/ / /_/ / /
\\____/\\__,_/_/ /_/ /_/\\__,_/_/   /_____/\\__,_/\\__,_/\\__,_/\\__,_/_/
"""


def run_migrations() -> None:
    from alembic import command
    from alembic.config import Config as AlembicConfig

    ini = Path(ROOT_DIR) / "alembic.ini"
    if not ini.exists():
        raise RuntimeError("未找到 alembic.ini，无法初始化数据库结构")
    alembic_config = AlembicConfig(str(ini))
    alembic_config.set_main_option("script_location", str(Path(ROOT_DIR) / "migrations"))
    command.upgrade(alembic_config, "head")


def main() -> int:
    parser = argparse.ArgumentParser(description="CampusBazaar 本地开发服务器")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--no-seed", action="store_true", help="跳过演示数据")
    parser.add_argument("--serve-dist", action="store_true", help="同时托管 frontend/dist（单命令演示）")
    args = parser.parse_args()

    try:
        app = create_app()
    except Exception as exc:  # noqa: BLE001 - 启动失败必须给出可读原因
        print(f"[启动失败] 配置加载异常：{exc}", file=sys.stderr)
        return 1

    if args.serve_dist:
        app.config["SERVE_FRONTEND"] = True

    print(BANNER)
    print(f"  环境      : {app.config.get('ENV')}")
    print(f"  数据库    : {app.config.get('SQLALCHEMY_DATABASE_URI')}")
    print(f"  接口地址  : http://{args.host}:{args.port}/api")

    try:
        with app.app_context():
            run_migrations()
            print("  数据库结构: 已迁移到最新版本")
            if app.config.get("SEED_DEMO_DATA") and not args.no_seed:
                from backend.seed import seed_demo_data

                seed_demo_data()
    except Exception as exc:  # noqa: BLE001
        print(f"[启动失败] 数据库初始化异常：{exc}", file=sys.stderr)
        print("提示：确认 instance/ 目录可写，或删除 instance/campus.db 后重试。", file=sys.stderr)
        return 1

    if app.config.get("CAPTCHA_MODE") == "dev":
        print(f"  验证码台账: http://{args.host}:{args.port}/dev/captchas （仅本地）")
    if app.config.get("SERVE_FRONTEND"):
        dist = Path(app.config["FRONTEND_DIST"]) / "index.html"
        if dist.exists():
            print(f"  前端页面  : http://{args.host}:{args.port}/")
        else:
            print("  提示：frontend/dist 不存在，先执行 cd frontend && npm run build")
    print("  按 Ctrl+C 停止\n")

    from backend.services.jobs import start_scheduler

    try:
        with app.app_context():
            start_scheduler(app)
        app.run(host=args.host, port=args.port, debug=False, use_reloader=False, threaded=True)
    except OSError as exc:
        print(f"[启动失败] 端口 {args.port} 可能已被占用：{exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n已停止。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
