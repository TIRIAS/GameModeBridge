package com.gamemodebridge

import android.content.Context
import android.util.Log
import com.google.firebase.messaging.FirebaseMessaging
import java.util.Base64

/** QR 내용 `GMB1:<토픽>:<공유 키 base64url>` (CLAUDE.md 6장 QR 형식) */
class QrPayload private constructor(val topic: String, val key: ByteArray) {
    companion object {
        private const val PREFIX = "GMB1"
        private val TOPIC = Regex("^gmb_[A-Za-z0-9]{16}$")

        /** 형식이 하나라도 어긋나면 null */
        fun parse(text: String): QrPayload? {
            val parts = text.trim().split(":")
            if (parts.size != 3 || parts[0] != PREFIX || !TOPIC.matches(parts[1])) return null
            val key = try {
                Base64.getUrlDecoder().decode(parts[2])
            } catch (e: IllegalArgumentException) {
                return null
            }
            return if (key.size == 32) QrPayload(parts[1], key) else null
        }
    }
}

/** 등록 상태. active는 사용 중인 키와 토픽, pending은 재등록 중 확정 전인 키와 토픽 */
data class RegState(
    val activeAlias: String? = null,
    val activeTopic: String? = null,
    val pendingAlias: String? = null,
    val pendingTopic: String? = null,
)

interface RegStateStore {
    fun load(): RegState
    fun save(state: RegState)
}

/** 키 별칭과 토픽 이름만 저장함 (키 값은 Keystore에만 있음) */
class PrefsRegStateStore(context: Context) : RegStateStore {
    private val prefs = context.getSharedPreferences("gmb_registration", Context.MODE_PRIVATE)

    override fun load() = RegState(
        prefs.getString("active_alias", null),
        prefs.getString("active_topic", null),
        prefs.getString("pending_alias", null),
        prefs.getString("pending_topic", null),
    )

    override fun save(state: RegState) {
        prefs.edit()
            .putString("active_alias", state.activeAlias)
            .putString("active_topic", state.activeTopic)
            .putString("pending_alias", state.pendingAlias)
            .putString("pending_topic", state.pendingTopic)
            .commit()
    }
}

interface TopicSubscriber {
    fun subscribe(topic: String, done: (Boolean) -> Unit)
    fun unsubscribe(topic: String)
}

object FirebaseTopicSubscriber : TopicSubscriber {
    override fun subscribe(topic: String, done: (Boolean) -> Unit) {
        FirebaseMessaging.getInstance().subscribeToTopic(topic).addOnCompleteListener { done(it.isSuccessful) }
    }

    override fun unsubscribe(topic: String) {
        FirebaseMessaging.getInstance().unsubscribeFromTopic(topic).addOnCompleteListener {
            if (!it.isSuccessful) Log.w("GameModeBridge", "이전 토픽 구독 해제 실패", it.exception)
        }
    }
}

/**
 * 기기 등록과 수신 메시지의 키 선택 (CLAUDE.md 6장 재등록).
 * 일반 재등록: 새 키를 임시 슬롯에 넣고 새 토픽을 구독함. 새 키로 만든 첫 정상 메시지를 받으면 교체를 확정함.
 * 등록이 실패하거나 확정 전이면 기존 키와 토픽을 계속 사용함
 */
class DeviceRegistration(
    private val vault: KeyVault,
    private val stateStore: RegStateStore,
    private val seqStore: SeqStore,
    private val subscriber: TopicSubscriber,
    private val notifier: NotificationHelper,
    private val nowSeconds: () -> Long = { System.currentTimeMillis() / 1000 },
) {

    fun state(): RegState = stateStore.load()

    /** QR 검증 후 호출. done(true)이면 새 토픽 구독 성공 */
    fun beginPending(qr: QrPayload, done: (Boolean) -> Unit) {
        val s = stateStore.load()
        val alias = if (s.activeAlias == ALIAS_A) ALIAS_B else ALIAS_A
        if (s.pendingTopic != null && s.pendingTopic != qr.topic) subscriber.unsubscribe(s.pendingTopic)
        vault.import(alias, qr.key)
        qr.key.fill(0)
        subscriber.subscribe(qr.topic) { ok ->
            if (ok) {
                stateStore.save(stateStore.load().copy(pendingAlias = alias, pendingTopic = qr.topic))
            } else {
                vault.delete(alias)
                stateStore.save(stateStore.load().copy(pendingAlias = null, pendingTopic = null))
            }
            done(ok)
        }
    }

    /** FCM 메시지 처리. from은 토픽 메시지의 경우 `/topics/<토픽>` */
    fun handleMessage(from: String?, data: Map<String, String>): ProcessResult {
        val topic = from?.removePrefix("/topics/")
        val s = stateStore.load()
        return when {
            topic != null && topic == s.activeTopic -> process(s.activeAlias, seqStore, data)
            topic != null && topic == s.pendingTopic -> {
                // 새 키의 순번은 0부터 다시 시작함. 첫 정상 메시지의 순번을 저장하는 시점에 교체를 확정함
                val commitOnSave = object : SeqStore {
                    override fun last() = 0L
                    override fun save(seq: Long) {
                        commit(s)
                        seqStore.save(seq)
                    }
                }
                process(s.pendingAlias, commitOnSave, data)
            }
            s.activeTopic == null && s.pendingTopic == null -> ProcessResult.Discarded(DiscardReason.NOT_REGISTERED)
            else -> ProcessResult.Discarded(DiscardReason.TOPIC)
        }
    }

    /** 유출 대응 재등록: 기존 키와 토픽을 즉시 삭제함 */
    fun revoke() {
        val s = stateStore.load()
        listOfNotNull(s.activeTopic, s.pendingTopic).forEach(subscriber::unsubscribe)
        listOfNotNull(s.activeAlias, s.pendingAlias).forEach(vault::delete)
        stateStore.save(RegState())
        seqStore.save(0)
    }

    private fun process(alias: String?, store: SeqStore, data: Map<String, String>): ProcessResult {
        val key = alias?.let(vault::key) ?: return ProcessResult.Discarded(DiscardReason.NOT_REGISTERED)
        return MessageProcessor(AesGcmCryptoManager(key), store, notifier, nowSeconds).process(data)
    }

    private fun commit(s: RegState) {
        s.activeTopic?.let(subscriber::unsubscribe)
        s.activeAlias?.let(vault::delete)
        stateStore.save(RegState(activeAlias = s.pendingAlias, activeTopic = s.pendingTopic))
    }

    companion object {
        private const val ALIAS_A = "gmb_key_a"
        private const val ALIAS_B = "gmb_key_b"

        fun create(context: Context) = DeviceRegistration(
            KeyStoreManager,
            PrefsRegStateStore(context),
            PrefsSeqStore(context),
            FirebaseTopicSubscriber,
            AndroidNotificationHelper(context),
        )
    }
}
