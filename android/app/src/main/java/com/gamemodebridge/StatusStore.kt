package com.gamemodebridge

import android.content.Context
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * 메인 화면에 표시할 마지막 처리 결과 저장.
 * 앱이 확인할 수 있는 범위(검증, 알림 게시 요청)까지만 기록함. 실제 모드 전환 여부는 알 수 없음
 */
class StatusStore(context: Context) {
    private val prefs = context.getSharedPreferences("gmb_status", Context.MODE_PRIVATE)

    fun record(text: String) {
        val time = SimpleDateFormat("MM-dd HH:mm:ss", Locale.KOREA).format(Date())
        prefs.edit().putString(KEY, "$time  $text").apply()
    }

    fun last(): String = prefs.getString(KEY, null) ?: "수신 기록 없음"

    private companion object {
        const val KEY = "last_result"
    }
}

/** 처리 결과를 화면 표시용 문구로 바꿈 (메시지 내용은 넣지 않음) */
fun ProcessResult.describe(): String = when (this) {
    is ProcessResult.Accepted -> if (serviceStart) {
        when (notify) {
            NotifyResult.POSTED -> "서비스 시작: 메시지 검증 완료, 이미 꺼진 상태라 키워드 없이 알림"
            NotifyResult.BLOCKED -> "서비스 시작: 메시지 검증 완료, 알림 권한 차단"
        }
    } else {
        val label = if (state == GameState.ON) "켜기" else "끄기"
        when (notify) {
            NotifyResult.POSTED -> "$label: 메시지 검증 완료, 알림 게시 요청 완료"
            NotifyResult.BLOCKED -> "$label: 메시지 검증 완료, 알림 권한 차단"
        }
    }
    is ProcessResult.Discarded -> "폐기: ${reason.name}"
}
