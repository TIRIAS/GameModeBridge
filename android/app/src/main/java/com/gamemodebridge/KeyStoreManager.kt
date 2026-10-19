package com.gamemodebridge

import android.security.keystore.KeyProperties
import android.security.keystore.KeyProtection
import java.security.KeyStore
import javax.crypto.SecretKey
import javax.crypto.spec.SecretKeySpec

/** 공유 키 보관소. 테스트에서는 메모리 구현을 주입함 */
interface KeyVault {
    fun import(alias: String, raw: ByteArray)
    fun key(alias: String): SecretKey?
    fun delete(alias: String)
}

/**
 * Android Keystore 구현.
 * Keystore: 키를 앱 저장소가 아닌 시스템 보호 영역에 두고, 한 번 넣은 키 값은 앱도 다시 꺼낼 수 없게 하는 안드로이드 기능.
 * 공유 키는 복호화 용도로만 쓸 수 있게 제한함 (CLAUDE.md 6장)
 */
object KeyStoreManager : KeyVault {

    private fun keyStore() = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }

    override fun import(alias: String, raw: ByteArray) {
        val protection = KeyProtection.Builder(KeyProperties.PURPOSE_DECRYPT)
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
            .build()
        keyStore().setEntry(alias, KeyStore.SecretKeyEntry(SecretKeySpec(raw, "AES")), protection)
    }

    override fun key(alias: String): SecretKey? = keyStore().getKey(alias, null) as? SecretKey

    override fun delete(alias: String) {
        val ks = keyStore()
        if (ks.containsAlias(alias)) ks.deleteEntry(alias)
    }
}
