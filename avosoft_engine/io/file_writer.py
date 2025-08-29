# avosoft_retail/avosoft_engine/io/file_writer.py
from pathlib import Path
import json, csv
from .base import Writer

class FileWriter(Writer):
    def write_jsonl(self, path: str, records):
        p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    def write_csv(self, path: str, rows, header):
        p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=header)
            w.writeheader()
            for r in rows:
                w.writerow(r)
