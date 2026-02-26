import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


def _now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z0-9_]+|[\u4e00-\u9fff]+", (text or "").lower())


class SimpleRAGStore:
    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.docs_dir = self.base_dir / "docs"
        self.manifest_path = self.base_dir / "manifest.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        self.manifest: Dict[str, Any] = {"docs": []}
        self.docs_cache: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if self.manifest_path.exists():
            try:
                self.manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            except Exception:
                self.manifest = {"docs": []}
        for meta in self.manifest.get("docs", []):
            doc_id = meta.get("doc_id")
            if not doc_id:
                continue
            p = self.docs_dir / f"{doc_id}.json"
            if not p.exists():
                continue
            try:
                self.docs_cache[doc_id] = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue

    def _save_manifest(self) -> None:
        self.manifest_path.write_text(
            json.dumps(self.manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _extract_text(self, filename: str, content: bytes) -> str:
        ext = Path(filename).suffix.lower()
        if ext in {".txt", ".md", ".csv", ".json", ".log", ".yaml", ".yml", ".xml"}:
            return content.decode("utf-8", errors="ignore")
        if ext == ".pdf":
            try:
                from pypdf import PdfReader  # type: ignore
            except Exception as exc:
                raise ValueError(f"PDF解析依赖缺失（pypdf）: {exc}")
            from io import BytesIO

            reader = PdfReader(BytesIO(content))
            return "\n".join([(p.extract_text() or "") for p in reader.pages])
        raise ValueError(f"暂不支持的文档类型: {ext}（支持 txt/md/csv/json/log/yaml/xml/pdf）")

    def _chunk(self, text: str, chunk_size: int = 1000, overlap: int = 120) -> List[str]:
        normalized = re.sub(r"\s+", " ", text or "").strip()
        if not normalized:
            return []
        chunks: List[str] = []
        i = 0
        n = len(normalized)
        while i < n:
            j = min(i + chunk_size, n)
            chunks.append(normalized[i:j])
            if j >= n:
                break
            i = max(j - overlap, i + 1)
        return chunks

    def ingest_file(self, filename: str, content: bytes) -> Dict[str, Any]:
        text = self._extract_text(filename, content)
        chunks = self._chunk(text)
        if not chunks:
            raise ValueError("文档无可用文本内容")

        doc_id = f"DOC-{uuid.uuid4().hex[:12]}"
        payload = {
            "doc_id": doc_id,
            "filename": filename,
            "created_at": _now_iso(),
            "chunks": [{"chunk_id": f"{doc_id}-C{i+1:03d}", "text": c} for i, c in enumerate(chunks)],
        }
        (self.docs_dir / f"{doc_id}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        meta = {
            "doc_id": doc_id,
            "filename": filename,
            "created_at": payload["created_at"],
            "chunk_count": len(chunks),
        }
        self.manifest.setdefault("docs", []).append(meta)
        self.docs_cache[doc_id] = payload
        self._save_manifest()
        return meta

    def list_docs(self) -> List[Dict[str, Any]]:
        docs = self.manifest.get("docs", [])
        return sorted(docs, key=lambda x: x.get("created_at", ""), reverse=True)

    def retrieve(self, query: str, top_k: int = 6) -> List[Dict[str, Any]]:
        q_terms = set(_tokenize(query))
        if not q_terms:
            return []
        hits: List[Dict[str, Any]] = []
        for meta in self.list_docs():
            doc = self.docs_cache.get(meta["doc_id"])
            if not doc:
                continue
            for ch in doc.get("chunks", []):
                terms = set(_tokenize(ch.get("text", "")))
                if not terms:
                    continue
                overlap = q_terms & terms
                if not overlap:
                    continue
                score = len(overlap) / max(1, len(q_terms))
                hits.append(
                    {
                        "doc_id": meta["doc_id"],
                        "filename": meta.get("filename", ""),
                        "chunk_id": ch.get("chunk_id"),
                        "score": round(score, 4),
                        "text": ch.get("text", ""),
                    }
                )
        hits.sort(key=lambda x: x["score"], reverse=True)
        return hits[: max(1, top_k)]
