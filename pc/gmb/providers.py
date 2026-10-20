"""프로세스 제공자 (CLAUDE.md 6단계 프로세스 조회 방식, 11장 PC 앱 보안).

프로세스 목록 조회와 이름 확인만 함. 프로세스 핸들 열기, 메모리 읽기 등은 하지 않음 (안티치트 제재 위험).
"""

import logging

import psutil

log = logging.getLogger(__name__)


class ProcessQueryError(Exception):
    """조회 자체가 실패함. 게임 종료로 단정하지 않기 위해 빈 목록과 구분함."""


class PsutilProvider:
    def running_names(self) -> set[str]:
        names = set()
        try:
            # attrs를 지정하면 psutil이 접근 거부 프로세스의 값을 None으로 채움
            for proc in psutil.process_iter(["name"]):
                try:
                    name = proc.info["name"]
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                if name:
                    names.add(name.lower())
        except (psutil.Error, OSError) as e:
            raise ProcessQueryError(type(e).__name__) from e
        return names


def running_exe_names() -> list[str]:
    """감지할 프로그램 관리 창에 보여줄 실행 중 exe 이름 목록. 원래 표기 유지, 대소문자 무시 정렬.

    조회에 실패하면 빈 목록을 돌려줌 (화면 표시용이므로 감지 판단에는 쓰지 않음).
    """
    unique: dict[str, str] = {}
    try:
        for proc in psutil.process_iter(["name"]):
            name = proc.info.get("name")
            if name and name.lower().endswith(".exe"):
                unique.setdefault(name.lower(), name)
    except (psutil.Error, OSError) as e:
        log.warning("실행 중 프로그램 조회 실패: %s", type(e).__name__)
    return sorted(unique.values(), key=str.lower)


class FakeProvider:
    """시나리오 목록을 차례로 돌려줌. 목록이 끝나면 마지막 값을 반복함. None은 조회 실패를 뜻함."""

    def __init__(self, steps: list[set[str] | None]):
        self.steps = list(steps)
        self.last: set[str] | None = set()

    def running_names(self) -> set[str]:
        if self.steps:
            self.last = self.steps.pop(0)
        if self.last is None:
            raise ProcessQueryError("fake")
        return {n.lower() for n in self.last}
