package com.gamemodebridge

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.longOrNull

/** 폐기 사유 코드. 로그에는 이 코드만 남기고 메시지 내용은 남기지 않음 */
enum class DiscardReason {
    VERSION, FORMAT, AUTH, STATE, STALE, FUTURE, SEQ,
    /** 등록된 키가 없음 */
    NOT_REGISTERED,
    /** 등록된 토픽이 아닌 곳에서 온 메시지 (교체 전 이전 토픽 등) */
    TOPIC,
}

sealed interface ProcessResult {
    /** serviceStart: 자동 동기화 off를 이미 꺼진 상태에서 받아 키워드 없는 서비스 시작 알림을 띄움 */
    data class Accepted(
        val state: GameState,
        val seq: Long,
        val notify: NotifyResult,
        val serviceStart: Boolean = false,
    ) : ProcessResult
    data class Discarded(val reason: DiscardReason) : ProcessResult
}

/**
 * FCM 데이터 메시지 수신 처리 (CLAUDE.md 5장 수신 측 처리 순서).
 * 외부 의존 요소(복호화, 순번 저장, 알림, 현재 시각)는 모두 주입받음
 */
class MessageProcessor(
    private val crypto: CryptoManager,
    private val seqStore: SeqStore,
    private val notifier: NotificationHelper,
    private val nowSeconds: () -> Long = { System.currentTimeMillis() / 1000 },
) {

    fun process(data: Map<String, String>): ProcessResult {
        // 1) 버전, 2) 복호화 및 인증 태그 검증
        val plaintext = try {
            crypto.open(data["v"], data["iv"], data["ct"])
        } catch (e: EnvelopeException) {
            return ProcessResult.Discarded(
                when (e.reason) {
                    EnvelopeError.VERSION -> DiscardReason.VERSION
                    EnvelopeError.FORMAT -> DiscardReason.FORMAT
                    EnvelopeError.AUTH -> DiscardReason.AUTH
                }
            )
        }
        val msg = parse(plaintext) ?: return ProcessResult.Discarded(DiscardReason.FORMAT)

        // 3) state 값
        val state = when (msg.state) {
            "on" -> GameState.ON
            "off" -> GameState.OFF
            else -> return ProcessResult.Discarded(DiscardReason.STATE)
        }

        // 4) 발송 시각
        val now = nowSeconds()
        if (now - msg.ts >= MAX_AGE_SEC) return ProcessResult.Discarded(DiscardReason.STALE)
        if (msg.ts - now >= MAX_FUTURE_SEC) return ProcessResult.Discarded(DiscardReason.FUTURE)

        // 5) 순번: 마지막 처리 순번 이하이면 재전송 또는 순서 역전
        if (msg.seq <= seqStore.last()) return ProcessResult.Discarded(DiscardReason.SEQ)

        // 6) 순번을 먼저 저장한 뒤 알림 게시
        seqStore.save(msg.seq)

        // PC 시작이나 절전 해제 때의 자동 동기화 off인데 이미 꺼진 상태면 키워드 알림을 띄우지 않음
        if (msg.sync && state == GameState.OFF && notifier.lastState() == GameState.OFF) {
            return ProcessResult.Accepted(state, msg.seq, notifier.postServiceStart(), serviceStart = true)
        }

        // 7) 게임 이름 정리 후 표시
        val game = sanitizeGame(msg.game).ifEmpty { "게임" }
        val text = if (state == GameState.ON) "$game 실행 감지" else "$game 종료 감지"
        return ProcessResult.Accepted(state, msg.seq, notifier.post(state, text))
    }

    private class Plaintext(val state: String, val game: String, val ts: Long, val seq: Long, val sync: Boolean)

    private fun parse(bytes: ByteArray): Plaintext? {
        val obj = try {
            Json.parseToJsonElement(bytes.toString(Charsets.UTF_8)).jsonObject
        } catch (e: IllegalArgumentException) {
            // 잘못된 JSON(SerializationException 포함)이나 객체가 아닌 값
            return null
        }
        if (obj.string("msg_id") == null) return null
        return Plaintext(
            state = obj.string("state") ?: return null,
            game = obj.string("game") ?: return null,
            ts = obj.long("ts") ?: return null,
            seq = obj.long("seq") ?: return null,
            // 선택 필드. 없거나 true가 아니면 일반 메시지로 처리함 (이전 PC 버전 호환)
            sync = (obj["sync"] as? JsonPrimitive)?.takeIf { !it.isString }?.booleanOrNull == true,
        )
    }

    private fun JsonObject.string(name: String): String? =
        (get(name) as? JsonPrimitive)?.takeIf { it.isString }?.content

    private fun JsonObject.long(name: String): Long? =
        (get(name) as? JsonPrimitive)?.takeIf { !it.isString }?.longOrNull

    companion object {
        const val MAX_AGE_SEC = 120L
        const val MAX_FUTURE_SEC = 60L
        const val MAX_GAME_LENGTH = 50

        private val KEYWORDS = Regex("${KEYWORD_ON}|${KEYWORD_OFF}", RegexOption.IGNORE_CASE)

        /**
         * 제어 문자와 루틴 키워드를 제거하고 최대 50자로 자름.
         * 키워드 제거 후 남은 글자가 다시 키워드가 되는 경우를 막기 위해 변화가 없을 때까지 반복함
         */
        fun sanitizeGame(raw: String): String {
            var text = raw.filterNot { Character.isISOControl(it) || Character.getType(it) == Character.FORMAT.toInt() }
            while (true) {
                val next = KEYWORDS.replace(text, "")
                if (next == text) break
                text = next
            }
            text = text.trim()
            // 서로게이트 쌍(이모지 등)이 잘리지 않도록 코드 포인트 기준으로 자름
            val cpCount = text.codePointCount(0, text.length)
            return if (cpCount <= MAX_GAME_LENGTH) text
            else text.substring(0, text.offsetByCodePoints(0, MAX_GAME_LENGTH))
        }
    }
}
