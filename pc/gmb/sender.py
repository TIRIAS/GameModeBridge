"""발송자: FCM HTTP v1 발송, 드라이런, 메모리 수집 (CLAUDE.md 3장 FCM 발송 옵션, 7장).

발송 성공은 FCM 서버가 접수했다는 뜻이며 휴대폰 도착을 뜻하지 않음.
"""

import json
import logging
import time
from pathlib import Path

log = logging.getLogger(__name__)

FCM_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
TTL = "60s"
MAX_RETRIES = 3
RETRY_DELAYS_SEC = (1, 2, 2)
REQUEST_TIMEOUT_SEC = 10
# 요청 자체가 잘못되어 다시 보내도 성공할 수 없는 응답
_PERMANENT_STATUS = {400, 401, 403, 404}


class SendError(Exception):
    pass


def build_fcm_message(topic: str, envelope: dict) -> dict:
    return {
        "message": {
            "topic": topic,
            "data": envelope,
            # collapse_key는 쓰지 않음: 기기당 연속 20개 한도에 걸리면 메시지가 버려짐 (CLAUDE.md 3장)
            "android": {"priority": "HIGH", "ttl": TTL},
        }
    }


class FcmSender:
    """FCM HTTP v1 발송. AuthorizedSession이 접근 토큰(1시간 유효)을 재사용하고 만료 시에만 갱신함."""

    def __init__(self, service_account_info: dict, session=None, sleep=time.sleep):
        self.project_id = service_account_info["project_id"]
        if session is None:
            from google.auth.transport.requests import AuthorizedSession
            from google.oauth2 import service_account

            creds = service_account.Credentials.from_service_account_info(service_account_info, scopes=[FCM_SCOPE])
            session = AuthorizedSession(creds)
        self.session = session
        self.sleep = sleep
        self.url = f"https://fcm.googleapis.com/v1/projects/{self.project_id}/messages:send"

    def send(self, topic: str, envelope: dict) -> None:
        """같은 봉투로 최초 1회와 재시도 최대 3회 발송함. 모두 실패하면 SendError."""
        body = build_fcm_message(topic, envelope)
        for attempt in range(MAX_RETRIES + 1):
            try:
                # requests 기본값대로 인증서 검증을 항상 켜 둠 (verify를 끄지 않음)
                resp = self.session.post(self.url, json=body, timeout=REQUEST_TIMEOUT_SEC)
            except Exception as e:  # 네트워크 오류는 재시도 대상
                reason = type(e).__name__
            else:
                if resp.status_code == 200:
                    return
                reason = f"HTTP {resp.status_code}"
                if resp.status_code in _PERMANENT_STATUS:
                    log.error("FCM 발송 거부: %s", reason)
                    raise SendError(reason)
            log.warning("FCM 발송 실패 (%d회차): %s", attempt + 1, reason)
            if attempt < MAX_RETRIES:
                self.sleep(RETRY_DELAYS_SEC[attempt])
        raise SendError(reason)


class DryRunSender:
    """발송 대신 로그와 파일에 기록함. 봉투는 암호문이므로 기록해도 내용이 드러나지 않음."""

    def __init__(self, path: Path):
        self.path = path

    def send(self, topic: str, envelope: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"time": int(time.time()), "fcm": build_fcm_message(topic, envelope)}) + "\n")
        log.info("드라이런 기록: %s", self.path)


class MemorySender:
    """테스트용: 보낸 메시지를 모음."""

    def __init__(self):
        self.sent: list[tuple[str, dict]] = []

    def send(self, topic: str, envelope: dict) -> None:
        self.sent.append((topic, envelope))
