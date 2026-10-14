package com.gamemodebridge

import java.io.File
import java.util.Base64
import javax.crypto.spec.SecretKeySpec
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test

// PC에서 만든 shared/testvectors/crypto_v1.json으로 교차 검증함
class CryptoManagerTest {

    private val vectors: JsonObject by lazy {
        val path = System.getProperty("gmb.testvectors") ?: error("gmb.testvectors 경로가 없음")
        Json.parseToJsonElement(File(path).readText(Charsets.UTF_8)).jsonObject
    }

    private fun JsonObject.str(name: String) = getValue(name).jsonPrimitive.content

    private fun managerFor(item: JsonObject) =
        AesGcmCryptoManager(SecretKeySpec(Base64.getUrlDecoder().decode(item.str("key")), "AES"))

    private fun open(item: JsonObject): ByteArray {
        val env = item.getValue("envelope").jsonObject
        return managerFor(item).open(env.str("v"), env.str("iv"), env.str("ct"))
    }

    @Test
    fun fileHasExpectedProtocol() {
        assertEquals(PROTOCOL_VERSION, vectors.str("version"))
        assertEquals("GMB-v1", vectors.str("aad"))
    }

    @Test
    fun validVectorsDecryptToSamePlaintext() {
        val valid = vectors.getValue("valid").jsonArray
        assertTrue(valid.isNotEmpty())
        for (element in valid) {
            val item = element.jsonObject
            assertEquals(item.str("name"), item.str("plaintext"), String(open(item), Charsets.UTF_8))
        }
    }

    @Test
    fun invalidVectorsAreRejectedWithReason() {
        val invalid = vectors.getValue("invalid").jsonArray
        assertTrue(invalid.isNotEmpty())
        for (element in invalid) {
            val item = element.jsonObject
            val expected = if (item.str("reason") == "version") EnvelopeError.VERSION else EnvelopeError.AUTH
            try {
                open(item)
                fail("${item.str("name")}: 폐기되어야 함")
            } catch (e: EnvelopeException) {
                assertEquals(item.str("name"), expected, e.reason)
            }
        }
    }

    @Test
    fun malformedEnvelopeIsFormatError() {
        val item = vectors.getValue("valid").jsonArray.first().jsonObject
        val manager = managerFor(item)
        val env = item.getValue("envelope").jsonObject
        val cases = listOf(
            Triple("1", null, env.str("ct")),
            Triple("1", env.str("iv"), null),
            Triple("1", "@@@", env.str("ct")),
            Triple("1", "AAAA", env.str("ct")),  // IV 3바이트
        )
        for ((v, iv, ct) in cases) {
            try {
                manager.open(v, iv, ct)
                fail("iv=$iv ct=$ct: 폐기되어야 함")
            } catch (e: EnvelopeException) {
                assertEquals(EnvelopeError.FORMAT, e.reason)
            }
        }
    }
}
