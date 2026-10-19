package com.gamemodebridge

import android.util.Log
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage

/**
 * FCM 데이터 메시지 수신 서비스.
 * 서비스: 화면 없이 백그라운드에서 동작하는 안드로이드 구성 요소. FCM 메시지가 오면 시스템이 실행함
 */
class GameModeMessagingService : FirebaseMessagingService() {

    override fun onMessageReceived(message: RemoteMessage) {
        val status = StatusStore(this)
        val key = KeyStoreManager.currentKey()
        if (key == null) {
            // 기기 등록(4단계) 전에는 복호화할 키가 없음
            Log.i(TAG, "폐기: NOT_REGISTERED")
            status.record("폐기: NOT_REGISTERED (기기 등록 전)")
            return
        }
        val processor = MessageProcessor(AesGcmCryptoManager(key), PrefsSeqStore(this), AndroidNotificationHelper(this))
        val result = processor.process(message.data)
        // 폐기 시 사유 코드만 남기고 메시지 내용은 남기지 않음
        if (result is ProcessResult.Discarded) Log.i(TAG, "폐기: ${result.reason}")
        status.record(result.describe())
    }

    // 토픽 방식이므로 등록 토큰(onNewToken)은 다루지 않음

    private companion object {
        const val TAG = "GameModeBridge"
    }
}
