package com.gamemodebridge

import java.util.Base64
import javax.crypto.AEADBadTagException
import javax.crypto.Cipher
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

// 봉투 형식 공통 값 (PC gmb/crypto.py와 같아야 함)
const val PROTOCOL_VERSION = "1"
internal val AAD = "GMB-v1".toByteArray(Charsets.US_ASCII)
private const val IV_SIZE = 12
private const val TAG_BITS = 128

/** 봉투를 열 수 없는 이유. 로그에는 이 사유 코드만 남김 */
enum class EnvelopeError { VERSION, FORMAT, AUTH }

class EnvelopeException(val reason: EnvelopeError) : Exception(reason.name)

/** 봉투(v, iv, ct)를 복호화하여 평문 바이트를 돌려줌. 실패 시 EnvelopeException */
interface CryptoManager {
    fun open(v: String?, iv: String?, ct: String?): ByteArray
}

/**
 * AES-256-GCM 복호화 구현.
 * 실제 앱에서는 Keystore 키를, 테스트와 디버그 시뮬레이터에서는 소프트웨어 테스트 키를 주입함
 */
class AesGcmCryptoManager(private val key: SecretKey) : CryptoManager {

    override fun open(v: String?, iv: String?, ct: String?): ByteArray {
        if (v != PROTOCOL_VERSION) throw EnvelopeException(EnvelopeError.VERSION)
        val ivBytes = decode(iv)
        val ctBytes = decode(ct)
        if (ivBytes.size != IV_SIZE) throw EnvelopeException(EnvelopeError.FORMAT)

        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE, key, GCMParameterSpec(TAG_BITS, ivBytes))
        cipher.updateAAD(AAD)
        return try {
            cipher.doFinal(ctBytes)
        } catch (e: AEADBadTagException) {
            throw EnvelopeException(EnvelopeError.AUTH)
        }
    }

    private fun decode(text: String?): ByteArray {
        if (text == null) throw EnvelopeException(EnvelopeError.FORMAT)
        return try {
            Base64.getUrlDecoder().decode(text)
        } catch (e: IllegalArgumentException) {
            throw EnvelopeException(EnvelopeError.FORMAT)
        }
    }
}
