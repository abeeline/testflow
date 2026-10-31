"""打 Windows 发布包（免安装，解压后双击 start.bat 即可运行）。

在任意系统（macOS / Linux / Windows）上执行，需要能访问 nuget.org 和 PyPI：

    python scripts/build_windows_release.py [--version 1.0.0] [--out release]

产物：release/TestFlow-<version>-win64.zip，解压后的目录结构：

    TestFlow-<version>-win64/
      start.bat          双击启动
      使用说明.txt
      python/            内置 Python（来自 nuget.org 官方 python 包），依赖已预装
      app/               程序代码
      data/              配置、设计历史、RAG 文档（首次运行自动创建，升级时保留这个目录）
"""
import argparse
import datetime as dt
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYTHON_VERSION = "3.12.10"  # nuget.org 上 "python" 包的版本
PY_TAG = "312"
NUGET_URL = f"https://api.nuget.org/v3-flatcontainer/python/{PYTHON_VERSION}/python.{PYTHON_VERSION}.nupkg"

APP_ITEMS = [
    "run.py", "main.py", "flow.py", "nodes.py", "exec_cases.py", "schemas.py",
    "requirements.txt", "pocketflow", "utils", "prompts", "static",
]
# 内置 Python 里用不到的部分，删掉以减小体积
PY_PRUNE = [
    "include", "libs", "Lib/test", "Lib/idlelib", "Lib/tkinter", "Lib/turtledemo",
    "Lib/lib2to3", "Lib/ensurepip", "Lib/venv",
]


def log(msg: str):
    print(f"[build] {msg}", flush=True)


def fetch_python(cache: Path) -> Path:
    cache.mkdir(parents=True, exist_ok=True)
    pkg = cache / f"python.{PYTHON_VERSION}.nupkg"
    if not pkg.exists():
        log(f"下载 Windows Python {PYTHON_VERSION}: {NUGET_URL}")
        with urllib.request.urlopen(NUGET_URL, timeout=300) as resp:
            pkg.write_bytes(resp.read())
    return pkg


def extract_python(pkg: Path, dest: Path):
    with zipfile.ZipFile(pkg) as zf:
        for info in zf.infolist():
            if not info.filename.startswith("tools/") or info.is_dir():
                continue
            rel = info.filename[len("tools/"):]
            if any(rel == p or rel.startswith(p + "/") for p in PY_PRUNE) or "/__pycache__/" in rel:
                continue
            target = dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as out:
                shutil.copyfileobj(src, out)


def install_deps(site_packages: Path):
    log("安装依赖（win_amd64 wheel）")
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "--no-compile",
        "--target", str(site_packages),
        "--platform", "win_amd64", "--python-version", PY_TAG, "--implementation", "cp",
        "--only-binary=:all:", "--upgrade",
        "-r", str(ROOT / "requirements.txt"),
    ])
    # pip --target 生成的 bin/ 是当前系统的脚本，Windows 上用不到
    shutil.rmtree(site_packages / "bin", ignore_errors=True)


def copy_app(dest: Path):
    dest.mkdir(parents=True, exist_ok=True)
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store")
    for item in APP_ITEMS:
        src = ROOT / item
        if src.is_dir():
            shutil.copytree(src, dest / item, ignore=ignore)
        else:
            shutil.copy2(src, dest / item)


def crlf(text: str) -> bytes:
    return text.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8")


def write_readme(dest: Path, version: str):
    text = (ROOT / "packaging" / "windows" / "使用说明.txt").read_text(encoding="utf-8")
    text = text.replace("{version}", version)
    # 带 BOM，记事本打开不会乱码
    (dest / "使用说明.txt").write_bytes(b"\xef\xbb\xbf" + crlf(text))


def zip_dir(src: Path, zip_path: Path):
    log(f"压缩 {zip_path.name}")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for p in sorted(src.rglob("*")):
            arc = Path(src.name) / p.relative_to(src)
            if p.is_dir():
                zf.write(p, arc.as_posix() + "/")
            else:
                zf.write(p, arc.as_posix())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default=dt.date.today().strftime("%Y.%m.%d"))
    parser.add_argument("--out", default=str(ROOT / "release"))
    parser.add_argument("--cache", default=str(ROOT / "release" / ".cache"))
    parser.add_argument("--no-zip", action="store_true")
    args = parser.parse_args()

    out = Path(args.out).resolve()
    name = f"TestFlow-{args.version}-win64"
    stage = out / name
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)

    pkg = fetch_python(Path(args.cache))
    log("解压内置 Python")
    extract_python(pkg, stage / "python")
    install_deps(stage / "python" / "Lib" / "site-packages")

    log("复制程序代码")
    copy_app(stage / "app")
    (stage / "app" / "VERSION").write_text(args.version, encoding="utf-8")
    (stage / "data").mkdir()
    (stage / "start.bat").write_bytes(crlf((ROOT / "start.bat").read_text(encoding="utf-8")))
    write_readme(stage, args.version)

    if not args.no_zip:
        zip_path = out / f"{name}.zip"
        zip_dir(stage, zip_path)
        log(f"完成: {zip_path} ({zip_path.stat().st_size / 1024 / 1024:.1f} MB)")
    else:
        log(f"完成: {stage}")


if __name__ == "__main__":
    main()
