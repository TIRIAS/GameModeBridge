package com.gamemodebridge

import java.security.SecureRandom
import java.util.Base64
import javax.crypto.Cipher
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put

/**
 * 시뮬레이터와 테스트용 메시지 생성기 (PC gmb/crypto.py의 seal과 같은 형식).
 * debug 소스 세트에만 두며, 실제 등록 키가 아닌 소프트웨어 테스트 키만 사용함
 */
class EnvelopeFactory(private val key: SecretKey) {

    private val random = SecureRandom()

    fun plaintext(
        state: String, game: String, ts: Long, seq: Long, msgId: String = randomMsgId(), sync: Boolean = false,
    ): ByteArray =
        buildJsonObject {
            put("state", state)
            put("game", game)
            put("ts", ts)
            put("seq", seq)
            put("msg_id", msgId)
            if (sync) put("sync", true)
        }.toString().toByteArray(Charsets.UTF_8)

    fun seal(plaintext: ByteArray, aad: ByteArray = AAD): Map<String, String> {
        val iv = ByteArray(12).also(random::nextBytes)
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, key, GCMParameterSpec(128, iv))
        cipher.updateAAD(aad)
        val ct = cipher.doFinal(plaintext)
        return mapOf("v" to PROTOCOL_VERSION, "iv" to b64(iv), "ct" to b64(ct))
    }

    fun message(state: String, game: String, ts: Long, seq: Long, sync: Boolean = false): Map<String, String> =
        seal(plaintext(state, game, ts, seq, sync = sync))

    private fun randomMsgId(): String =
        ByteArray(16).also(random::nextBytes).joinToString("") { "%02x".format(it) }

    private fun b64(bytes: ByteArray): String = Base64.getUrlEncoder().withoutPadding().encodeToString(bytes)

    companion object {
        /** 매번 새로 만드는 시뮬레이터 전용 키 (저장하지 않음) */
        fun newTestKey(): SecretKey =
            javax.crypto.KeyGenerator.getInstance("AES").apply { init(256) }.generateKey()

        /** 바이트 하나를 바꿔 위변조된 봉투를 만듦 */
        fun tamper(envelope: Map<String, String>): Map<String, String> {
            val ct = Base64.getUrlDecoder().decode(envelope.getValue("ct"))
            ct[0] = (ct[0].toInt() xor 0x01).toByte()
            return envelope + ("ct" to Base64.getUrlEncoder().withoutPadding().encodeToString(ct))
        }
    }
}
