"""Entrypoint: python main.py [gateway|worker|heartbeat|watchdog]"""
import sys


def main() -> None:
    role = sys.argv[1] if len(sys.argv) > 1 else "gateway"
    if role == "gateway":
        from gateway.telegram_bot import run
    elif role == "worker":
        from runtime.worker import run
    elif role == "heartbeat":
        from orchestrator.heartbeat import run
    elif role == "watchdog":
        from supervisor.watchdog import run
    else:
        raise SystemExit(f"Vai trò không hợp lệ: {role}")
    run()


if __name__ == "__main__":
    main()
