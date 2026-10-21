package com.gamemodebridge

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

// CLAUDE.md 5장 수신 측 처리 순서 전 단계 확인
class MessageProcessorTest {

    private class MemorySeqStore(var value: Long = 0) : SeqStore {
        override fun last() = value
        override fun save(seq: Long) { value = seq }
    }

    private class FakeNotifier(private val store: SeqStore, var result: NotifyResult = NotifyResult.POSTED) :
        NotificationHelper {
        val posted = mutableListOf<Pair<GameState, String>>()
        val seqAtPost = mutableListOf<Long>()
        var last: GameState? = null
        var serviceStarts = 0
        override fun post(state: GameState, text: String): NotifyResult {
            posted += state to text
            seqAtPost += store.last()
            if (result == NotifyResult.POSTED) last = state
            return result
        }
        override fun postServiceStart(): NotifyResult {
            serviceStarts++
            return result
        }
        override fun lastState() = last
    }

    private val now = 1_760_000_000L
    private val key = EnvelopeFactory.newTestKey()
    private val factory = EnvelopeFactory(key)
    private val seqStore = MemorySeqStore()
    private val notifier = FakeNotifier(seqStore)
    private val processor = MessageProcessor(AesGcmCryptoManager(key), seqStore, notifier) { now }

    private fun msg(
        state: String = "on", game: String = "VALORANT", ts: Long = now, seq: Long = 1, sync: Boolean = false,
    ) = factory.message(state, game, ts, seq, sync)

    private fun discarded(reason: DiscardReason) = ProcessResult.Discarded(reason)

    @Test
    fun validOnPostsKeywordNotification() {
        assertEquals(ProcessResult.Accepted(GameState.ON, 1, NotifyResult.POSTED), processor.process(msg()))
        assertEquals(listOf(GameState.ON to "VALORANT 실행 감지"), notifier.posted)
        assertEquals(1L, seqStore.last())
    }

    @Test
    fun validOffPostsOffNotification() {
        processor.process(msg(state = "off", game = "검은사막"))
        assertEquals(listOf(GameState.OFF to "검은사막 종료 감지"), notifier.posted)
    }

    @Test
    fun emptyGameNameUsesDefaultLabel() {
        processor.process(msg(state = "off", game = ""))
        assertEquals("게임 종료 감지", notifier.posted.single().second)
    }

    @Test
    fun seqIsSavedBeforeNotification() {
        processor.process(msg(seq = 7))
        assertEquals(listOf(7L), notifier.seqAtPost)
    }

    @Test
    fun blockedNotificationIsReported() {
        notifier.result = NotifyResult.BLOCKED
        assertEquals(ProcessResult.Accepted(GameState.ON, 1, NotifyResult.BLOCKED), processor.process(msg()))
    }

    // 1) 버전
    @Test
    fun unsupportedVersionDiscarded() {
        assertEquals(discarded(DiscardReason.VERSION), processor.process(msg() + ("v" to "2")))
    }

    // 2) 형식 및 인증
    @Test
    fun missingFieldDiscardedAsFormat() {
        assertEquals(discarded(DiscardReason.FORMAT), processor.process(msg() - "iv"))
    }

    @Test
    fun tamperedDiscardedAsAuth() {
        assertEquals(discarded(DiscardReason.AUTH), processor.process(EnvelopeFactory.tamper(msg())))
    }

    @Test
    fun otherKeyDiscardedAsAuth() {
        val other = EnvelopeFactory(EnvelopeFactory.newTestKey()).message("on", "x", now, 1)
        assertEquals(discarded(DiscardReason.AUTH), processor.process(other))
    }

    @Test
    fun otherAadDiscardedAsAuth() {
        val env = factory.seal(factory.plaintext("on", "x", now, 1), aad = "GMB-v2".toByteArray())
        assertEquals(discarded(DiscardReason.AUTH), processor.process(env))
    }

    @Test
    fun malformedPlaintextDiscardedAsFormat() {
        val cases = listOf(
            "not json",
            "[1,2]",
            """{"state":"on","game":"x","ts":$now,"seq":1}""",  // msg_id 없음
            """{"state":"on","game":"x","ts":"$now","seq":1,"msg_id":"a"}""",  // ts가 문자열
            """{"state":"on","game":"x","ts":$now,"seq":1.5,"msg_id":"a"}""",  // seq가 정수 아님
            """{"state":1,"game":"x","ts":$now,"seq":1,"msg_id":"a"}""",  // state가 숫자
        )
        for (text in cases) {
            assertEquals(text, discarded(DiscardReason.FORMAT), processor.process(factory.seal(text.toByteArray())))
        }
        assertTrue(notifier.posted.isEmpty())
    }

    // 3) state 값
    @Test
    fun unknownStateDiscarded() {
        assertEquals(discarded(DiscardReason.STATE), processor.process(msg(state = "start")))
    }

    // 4) 발송 시각 경계
    @Test
    fun staleBoundary() {
        assertEquals(discarded(DiscardReason.STALE), processor.process(msg(ts = now - 120, seq = 1)))
        assertTrue(processor.process(msg(ts = now - 119, seq = 2)) is ProcessResult.Accepted)
    }

