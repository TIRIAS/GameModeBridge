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
        val result = DeviceRegistration.create(this).handleMessage(message.from, message.data)
        // 처리 결과(사유 코드)만 남기고 메시지 내용은 남기지 않음. 로그 시각은 전달 지연 측정에 사용함
        Log.i(TAG, "수신 처리: ${result.describe()}")
        StatusStore(this).record(result.describe())
    }

    // 토픽 방식이므로 등록 토큰(onNewToken)은 다루지 않음

    private companion object {
        const val TAG = "GameModeBridge"
    }
}
