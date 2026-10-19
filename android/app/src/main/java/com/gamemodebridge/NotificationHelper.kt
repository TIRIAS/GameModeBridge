package com.gamemodebridge

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context

// 루틴 키워드 (PC 쪽과 같아야 함). 서로 포함 관계가 없도록 유지함
const val KEYWORD_ON = "GAMEMODE_ON"
const val KEYWORD_OFF = "GAMEMODE_OFF"

enum class GameState { ON, OFF }

enum class NotifyResult { POSTED, BLOCKED }

/** 루틴 키워드 알림 게시. 테스트에서는 가짜 구현을 주입함 */
interface NotificationHelper {
    fun post(state: GameState, text: String): NotifyResult
}

class AndroidNotificationHelper(private val context: Context) : NotificationHelper {

    private val manager = context.getSystemService(NotificationManager::class.java)

    init {
        // 알림 채널: 사용자가 설정에서 종류별로 알림을 켜고 끌 수 있는 단위.
        // 루틴 감지 검증을 생략했으므로 감지 가능성이 높은 기본 중요도를 사용함
        val channel = NotificationChannel(CHANNEL_ID, "게임 모드 신호", NotificationManager.IMPORTANCE_DEFAULT)
        channel.lockscreenVisibility = Notification.VISIBILITY_PRIVATE
        manager.createNotificationChannel(channel)
    }

    override fun post(state: GameState, text: String): NotifyResult {
        if (!manager.areNotificationsEnabled()) return NotifyResult.BLOCKED
        val title = if (state == GameState.ON) KEYWORD_ON else KEYWORD_OFF
        val notification = Notification.Builder(context, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_stat_gmb)
            .setContentTitle(title)
            .setContentText(text)
            .setVisibility(Notification.VISIBILITY_PRIVATE)
            // 루틴이 인식할 시간을 두고 자동 삭제함 (CLAUDE.md 5장)
            .setTimeoutAfter(AUTO_CANCEL_MS)
            .build()
        manager.notify(if (state == GameState.ON) ID_ON else ID_OFF, notification)
        return NotifyResult.POSTED
    }

    fun isEnabled(): Boolean = manager.areNotificationsEnabled()

    private companion object {
        const val CHANNEL_ID = "gmb_state"
        const val ID_ON = 1
        const val ID_OFF = 2
        const val AUTO_CANCEL_MS = 5_000L
    }
}
