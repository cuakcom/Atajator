"""
Busca el atajo de teclado más relevante para el contexto del click.
Lee los JSON de shortcuts sin dependencias externas.
"""
import json
import os

SHORTCUTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shortcuts")

PROCESS_MAP = {
    "chrome.exe":    "chrome",
    "firefox.exe":   "firefox",
    "msedge.exe":    "edge",
    "opera.exe":     "opera",
    "excel.exe":     "excel",
    "winword.exe":   "word",
    "powerpnt.exe":  "powerpoint",
    "onenote.exe":   "onenote",
    "outlook.exe":   "outlook",
    "code.exe":      "vscode",
    "notepad.exe":   "notepad",
    "notepad++.exe": "notepadpp",
    "explorer.exe":  "explorer",
    "cmd.exe":       "cmd",
    "powershell.exe":"powershell",
    "mspaint.exe":   "paint",
}


class ShortcutMatcher:
    def __init__(self):
        self._db: dict = {}
        self._load_all()

    def _load_all(self):
        if not os.path.isdir(SHORTCUTS_DIR):
            return
        for fname in os.listdir(SHORTCUTS_DIR):
            if fname.endswith(".json"):
                key  = fname[:-5]
                path = os.path.join(SHORTCUTS_DIR, fname)
                try:
                    with open(path, encoding="utf-8") as f:
                        self._db[key] = json.load(f)
                except Exception:
                    pass

    def reload(self):
        self._db.clear()
        self._load_all()

    def find(self, app_info: dict):
        process = app_info.get("process", "").lower()
        key     = PROCESS_MAP.get(process)
        if not key:
            return None

        db_entry = self._db.get(key)
        if not db_entry:
            return None

        control_text = app_info.get("control_text", "").lower()
        class_name   = app_info.get("class_name", "").lower()
        region       = app_info.get("region", "content")

        best       = None
        best_score = 0

        for entry in db_entry.get("shortcuts", []):
            score = self._score(entry, control_text, class_name, region)
            if score > best_score:
                best_score = score
                best = entry

        if best and best_score > 0:
            return {
                "shortcut":   best["shortcut"],
                "action":     best["action"],
                "app":        db_entry.get("name", key),
                "confidence": best_score,
            }
        return None

    @staticmethod
    def _score(entry: dict, text: str, cls: str, region: str) -> int:
        score = 0
        for kw in entry.get("keywords", []):
            kw_l = kw.lower()
            if kw_l and kw_l in text:
                score += 12
            elif kw_l and text and text[:4] in kw_l:
                score += 3
        for cn in entry.get("class_names", []):
            if cn.lower() == cls:
                score += 8
        for r in entry.get("regions", []):
            if r == region:
                score += 5
        return score
