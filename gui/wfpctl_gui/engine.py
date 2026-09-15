from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from wfpctl_gui.i18n import tr


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
            raise RuntimeError(tr("timeout_msg").format(cmd=f"wfpctl {' '.join(args)}")) from exc
        except Exception as exc:
            raise RuntimeError(tr("exec_fail_msg").format(err=exc)) from exc

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

    def list_rules(self, show_all: bool = False, sublayer: str = "") -> list[dict[str, Any]]:
        try:
            args = ["list", "-json"]
            if show_all:
                args.append("-all")
            if sublayer:
                args += ["-sublayer", sublayer]
            r = self.cmd(*args)
            if r.returncode != 0:
                return []
            text = r.stdout.strip()
            if not text:
                return []
            data = json.loads(text)
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def list_sublayers(self) -> list[dict[str, Any]]:
        try:
            r = self.cmd("sublayers", "-json")
            if r.returncode != 0:
                return []
            text = r.stdout.strip()
            if not text:
                return []
            data = json.loads(text)
            return data if isinstance(data, list) else []
        except Exception:
            return []

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
                raise RuntimeError(output.strip() or tr("exit_code").format(rc=r.returncode))
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
            return ok, output.strip() if ok else output.strip() or tr("exit_code").format(rc=r.returncode)
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
            return ok, output.strip() if ok else output.strip() or tr("exit_code").format(rc=r.returncode)
        except Exception as exc:
            return False, str(exc)

    RULE_FIELDS = ("name", "target", "port", "protocol", "direction", "action")

    @classmethod
    def _signature(cls, rule: dict[str, Any]) -> tuple[str, ...]:
        return tuple(str(rule.get(k, "") or "") for k in cls.RULE_FIELDS)

    def export_rules(self, path: str) -> int:
        rules = self.list_rules()
        doc = {
            "format": "wfpctl-rules",
            "version": 1,
            "rules": [
                {
                    "name": r.get("name", ""),
                    "target": r.get("target", ""),
                    "port": r.get("port", ""),
                    "protocol": r.get("protocol", ""),
                    "direction": r.get("direction", ""),
                    "action": r.get("action", ""),
                    "weight": r.get("weight", "auto"),
                }
                for r in rules
            ],
        }
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=2)
        return len(doc["rules"])

    def import_rules(self, path: str) -> dict[str, int]:
        with open(path, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
        if not isinstance(doc, dict) or doc.get("format") != "wfpctl-rules":
            raise ValueError(tr("not_rules_file"))
        rules = doc.get("rules")
        if not isinstance(rules, list):
            raise ValueError(tr("missing_rules_list"))

        existing = {self._signature(r) for r in self.list_rules()}

        added = 0
        skipped = 0
        failed = 0
        errors: list[str] = []

        for i, r in enumerate(rules, 1):
            if not isinstance(r, dict):
                failed += 1
                errors.append(tr("invalid_record").format(i=i))
                continue
            sig = self._signature(r)
            if sig in existing:
                skipped += 1
                continue
            try:
                priority = "highest"
                weight = 0
                weight_s = str(r.get("weight", "auto") or "auto")
                if weight_s not in ("auto", ""):
                    weight = int(weight_s)
                    if weight == 2**64 - 1:
                        priority = "highest"
                        weight = 0
                    elif weight == 1:
                        priority = "lowest"
                        weight = 0
                    else:
                        priority = "custom"
                self.add_rule(
                    name=str(r.get("name", "") or "wfpctl-rule"),
                    target=str(r.get("target", "") or ""),
                    port=str(r.get("port", "") or ""),
                    protocol=str(r.get("protocol", "") or ""),
                    direction=str(r.get("direction", "") or "out"),
                    action=str(r.get("action", "") or "block"),
                    priority=priority,
                    weight=weight,
                )
                added += 1
                existing.add(sig)
            except Exception as exc:
                failed += 1
                errors.append(tr("record_error").format(i=i, msg=exc))

        result: dict[str, int] = {"added": added, "skipped": skipped, "failed": failed}
        if errors:
            result["errors"] = "\n".join(errors)
        return result
