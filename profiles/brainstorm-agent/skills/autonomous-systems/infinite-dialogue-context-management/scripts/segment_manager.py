#!/usr/bin/env python3
"""
Hermes 段管理器 — 每50轮自动归档切换
用法: python3 scripts/segment_manager.py [stats|test|reset]
集成: 注入gear_enforcer.py自动每1分钟检查段切换条件
"""
import json
import os
import time
from datetime import datetime
from pathlib import Path

HERMES = Path(os.path.expanduser("~/.hermes"))
MAX_TURNS_PER_SEGMENT = 50

class SegmentManager:
    def __init__(self):
        self.state_file = HERMES / "reports" / "segment_state.json"
        self.handoff_dir = HERMES / "reports" / "handoff_notes"
        self.handoff_dir.mkdir(parents=True, exist_ok=True)
        self.state = self._load_state()

    def _load_state(self) -> dict:
        if self.state_file.exists():
            try: return json.loads(self.state_file.read_text())
            except: pass
        return {"segment_id": 0, "turn_in_segment": 0, "max_turns_per_segment": MAX_TURNS_PER_SEGMENT,
                "total_turns_all": 0, "created_at": datetime.now().isoformat(),
                "tasks_completed_in_segment": [], "key_decisions": []}

    def _save_state(self):
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(self.state, indent=2, ensure_ascii=False))

    def advance_turn(self, action_summary="", decision="") -> str:
        self.state["turn_in_segment"] += 1
        self.state["total_turns_all"] += 1
        if action_summary:
            self.state["tasks_completed_in_segment"].append(
                {"turn": self.state["turn_in_segment"], "summary": action_summary[:200], "ts": datetime.now().isoformat()})
        if decision:
            self.state["key_decisions"].append(
                {"turn": self.state["turn_in_segment"], "decision": decision[:200], "ts": datetime.now().isoformat()})
        self._save_state()
        if self.state["turn_in_segment"] >= MAX_TURNS_PER_SEGMENT:
            return self._rotate()
        return ""

    def _rotate(self) -> str:
        old = self.state["segment_id"]; new = old + 1
        handoff = f"# 段{old}交接笔记 (轮次{self.state['total_turns_all'] - len(self.state['tasks_completed_in_segment']) + 1}-{self.state['total_turns_all']})\n\n## 完成的任务\n"
        for t in self.state["tasks_completed_in_segment"][-10:]:
            handoff += f"- 第{t['turn']}轮: {t['summary']}\n"
        if self.state["key_decisions"]:
            handoff += "\n## 关键决策\n"
            for d in self.state["key_decisions"][-5:]:
                handoff += f"- 第{d['turn']}轮: {d['decision']}\n"
        fname = f"handoff_s{old}_to_s{new}_{int(time.time())}.md"
        (self.handoff_dir / fname).write_text(handoff)
        self.state["segment_id"] = new; self.state["turn_in_segment"] = 0
        self.state["tasks_completed_in_segment"] = []; self.state["key_decisions"] = []
        self._save_state()
        return handoff

    def get_stats(self) -> dict:
        return {"current_segment": self.state["segment_id"], "turns_in_segment": self.state["turn_in_segment"],
                "max_turns_per_segment": MAX_TURNS_PER_SEGMENT, "total_turns_all": self.state["total_turns_all"],
                "tasks_in_segment": len(self.state["tasks_completed_in_segment"]),
                "decisions_in_segment": len(self.state["key_decisions"])}

if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stats"
    sm = SegmentManager()
    if cmd == "stats":
        print(json.dumps(sm.get_stats(), indent=2))
    elif cmd == "test":
        for i in range(52):
            sm.advance_turn(f"step{i+1}", f"decision_{'A' if i%2==0 else 'B'}")
        print(json.dumps(sm.get_stats(), indent=2))
    elif cmd == "reset":
        sm.state = {"segment_id": 0, "turn_in_segment": 0, "max_turns_per_segment": MAX_TURNS_PER_SEGMENT,
                    "total_turns_all": 0, "created_at": datetime.now().isoformat(),
                    "tasks_completed_in_segment": [], "key_decisions": []}
        sm._save_state()
        print("reset ok")
