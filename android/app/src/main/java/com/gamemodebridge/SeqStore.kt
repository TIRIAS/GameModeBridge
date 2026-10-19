package com.gamemodebridge

import android.content.Context

/** 마지막으로 처리한 메시지 순번 보존 (CLAUDE.md 5장 순번 규칙) */
interface SeqStore {
    /** 처리한 메시지가 없으면 0 */
    fun last(): Long
    fun save(seq: Long)
}

/** 순번은 비밀 정보가 아니므로 일반 앱 저장소(SharedPreferences)에 둠 */
class PrefsSeqStore(context: Context, prefsName: String = "gmb_seq") : SeqStore {
    private val prefs = context.getSharedPreferences(prefsName, Context.MODE_PRIVATE)

    override fun last(): Long = prefs.getLong(KEY, 0L)

    // commit(): 알림 게시 전에 디스크 저장을 끝내기 위해 동기 저장함
    override fun save(seq: Long) {
        prefs.edit().putLong(KEY, seq).commit()
    }

    private companion object {
        const val KEY = "last_seq"
    }
}
