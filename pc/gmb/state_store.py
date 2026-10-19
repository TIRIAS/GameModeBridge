"""발송 순번(seq) 보존 (CLAUDE.md 5장 순번 규칙).

순번은 비밀 정보가 아니므로 일반 파일에 둠. 암호문 안에 들어가므로 위조할 수 없음.
"""

import json
import os
from pathlib import Path


def default_path() -> Path:
    return Path(os.environ["APPDATA"]) / "GameModeBridge" / "state.json"


class FileStateStore:
    def __init__(self, path: Path):
        self.path = path

    def last_seq(self) -> int:
        if not self.path.exists():
            return 0
        return int(json.loads(self.path.read_text(encoding="utf-8"))["seq"])

    def next_seq(self) -> int:
        """순번을 1 증가시켜 발송 전에 디스크에 저장하고 돌려줌."""
        seq = self.last_seq() + 1
        self._write(seq)
        return seq

    def reset(self) -> None:
        """새 키로 재등록할 때 0으로 초기화함."""
        self._write(0)

    def _write(self, seq: int) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"seq": seq}), encoding="utf-8")
        os.replace(tmp, self.path)  # 쓰는 도중 꺼져도 파일이 깨지지 않게 교체 방식으로 저장
