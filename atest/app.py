import importlib.util
import json
import os
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT_DIR = Path(__file__).resolve().parents[1]
ATEST_DIR = Path(__file__).resolve().parent
WEB_DIR = ROOT_DIR / "cookbook" / "pocketflow-system-test-agent-web"
WEB_MAIN_PATH = WEB_DIR / "main.py"
STATIC_DIR = Path(__file__).resolve().parent / "static"
DATA_DIR = ATEST_DIR / "data"


def _load_atest_env() -> None:
    env_path = ATEST_DIR / ".env"
    if not env_path.exists():
        return
    parsed: Dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        k, v = raw.split("=", 1)
        key = k.strip()
        val = v.strip().strip('"').strip("'")
        if key:
            parsed[key] = val
    # ATest-specific namespace has higher priority inside this process.
    if parsed.get("ATEST_LLM_API_BASE"):
        os.environ["LLM_API_BASE"] = parsed["ATEST_LLM_API_BASE"]
    if parsed.get("ATEST_LLM_API_KEY"):
        os.environ["LLM_API_KEY"] = parsed["ATEST_LLM_API_KEY"]
    if parsed.get("ATEST_LLM_MODEL"):
        os.environ["LLM_MODEL"] = parsed["ATEST_LLM_MODEL"]
    # Fallback to shared names if ATEST_ names not provided.
    if parsed.get("LLM_API_BASE") and not os.environ.get("LLM_API_BASE"):
        os.environ["LLM_API_BASE"] = parsed["LLM_API_BASE"]
    if parsed.get("LLM_API_KEY") and not os.environ.get("LLM_API_KEY"):
        os.environ["LLM_API_KEY"] = parsed["LLM_API_KEY"]
    if parsed.get("LLM_MODEL") and not os.environ.get("LLM_MODEL"):
        os.environ["LLM_MODEL"] = parsed["LLM_MODEL"]


def _ensure_atest_data_layout() -> None:
    src_root = WEB_DIR / "at_agent"
    mapping = {
        "specs/3gpp_base_atspec.v0.json": src_root / "specs" / "3gpp_base_atspec.v0.json",
        "profiles/generic_3gpp.profile.v0.json": src_root / "profiles" / "generic_3gpp.profile.v0.json",
        "models/3gpp_base.efsm.json": src_root / "models" / "3gpp_base.efsm.json",
        "manifests/default.manifest.json": src_root / "manifests" / "default.manifest.json",
        "extensions/vendor.extension.json": src_root / "extensions" / "vendor.extension.json",
    }
    for rel, src in mapping.items():
        dst = DATA_DIR / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists():
            shutil.copy2(src, dst)
    (DATA_DIR / "build").mkdir(parents=True, exist_ok=True)

