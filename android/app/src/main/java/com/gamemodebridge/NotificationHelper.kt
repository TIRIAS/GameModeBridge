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

    /** 키워드 없는 서비스 시작 알림 (루틴이 반응하지 않음). 마지막 상태는 바꾸지 않음 */
    fun postServiceStart(): NotifyResult

    /** 마지막으로 게시한 키워드 알림의 상태. 게시한 적이 없으면 null */
    fun lastState(): GameState?
}

class AndroidNotificationHelper(private val context: Context) : NotificationHelper {

    private val manager = context.getSystemService(NotificationManager::class.java)
    private val prefs = context.getSharedPreferences("gmb_notify", Context.MODE_PRIVATE)

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
            .build()
        // 자동 삭제하지 않음. 이전 알림을 지우고 새로 게시하여 마지막 상태 하나만 남김.
        // 같은 알림을 덮어쓰면(업데이트) 루틴이 새 알림으로 감지하지 않을 수 있으므로 지운 뒤 게시함
        cancelAll()
        manager.notify(if (state == GameState.ON) ID_ON else ID_OFF, notification)
        prefs.edit().putString(KEY_LAST_STATE, state.name).commit()
        return NotifyResult.POSTED
    }

    override fun postServiceStart(): NotifyResult {
        if (!manager.areNotificationsEnabled()) return NotifyResult.BLOCKED
        // 루틴 키워드를 넣지 않음. 이미 꺼진 상태이므로 게임 모드 끄기 루틴을 다시 실행할 필요가 없음
        val notification = Notification.Builder(context, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_stat_gmb)
            .setContentTitle("GameModeBridge 서비스 시작")
            .setContentText("PC 감지가 시작되었습니다. 게임 모드는 꺼진 상태입니다")
            .setVisibility(Notification.VISIBILITY_PRIVATE)
            .build()
        cancelAll()
        manager.notify(ID_SERVICE_START, notification)
        return NotifyResult.POSTED
    }

    override fun lastState(): GameState? =
        prefs.getString(KEY_LAST_STATE, null)?.let { runCatching { GameState.valueOf(it) }.getOrNull() }

    private fun cancelAll() {
        manager.cancel(ID_ON)
        manager.cancel(ID_OFF)
        manager.cancel(ID_SERVICE_START)
    }

    fun isEnabled(): Boolean = manager.areNotificationsEnabled()

    private companion object {
        const val CHANNEL_ID = "gmb_state"
        const val ID_ON = 1
        const val ID_OFF = 2
        const val ID_SERVICE_START = 3
        const val KEY_LAST_STATE = "last_state"
    }
}
