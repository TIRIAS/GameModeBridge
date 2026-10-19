package com.gamemodebridge

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.view.View
import android.widget.Button
import android.widget.TextView

class MainActivity : Activity() {

    private lateinit var notifier: AndroidNotificationHelper
    private lateinit var status: StatusStore

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        notifier = AndroidNotificationHelper(this)
        status = StatusStore(this)

        // PC 비정상 종료 등으로 게임 모드가 남아 있을 때 수동 복구용
        findViewById<Button>(R.id.manualOff).setOnClickListener {
            val result = notifier.post(GameState.OFF, "수동 끄기")
            status.record(if (result == NotifyResult.POSTED) "수동 끄기: 알림 게시 요청 완료" else "수동 끄기: 알림 권한 차단")
            refresh()
        }

        findViewById<Button>(R.id.openRegistration).setOnClickListener {
            startActivity(Intent(this, RegistrationActivity::class.java))
        }

        findViewById<Button>(R.id.requestPermission).setOnClickListener { requestNotificationPermission() }

        // 배터리 최적화 예외 목록 화면을 엶 (별도 권한이 필요 없는 방식)
        findViewById<Button>(R.id.batterySettings).setOnClickListener {
            startActivity(Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS))
        }

        // 시뮬레이터는 debug 빌드에만 있으므로 존재할 때만 버튼을 보여줌
        val simulator = Intent().setClassName(this, SIMULATOR_CLASS)
        if (packageManager.resolveActivity(simulator, 0) != null) {
            findViewById<Button>(R.id.openSimulator).apply {
                visibility = View.VISIBLE
                setOnClickListener { startActivity(simulator) }
            }
        }

        if (!notifier.isEnabled()) requestNotificationPermission()
    }

    override fun onResume() {
        super.onResume()
        refresh()
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        refresh()
    }

    private fun refresh() {
        val reg = PrefsRegStateStore(this).load()
        findViewById<TextView>(R.id.registrationStatus).text = when {
            reg.activeTopic != null && reg.pendingTopic != null -> "기기 등록: 등록됨, 새 등록 확정 대기 중"
            reg.activeTopic != null -> "기기 등록: 등록됨"
            reg.pendingTopic != null -> "기기 등록: 확정 대기 중 (PC의 첫 메시지 수신 시 확정)"
            else -> "기기 등록: 등록 안 됨"
        }
        findViewById<TextView>(R.id.permissionStatus).text =
            if (notifier.isEnabled()) "알림 권한: 허용됨" else "알림 권한: 차단됨 (알림을 띄울 수 없음)"
        findViewById<TextView>(R.id.lastResult).text = "마지막 처리: ${status.last()}"
    }

    // Android 13 이상은 알림을 띄우려면 사용자 허용이 필요함. 이미 거부했다면 앱 알림 설정 화면을 엶
    private fun requestNotificationPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED &&
            !hasRequestedBefore()
        ) {
            markRequested()
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 0)
        } else if (!notifier.isEnabled()) {
            startActivity(Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS).putExtra(Settings.EXTRA_APP_PACKAGE, packageName))
        }
    }

    private fun hasRequestedBefore() = getPreferences(MODE_PRIVATE).getBoolean(KEY_REQUESTED, false)

    private fun markRequested() = getPreferences(MODE_PRIVATE).edit().putBoolean(KEY_REQUESTED, true).apply()

    private companion object {
        const val SIMULATOR_CLASS = "com.gamemodebridge.SimulatorActivity"
        const val KEY_REQUESTED = "notification_permission_requested"
    }
}
