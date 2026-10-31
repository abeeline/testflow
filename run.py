"""TestFlow 启动入口：python run.py [--host 127.0.0.1] [--port 8010] [--no-browser]

Windows 发布包里由 start.bat 调用。端口被占用时自动顺延到下一个可用端口，
启动成功后自动打开浏览器。
"""
import argparse
import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


def _port_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False


def _pick_port(host: str, preferred: int) -> int:
    for port in range(preferred, preferred + 20):
        if _port_free(host, port):
            return port
    raise SystemExit(f"端口 {preferred}-{preferred + 19} 都被占用，请用 --port 指定其它端口。")


def _open_browser_when_ready(url: str, port: int):
    def worker():
        for _ in range(60):
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                    break
            except OSError:
                time.sleep(0.5)
        webbrowser.open(url)

    threading.Thread(target=worker, daemon=True).start()


def main():
    parser = argparse.ArgumentParser(description="TestFlow 测试设计工作台")
    parser.add_argument("--host", default=os.environ.get("TESTFLOW_HOST", "127.0.0.1"),
                        help="监听地址，局域网共享用 0.0.0.0（默认 127.0.0.1）")
    parser.add_argument("--port", type=int, default=int(os.environ.get("TESTFLOW_PORT", "8010")))
    parser.add_argument("--no-browser", action="store_true", help="启动后不自动打开浏览器")
    args = parser.parse_args()

    import uvicorn
    from main import app
    from utils.paths import DATA_DIR

    port = _pick_port(args.host, args.port)
    url = f"http://127.0.0.1:{port}/"
    print("=" * 60)
    print(" TestFlow 测试设计工作台")
    print(f" 访问地址: {url}")
    if args.host not in ("127.0.0.1", "localhost"):
        print(f" 局域网访问: http://<本机IP>:{port}/")
    print(f" 数据目录: {DATA_DIR}")
    print(" 关闭本窗口即可停止服务")
    print("=" * 60, flush=True)

    if not args.no_browser:
        _open_browser_when_ready(url, port)
    uvicorn.run(app, host=args.host, port=port, log_level="warning")


if __name__ == "__main__":
    main()