    @Test
    fun futureBoundary() {
        assertEquals(discarded(DiscardReason.FUTURE), processor.process(msg(ts = now + 60, seq = 1)))
        assertTrue(processor.process(msg(ts = now + 59, seq = 2)) is ProcessResult.Accepted)
    }

    // 5) 순번
    @Test
    fun replayDiscarded() {
        val m = msg(seq = 3)
        assertTrue(processor.process(m) is ProcessResult.Accepted)
        assertEquals(discarded(DiscardReason.SEQ), processor.process(m))
        assertEquals(1, notifier.posted.size)
    }

    @Test
    fun reorderedOlderMessageDiscarded() {
        val on = msg(state = "on", seq = 1)
        val off = msg(state = "off", seq = 2)
        processor.process(off)
        assertEquals(discarded(DiscardReason.SEQ), processor.process(on))
        assertEquals(listOf(GameState.OFF), notifier.posted.map { it.first })
    }

    @Test
    fun seqSurvivesNewProcessorInstance() {
        processor.process(msg(seq = 5))
        // 앱 재시작: 같은 저장소로 새 처리기를 만들어도 이전 순번 이하는 폐기됨
        val restarted = MessageProcessor(AesGcmCryptoManager(key), seqStore, notifier) { now }
        assertEquals(discarded(DiscardReason.SEQ), restarted.process(msg(seq = 5)))
    }

    @Test
    fun discardedMessageDoesNotChangeSeq() {
        processor.process(msg(seq = 2))
        processor.process(EnvelopeFactory.tamper(msg(seq = 10)))
        processor.process(msg(seq = 10, ts = now - 500))
        assertEquals(2L, seqStore.last())
    }

    // 7) 게임 이름 정리
    @Test
    fun sanitizeRemovesControlCharacters() {
        assertEquals("ABC", MessageProcessor.sanitizeGame("A\nB\u0000C‎"))
    }

    @Test
    fun sanitizeRemovesKeywordsIgnoringCase() {
        assertEquals("게임", MessageProcessor.sanitizeGame("GAMEMODE_ON게임gamemode_off"))
    }

    @Test
    fun sanitizeRemovesNestedKeyword() {
        // 안쪽 키워드를 지우면 바깥에 새 키워드가 생기는 경우
        assertEquals("", MessageProcessor.sanitizeGame("GAMEMODE_GAMEMODE_ONON"))
    }

    @Test
    fun sanitizeTruncatesTo50CodePoints() {
        assertEquals("가".repeat(50), MessageProcessor.sanitizeGame("가".repeat(80)))
        val emoji = "🎮"  // 서로게이트 쌍 이모지
        val result = MessageProcessor.sanitizeGame(emoji.repeat(60))
        assertEquals(50, result.codePointCount(0, result.length))
    }

    @Test
    fun keywordInGameNameIsNotShownInNotification() {
        processor.process(msg(state = "off", game = "GAMEMODE_ON"))
        assertEquals("게임 종료 감지", notifier.posted.single().second)
    }

    // ---------- 자동 동기화 (PC 시작, 절전 해제) ----------

    @Test
    fun syncOffWhenAlreadyOffPostsServiceStartWithoutKeyword() {
        notifier.last = GameState.OFF
        val result = processor.process(msg(state = "off", game = "", sync = true))
        assertEquals(ProcessResult.Accepted(GameState.OFF, 1, NotifyResult.POSTED, serviceStart = true), result)
        assertEquals(1, notifier.serviceStarts)
        assertTrue(notifier.posted.isEmpty())
        assertEquals(1L, seqStore.last())
    }

    @Test
    fun syncOffWhenOnPostsOffKeyword() {
        // 게임 중 PC가 꺼졌다가 다시 켜진 경우: 게임 모드를 꺼야 함
        notifier.last = GameState.ON
        processor.process(msg(state = "off", game = "", sync = true))
        assertEquals(listOf(GameState.OFF to "게임 종료 감지"), notifier.posted)
        assertEquals(0, notifier.serviceStarts)
    }

    @Test
    fun syncOffWithUnknownStatePostsOffKeyword() {
        processor.process(msg(state = "off", game = "", sync = true))
        assertEquals(GameState.OFF, notifier.posted.single().first)
    }

    @Test
    fun nonSyncOffWhenAlreadyOffStillPostsKeyword() {
        // 트레이의 현재 상태 다시 보내기는 항상 키워드 알림
        notifier.last = GameState.OFF
        processor.process(msg(state = "off", game = "", sync = false))
        assertEquals(GameState.OFF, notifier.posted.single().first)
    }

    @Test
    fun syncOnPostsOnKeyword() {
        notifier.last = GameState.ON
        processor.process(msg(state = "on", sync = true))
        assertEquals(GameState.ON, notifier.posted.single().first)
    }

    @Test
    fun syncFieldAsStringIsIgnored() {
        notifier.last = GameState.OFF
        val plain = "{\"state\":\"off\",\"game\":\"\",\"ts\":$now,\"seq\":1,\"msg_id\":\"ab\",\"sync\":\"true\"}"
        processor.process(factory.seal(plain.toByteArray(Charsets.UTF_8)))
        assertEquals(GameState.OFF, notifier.posted.single().first)
    }
}
