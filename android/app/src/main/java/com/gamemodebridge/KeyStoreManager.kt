package com.gamemodebridge

import java.security.KeyStore
import javax.crypto.SecretKey

/**
 * Android Keystore에 저장된 공유 키 조회.
 * Keystore: 키를 앱 저장소가 아닌 시스템 보호 영역에 두고, 키 값 자체는 꺼낼 수 없게 하는 안드로이드 기능.
 * 키 가져오기와 교체는 4단계(기기 등록)에서 구현함
 */
object KeyStoreManager {
    private const val ALIAS = "gmb_shared_key"

    /** 등록된 키가 없으면 null */
    fun currentKey(): SecretKey? {
        val keyStore = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        return keyStore.getKey(ALIAS, null) as? SecretKey
    }
}
