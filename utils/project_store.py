"""项目 / Product 管理。

每个测试设计归属一个项目（Product）。项目保存默认的产品通信特性、可用测试环境，
并拥有自己的资料库（项目资料 RAG），测试设计时只检索当前项目资料 + 公共资料。

存储结构（都在数据目录下，升级时随 data\\ 一起拷走）：
    projects/projects.json            项目列表
    projects/<project_id>/rag_data/   项目资料库（与公共资料同格式）
"""
import json
import re
import shutil
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.rag_store import SimpleRAGStore

DEFAULT_PROJECT_ID = "default"
DEFAULT_PROJECT_NAME = "默认项目"
_PROJECT_ID_RE = re.compile(r"^(default|P-[0-9a-f]{10})$")


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def valid_project_id(project_id: str) -> bool:
    return bool(_PROJECT_ID_RE.match(str(project_id or "")))


class ProjectStore:
    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.base_dir / "projects.json"
        self._lock = threading.Lock()
        self._rag_stores: Dict[str, SimpleRAGStore] = {}
        self._projects: List[Dict[str, Any]] = []
        self._load()
        if not self.get(DEFAULT_PROJECT_ID):
            now = _now()
            self._projects.insert(0, {
                "project_id": DEFAULT_PROJECT_ID,
                "name": DEFAULT_PROJECT_NAME,
                "code": "",
                "description": "未指定项目的测试设计（包括升级前的历史记录）都归在这里。",
                "product_profile_selected": {},
                "test_environment_ids": [],
                "created_at": now,
                "updated_at": now,
            })
            self._save()

    # ---- 持久化 ----
    def _load(self) -> None:
        if not self.index_path.exists():
            return
        try:
            data = json.loads(self.index_path.read_text(encoding="utf-8"))
            items = data.get("projects", []) if isinstance(data, dict) else []
            self._projects = [p for p in items if isinstance(p, dict) and valid_project_id(p.get("project_id", ""))]
        except Exception:
            self._projects = []

    def _save(self) -> None:
        tmp = self.index_path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"projects": self._projects}, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.index_path)

    # ---- 查询 ----
    def list(self) -> List[Dict[str, Any]]:
        return [dict(p) for p in self._projects]

    def get(self, project_id: str) -> Optional[Dict[str, Any]]:
        for p in self._projects:
            if p.get("project_id") == project_id:
                return dict(p)
        return None

    def resolve_id(self, project_id: str) -> str:
        """未知或为空的项目统一落到默认项目，保证每条测试设计都有归属。"""
        pid = str(project_id or "").strip()
        return pid if pid and self.get(pid) else DEFAULT_PROJECT_ID

    def name_of(self, project_id: str) -> str:
        p = self.get(self.resolve_id(project_id))
        return (p or {}).get("name", DEFAULT_PROJECT_NAME)

    # ---- 增删改 ----
    @staticmethod
    def _clean_fields(fields: Dict[str, Any]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        if "name" in fields and fields["name"] is not None:
            out["name"] = str(fields["name"]).strip()[:80]
        if "code" in fields and fields["code"] is not None:
            out["code"] = str(fields["code"]).strip()[:40]
        if "description" in fields and fields["description"] is not None:
            out["description"] = str(fields["description"]).strip()[:2000]
        if "product_profile_selected" in fields and isinstance(fields["product_profile_selected"], dict):
            out["product_profile_selected"] = {
                str(k): [str(v) for v in vals] for k, vals in fields["product_profile_selected"].items() if isinstance(vals, list)
            }
        if "test_environment_ids" in fields and isinstance(fields["test_environment_ids"], list):
            out["test_environment_ids"] = [str(x) for x in fields["test_environment_ids"]]
        return out

    def _name_taken(self, name: str, exclude_id: str = "") -> bool:
        key = name.strip().lower()
        return any(p.get("name", "").strip().lower() == key and p.get("project_id") != exclude_id for p in self._projects)

    def create(self, fields: Dict[str, Any]) -> Dict[str, Any]:
        data = self._clean_fields(fields)
        if not data.get("name"):
            raise ValueError("项目名称不能为空")
        with self._lock:
            if self._name_taken(data["name"]):
                raise ValueError(f"项目名称已存在: {data['name']}")
            now = _now()
            project = {
                "project_id": f"P-{uuid.uuid4().hex[:10]}",
                "name": data["name"],
                "code": data.get("code", ""),
                "description": data.get("description", ""),
                "product_profile_selected": data.get("product_profile_selected", {}),
                "test_environment_ids": data.get("test_environment_ids", []),
                "created_at": now,
                "updated_at": now,
            }
            self._projects.append(project)
            self._save()
            return dict(project)

    def update(self, project_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
        data = self._clean_fields(fields)
        if "name" in data and not data["name"]:
            raise ValueError("项目名称不能为空")
        with self._lock:
            for p in self._projects:
                if p.get("project_id") != project_id:
                    continue
                if "name" in data and self._name_taken(data["name"], exclude_id=project_id):
                    raise ValueError(f"项目名称已存在: {data['name']}")
                p.update(data)
                p["updated_at"] = _now()
                self._save()
                return dict(p)
        raise KeyError(project_id)

    def delete(self, project_id: str) -> None:
        if project_id == DEFAULT_PROJECT_ID:
            raise ValueError("默认项目不能删除")
        with self._lock:
            before = len(self._projects)
            self._projects = [p for p in self._projects if p.get("project_id") != project_id]
            if len(self._projects) == before:
                raise KeyError(project_id)
            self._save()
            self._rag_stores.pop(project_id, None)
            project_dir = self.base_dir / project_id
            if valid_project_id(project_id) and project_dir.is_dir():
                shutil.rmtree(project_dir, ignore_errors=True)

    # ---- 项目资料 ----
    def rag_store(self, project_id: str) -> SimpleRAGStore:
        pid = self.resolve_id(project_id)
        store = self._rag_stores.get(pid)
        if store is None:
            store = SimpleRAGStore(self.base_dir / pid / "rag_data")
            self._rag_stores[pid] = store
        return store
