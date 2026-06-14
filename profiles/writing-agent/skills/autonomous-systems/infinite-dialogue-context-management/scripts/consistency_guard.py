#!/usr/bin/env python3
"""
Hermes 一致性守卫 — 每5轮自检文件/cron/齿轮/上下文系统
用法: python3 scripts/consistency_guard.py
集成: 注入gear_enforcer.py每轮循环中自动调用
"""
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

HERMES = Path(os.path.expanduser("~/.hermes"))
CHECKPOINT = HERMES / "reports" / "consistency_checkpoint.json"

class ConsistencyGuard:
    def __init__(self):
        self.last_check = self._load()
        self.anomalies = []

    def _load(self) -> dict:
        if CHECKPOINT.exists():
            try: return json.loads(CHECKPOINT.read_text())
            except: pass
        return {"last_check_turn": 0, "checks_passed": 0, "checks_failed": 0}

    def _save(self):
        CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
        CHECKPOINT.write_text(json.dumps(self.last_check, indent=2))

    def check(self, current_turn: int) -> list:
        if current_turn - self.last_check["last_check_turn"] < 5:
            return []
        self.anomalies = []
        # 1. 文件完整性
        critical = ["scripts/context_packer.py", "scripts/surgical_context_slicer.py",
                    "scripts/context_auto_assoc.py", "scripts/context_index_system.py",
                    "scripts/cross_session_cache.py", "scripts/context_reconstructor.py",
                    "scripts/segment_manager.py", "scripts/hermes_retrospect.py", "SOUL.md"]
        for rel in critical:
            p = HERMES / rel
            if not p.exists():
                self.anomalies.append(f"文件丢失: {rel}")
            elif p.stat().st_size < 100 and rel.endswith(".py"):
                self.anomalies.append(f"文件异常小: {rel}")
        # 2. cron完整性
        cron_out = subprocess.run(["crontab","-l"], capture_output=True, text=True).stdout
        for rc in ["context_packer", "surgical_context", "context_auto_assoc", "context_index_system", "cross_session_cache"]:
            if rc not in cron_out:
                self.anomalies.append(f"cron丢失: {rc}")
        # 3. 齿轮健康
        wg = HERMES / "reports" / "wake_guide.json"
        if wg.exists():
            try:
                d = json.loads(wg.read_text())
                if d.get("gear_health") != "healthy":
                    self.anomalies.append(f"齿轮不健康: {d.get('gear_health')}")
            except: self.anomalies.append("wake_guide读取失败")
        # 4. 上下文输出新鲜度(x不需要最新，只要有内容)
        idx = HERMES / "reports" / "context_index.json"
        if idx.exists():
            try:
                d = json.loads(idx.read_text())
                if len(d.get("sections", [])) == 0:
                    self.anomalies.append("context_index sections为空")
            except: self.anomalies.append("context_index损坏")
        self.last_check["last_check_turn"] = current_turn
        if self.anomalies: self.last_check["checks_failed"] += 1
        else: self.last_check["checks_passed"] += 1
        self._save()
        if self.anomalies:
            log = HERMES / "reports" / "consistency_anomalies.log"
            with open(log, "a") as f:
                f.write(f"[{datetime.now().isoformat()}] {len(self.anomalies)} anomalies\n")
                for a in self.anomalies: f.write(f"  {a}\n")
        return self.anomalies

if __name__ == "__main__":
    g = ConsistencyGuard()
    a = g.check(10)
    if a:
        print(f"❌ {len(a)} anomalies:\n" + "\n".join(a))
    else:
        print("✅ all clear")