if str(WEB_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_DIR))
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def _load_pf_main():
    spec = importlib.util.spec_from_file_location("pf_web_main", str(WEB_MAIN_PATH))
    if not spec or not spec.loader:
        raise RuntimeError(f"cannot load module from {WEB_MAIN_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_load_atest_env()
DATA_DIR = Path(os.getenv("ATEST_DATA_DIR", str(ATEST_DIR / "data")))
pf = _load_pf_main()
_ensure_atest_data_layout()

# Rebind AT asset paths to atest-local data directory for full runtime isolation.
pf.at_agent_dir = DATA_DIR
pf.at_specs_dir = DATA_DIR / "specs"
pf.at_profiles_dir = DATA_DIR / "profiles"
pf.at_models_dir = DATA_DIR / "models"
pf.at_manifests_dir = DATA_DIR / "manifests"
pf.at_extensions_dir = DATA_DIR / "extensions"
pf.at_build_dir = DATA_DIR / "build"
pf.at_spec_path = pf.at_specs_dir / "3gpp_base_atspec.v0.json"
pf.at_profile_path = pf.at_profiles_dir / "generic_3gpp.profile.v0.json"
pf.at_efsm_path = pf.at_models_dir / "3gpp_base.efsm.json"
pf.at_manifest_path = pf.at_manifests_dir / "default.manifest.json"
pf.at_extension_path = pf.at_extensions_dir / "vendor.extension.json"
pf.at_effective_atspec_path = pf.at_build_dir / "effective_atspec.json"
pf.at_effective_profile_path = pf.at_build_dir / "effective_profile.json"
pf.at_active_efsm_path = pf.at_build_dir / "active_efsm.json"
pf.at_compile_report_path = pf.at_build_dir / "compile_report.json"


class AtestLLMClient:
    def __init__(self):
        # Strictly use current process env (populated by atest/.env), no fallback to testflow .env.
        self.api_base = os.getenv("LLM_API_BASE", "").rstrip("/")
        self.api_key = os.getenv("LLM_API_KEY", "")
        self.model = os.getenv("LLM_MODEL", "")

    @property
    def enabled(self) -> bool:
        return bool(self.api_base and self.api_key and self.model)

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
    ) -> str:
        if not self.enabled:
            raise RuntimeError("ATest LLM config missing. Set ATEST_LLM_API_BASE/KEY/MODEL in atest/.env.")

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        req = urllib.request.Request(
            url=f"{self.api_base}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"ATest LLM HTTP error: {exc.code} {details}") from exc
        except Exception as exc:
            raise RuntimeError(f"ATest LLM request failed: {exc}") from exc

        try:
            return body["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            raise RuntimeError(f"ATest LLM response parse failed: {body}") from exc


# Override imported module client so compile/config-compile use isolated atest LLM config.
pf.LLMClient = AtestLLMClient


class AtAssetSaveRequest(BaseModel):
    data: Dict[str, Any]
    locked_baseline: bool = False


class AtCompileRequest(BaseModel):
    use_llm: bool = True


class AtConfigCompileRequest(BaseModel):
    request_text: str = Field(..., min_length=1)
    use_llm: bool = True
    apply_changes: bool = True
    compile_after_apply: bool = True


class AutomationRequest(BaseModel):
    mode: str = Field(..., description="android_adb | at_serial")
    device_id: str = ""
    at_port: str = ""
    baudrate: int = 115200
    test_case_spec: Optional[Dict[str, Any]] = None
    script_spec: Optional[Dict[str, Any]] = None
    max_cases: int = 5
    max_steps: int = 20


app = FastAPI(title="ATest Agent")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/healthz")
def healthz():
    return {"ok": True, "app": "atest"}


@app.get("/api/at-agent/spec")
def at_agent_get_spec():
    return pf._load_json_file(pf.at_spec_path)


@app.post("/api/at-agent/spec")
def at_agent_save_spec(payload: AtAssetSaveRequest):
    if payload.locked_baseline:
        existing = pf._load_json_file(pf.at_spec_path)
        if existing:
            merged = pf._merge_atspec(existing, payload.data)
            if existing.get("meta"):
                merged.setdefault("meta", {})
                merged["meta"]["id"] = existing.get("meta", {}).get("id", merged.get("meta", {}).get("id"))
            pf.at_spec_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
            return {"saved": True, "path": str(pf.at_spec_path), "mode": "merge_locked"}
    pf.at_spec_path.write_text(json.dumps(payload.data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"saved": True, "path": str(pf.at_spec_path)}


@app.get("/api/at-agent/profile")
def at_agent_get_profile():
    return pf._load_json_file(pf.at_profile_path)


@app.post("/api/at-agent/profile")
def at_agent_save_profile(payload: AtAssetSaveRequest):
    pf.at_profile_path.write_text(json.dumps(payload.data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"saved": True, "path": str(pf.at_profile_path)}


@app.get("/api/at-agent/manifest")
def at_agent_get_manifest():
    return pf._load_json_file(pf.at_manifest_path)


@app.post("/api/at-agent/manifest")
def at_agent_save_manifest(payload: AtAssetSaveRequest):
    pf.at_manifest_path.write_text(json.dumps(payload.data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"saved": True, "path": str(pf.at_manifest_path)}


@app.get("/api/at-agent/extension")
def at_agent_get_extension():
    return pf._load_json_file(pf.at_extension_path)


@app.post("/api/at-agent/extension")
def at_agent_save_extension(payload: AtAssetSaveRequest):
    pf.at_extension_path.write_text(json.dumps(payload.data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"saved": True, "path": str(pf.at_extension_path)}


@app.get("/api/at-agent/efsm")
def at_agent_get_efsm():
    return pf._load_json_file(pf.at_efsm_path)


@app.post("/api/at-agent/efsm")
def at_agent_save_efsm(payload: AtAssetSaveRequest):
    pf.at_efsm_path.write_text(json.dumps(payload.data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"saved": True, "path": str(pf.at_efsm_path)}


@app.post("/api/at-agent/compile")
def at_agent_compile(payload: AtCompileRequest):
    try:
        return pf._compile_at_assets(use_llm=payload.use_llm)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"AT编译失败: {exc}")


@app.post("/api/at-agent/config-compile")
def at_agent_config_compile(payload: AtConfigCompileRequest):
    try:
        result = pf._generate_config_updates_with_retry(
            request_text=payload.request_text.strip(),
            use_llm=payload.use_llm,
            max_attempts=3,
        )
        manifest_new = result["manifest_new"]
        extension_new = result["extension_new"]

        if payload.apply_changes:
            pf.at_manifest_path.write_text(json.dumps(manifest_new, ensure_ascii=False, indent=2), encoding="utf-8")
            pf.at_extension_path.write_text(json.dumps(extension_new, ensure_ascii=False, indent=2), encoding="utf-8")

        compiled: Dict[str, Any] = {}
        if payload.apply_changes and payload.compile_after_apply:
            compiled = pf._compile_at_assets(use_llm=payload.use_llm)

        return {
            "applied": bool(payload.apply_changes),
            "compiled": bool(payload.apply_changes and payload.compile_after_apply),
            "change_spec": result.get("change_spec", {}),
            "manifest_patch": result.get("manifest_patch", []),
            "extension_mode": result.get("extension_mode", "replace"),
            "extension_patch": result.get("extension_patch", []),
            "manifest": manifest_new,
            "extension": extension_new,
            "retries_used": result.get("attempts", 1),
            "compile_result": compiled,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"AT配置编译失败: {exc}")


@app.post("/api/at-agent/reset-baseline")
def at_agent_reset_baseline():
    try:
        pf.at_manifest_path.write_text(json.dumps(pf.ATMANIFEST_DEFAULT, ensure_ascii=False, indent=2), encoding="utf-8")
        pf.at_extension_path.write_text(json.dumps(pf.ATEXTENSION_DEFAULT, ensure_ascii=False, indent=2), encoding="utf-8")
        compiled = pf._compile_at_assets(use_llm=False)
        return {
            "reset": True,
            "manifest": pf._load_json_file(pf.at_manifest_path),
            "extension": pf._load_json_file(pf.at_extension_path),
            "compile_result": compiled,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"AT基线重置失败: {exc}")


@app.get("/api/at-agent/build")
def at_agent_build_get():
    return {
        "effective_atspec": pf._load_json_file(pf.at_effective_atspec_path),
        "effective_profile": pf._load_json_file(pf.at_effective_profile_path),
        "active_efsm": pf._load_json_file(pf.at_active_efsm_path),
        "report": pf._load_json_file(pf.at_compile_report_path),
    }


@app.post("/api/at-agent/mbt/run")
def at_agent_mbt_run(payload: AutomationRequest):
    try:
        p = pf.AutomationRequest(**payload.model_dump())
        return pf.at_agent_mbt_run(p)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"AT MBT执行失败: {exc}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8011)
