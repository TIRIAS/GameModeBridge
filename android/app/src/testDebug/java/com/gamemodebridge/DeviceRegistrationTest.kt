package com.gamemodebridge

import java.util.Base64
import javax.crypto.SecretKey
import javax.crypto.spec.SecretKeySpec
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

// CLAUDE.md 6장 재등록 규칙과 4단계 완료 기준 확인
class DeviceRegistrationTest {

    private class MemoryVault : KeyVault {
        val keys = mutableMapOf<String, SecretKey>()
        override fun import(alias: String, raw: ByteArray) { keys[alias] = SecretKeySpec(raw.copyOf(), "AES") }
        override fun key(alias: String) = keys[alias]
        override fun delete(alias: String) { keys.remove(alias) }
    }

    private class MemoryState : RegStateStore {
        var value = RegState()
        override fun load() = value
        override fun save(state: RegState) { value = state }
    }

    private class MemorySeq : SeqStore {
        var value = 0L
        override fun last() = value
        override fun save(seq: Long) { value = seq }
    }

    private class FakeSubscriber(var succeed: Boolean = true) : TopicSubscriber {
        val subscribed = mutableSetOf<String>()
        val unsubscribed = mutableListOf<String>()
        override fun subscribe(topic: String, done: (Boolean) -> Unit) {
            if (succeed) subscribed += topic
            done(succeed)
        }
        override fun unsubscribe(topic: String) {
            subscribed -= topic
            unsubscribed += topic
        }
    }

    private class FakeNotifier : NotificationHelper {
        val posted = mutableListOf<GameState>()
        override fun post(state: GameState, text: String): NotifyResult {
            posted += state
            return NotifyResult.POSTED
        }
    }

    private val now = 1_760_000_000L
    private val vault = MemoryVault()
    private val state = MemoryState()
    private val seq = MemorySeq()
    private val subscriber = FakeSubscriber()
    private val notifier = FakeNotifier()
    private val registration = DeviceRegistration(vault, state, seq, subscriber, notifier) { now }

    private class Device(val topic: String, val raw: ByteArray) {
        val factory = EnvelopeFactory(SecretKeySpec(raw, "AES"))
        val qrText = "GMB1:$topic:" + Base64.getUrlEncoder().withoutPadding().encodeToString(raw)
        fun msg(seq: Long, state: String = "on") = factory.message(state, "게임", 1_760_000_000L, seq)
    }

    private val old = Device("gmb_" + "A".repeat(16), ByteArray(32) { 1 })
    private val new = Device("gmb_" + "B".repeat(16), ByteArray(32) { 2 })

    private fun begin(device: Device): Boolean {
        var ok = false
        registration.beginPending(QrPayload.parse(device.qrText)!!) { ok = it }
        return ok
    }

    private fun send(device: Device, seq: Long, topic: String = device.topic) =
        registration.handleMessage("/topics/$topic", device.msg(seq))

    private fun registerAndConfirm(device: Device) {
        assertTrue(begin(device))
        assertTrue(send(device, 1) is ProcessResult.Accepted)
    }

    @Test
    fun notRegisteredDiscards() {
        assertEquals(ProcessResult.Discarded(DiscardReason.NOT_REGISTERED), send(old, 1))
    }

    @Test
    fun firstRegistrationIsPendingUntilFirstValidMessage() {
        assertTrue(begin(old))
        assertEquals(old.topic, state.value.pendingTopic)
        assertNull(state.value.activeTopic)
        assertTrue(old.topic in subscriber.subscribed)

        assertTrue(send(old, 1) is ProcessResult.Accepted)
        assertEquals(old.topic, state.value.activeTopic)
        assertNull(state.value.pendingTopic)
        assertEquals(1L, seq.value)
    }

    @Test
    fun subscribeFailureKeepsExistingConnection() {
        registerAndConfirm(old)
        val before = state.value
        subscriber.succeed = false
        assertTrue(!begin(new))
        assertEquals(before, state.value)
        assertEquals(1, vault.keys.size)
        assertTrue(send(old, 2) is ProcessResult.Accepted)
    }

    @Test
    fun reRegistrationKeepsOldKeyUntilCommit() {
        registerAndConfirm(old)
        assertTrue(send(old, 2) is ProcessResult.Accepted)
        assertTrue(begin(new))
        // 확정 전에는 기존 키로 계속 동작함
        assertTrue(send(old, 3) is ProcessResult.Accepted)
        assertEquals(2, vault.keys.size)
    }

