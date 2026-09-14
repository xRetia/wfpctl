from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


class Engine:
    def __init__(self) -> None:
        self._exe = self._find_exe()

    @staticmethod
    def _find_exe() -> str | None:
        if getattr(sys, "frozen", False):
            base = Path(sys.executable).parent
        else:
            base = Path(__file__).resolve().parent

        project_root = base.parent

        candidates = [
            base / "wfpctl.exe",
            base / "wfpctl64.exe",
            base / "wfpctl32.exe",
            project_root / "wfpctl.exe",
            project_root / "wfpctl64.exe",
            project_root / "wfpctl32.exe",
            project_root / "wfpctl-windows-amd64.exe",
        ]
        for c in candidates:
            if c.is_file():
                return str(c)

        path = shutil.which("wfpctl")
        if path:
            return path

        return None

    @property
    def available(self) -> bool:
        return self._exe is not None

    @property
    def exe_path(self) -> str:
        return self._exe or ""

    def cmd(self, *args: str) -> subprocess.CompletedProcess[str]:
        if not self._exe:
            raise FileNotFoundError("wfpctl executable not found")
        try:
            return subprocess.run(
                [self._exe, *args],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"命令超时: wfpctl {' '.join(args)}") from exc
        except Exception as exc:
            raise RuntimeError(f"执行失败: {exc}") from exc

    def version(self) -> str:
        try:
            r = self.cmd("version")
            out = r.stdout.strip() or r.stderr.strip()
            if out:
                first = out.splitlines()[0].strip()
                if first.startswith("wfpctl"):
                    parts = first.split(None, 1)
                    if len(parts) == 2:
                        return parts[1]
            return out or "unknown"
        except Exception:
            return "unknown"

    def list_rules(self) -> list[dict[str, Any]]:
        try:
            r = self.cmd("list", "-json")
            if r.returncode != 0:
                return []
            text = r.stdout.strip()
            if not text:
                return []
            data = json.loads(text)
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def list_sublayers(self) -> str:
        try:
            r = self.cmd("sublayers")
            if r.returncode == 0:
                return r.stdout.strip() or r.stderr.strip()
            return r.stderr.strip() or r.stdout.strip() or "无输出"
        except Exception as exc:
            return f"错误: {exc}"

    def add_rule(
        self,
        name: str,
        target: str,
        port: str,
        protocol: str,
        direction: str,
        action: str,
        priority: str,
        weight: int,
    ) -> str:
        args = ["add"]
        args += ["-name", name]
        args += ["-target", target]
        if port:
            args += ["-port", port]
        if protocol:
            args += ["-protocol", protocol]
        args += ["-direction", direction]
        args += ["-action", action]
        if priority == "custom":
            args += ["-priority", "custom", "-weight", str(weight)]
        else:
            args += ["-priority", priority]
        try:
            r = self.cmd(*args)
            output = (r.stdout or "") + (r.stderr or "")
            if r.returncode != 0:
                raise RuntimeError(output.strip() or f"退出码 {r.returncode}")
            return output.strip()
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(str(exc))

    def delete_rule(self, key: str) -> tuple[bool, str]:
        try:
            r = self.cmd("delete", "-key", key)
            output = (r.stdout or "") + (r.stderr or "")
            ok = r.returncode == 0
            return ok, output.strip() if ok else output.strip() or f"退出码 {r.returncode}"
        except Exception as exc:
            return False, str(exc)

    def delete_sublayer(self, key: str) -> tuple[bool, str]:
        try:
            args = ["sublayers", "-delete"]
            if key:
                args += ["-key", key]
            r = self.cmd(*args)
            output = (r.stdout or "") + (r.stderr or "")
            ok = r.returncode == 0
            return ok, output.strip() if ok else output.strip() or f"退出码 {r.returncode}"
        except Exception as exc:
            return False, str(exc)