    @Test
    fun commitResetsSeqAndRetiresOldKey() {
        registerAndConfirm(old)
        repeat(56) { send(old, it + 2L) }
        assertEquals(57L, seq.value)

        assertTrue(begin(new))
        // PC는 재등록 확정 후 순번 1부터 다시 보냄
        val result = send(new, 1)
        assertTrue(result is ProcessResult.Accepted)
        assertEquals(new.topic, state.value.activeTopic)
        assertNull(state.value.pendingTopic)
        assertEquals(1L, seq.value)
        assertEquals(1, vault.keys.size)
        assertTrue(old.topic in subscriber.unsubscribed)

        // 확정 후 이전 키로 만든 메시지는 폐기됨
        assertEquals(ProcessResult.Discarded(DiscardReason.TOPIC), send(old, 58))
        assertEquals(ProcessResult.Discarded(DiscardReason.AUTH), send(old, 58, topic = new.topic))
        assertTrue(send(new, 2) is ProcessResult.Accepted)
    }

    @Test
    fun wrongKeyOnPendingTopicDoesNotCommit() {
        registerAndConfirm(old)
        assertTrue(begin(new))
        assertEquals(ProcessResult.Discarded(DiscardReason.AUTH), send(old, 99, topic = new.topic))
        assertEquals(old.topic, state.value.activeTopic)
        assertEquals(new.topic, state.value.pendingTopic)
    }

    @Test
    fun rescanReplacesPending() {
        registerAndConfirm(old)
        assertTrue(begin(new))
        val newer = Device("gmb_" + "C".repeat(16), ByteArray(32) { 3 })
        assertTrue(begin(newer))
        assertEquals(newer.topic, state.value.pendingTopic)
        assertTrue(new.topic in subscriber.unsubscribed)
        assertEquals(ProcessResult.Discarded(DiscardReason.TOPIC), send(new, 1))
        assertTrue(send(newer, 1) is ProcessResult.Accepted)
    }

    @Test
    fun unknownTopicDiscarded() {
        registerAndConfirm(old)
        assertEquals(ProcessResult.Discarded(DiscardReason.TOPIC), send(old, 2, topic = "gmb_" + "Z".repeat(16)))
        assertEquals(ProcessResult.Discarded(DiscardReason.TOPIC), registration.handleMessage(null, old.msg(2)))
    }

    @Test
    fun revokeDeletesEverythingImmediately() {
        registerAndConfirm(old)
        assertTrue(begin(new))
        registration.revoke()
        assertEquals(RegState(), state.value)
        assertTrue(vault.keys.isEmpty())
        assertTrue(subscriber.subscribed.isEmpty())
        assertEquals(0L, seq.value)
        assertEquals(ProcessResult.Discarded(DiscardReason.NOT_REGISTERED), send(old, 5))
    }

    @Test
    fun qrPayloadKeyIsWipedAfterImport() {
        val qr = QrPayload.parse(old.qrText)!!
        registration.beginPending(qr) {}
        assertTrue(qr.key.all { it == 0.toByte() })
        assertNotNull(vault.keys.values.single())
    }
}

class QrPayloadTest {
    private val key43 = Base64.getUrlEncoder().withoutPadding().encodeToString(ByteArray(32) { 7 })
    private val topic = "gmb_abcDEF0123456789".take(20)

    @Test
    fun validPayload() {
        val qr = QrPayload.parse("GMB1:$topic:$key43")
        assertNotNull(qr)
        assertEquals(topic, qr!!.topic)
        assertEquals(32, qr.key.size)
    }

    @Test
    fun surroundingWhitespaceAllowed() {
        assertNotNull(QrPayload.parse("  GMB1:$topic:$key43\n"))
    }

    @Test
    fun invalidPayloadsRejected() {
        val b64 = Base64.getUrlEncoder().withoutPadding()
        val cases = listOf(
            "",
            "GMB2:$topic:$key43",  // 형식 버전
            "gmb1:$topic:$key43",
            "GMB1:$topic",  // 항목 부족
            "GMB1:$topic:$key43:extra",
            "GMB1:gmb_short:$key43",  // 토픽 길이
            "GMB1:gmb_abcdefghijklmnopq:$key43",  // 17자
            "GMB1:xyz_abcdefghijklmnop:$key43",  // 접두어
            "GMB1:gmb_abcdefghijklmn-p:$key43",  // 허용되지 않는 문자
            "GMB1:$topic:${b64.encodeToString(ByteArray(31))}",  // 키 31바이트
            "GMB1:$topic:${b64.encodeToString(ByteArray(33))}",  // 키 33바이트
            "GMB1:$topic:not*base64",
        )
        for (text in cases) assertNull(text, QrPayload.parse(text))
    }
}
