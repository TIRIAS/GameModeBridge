package com.gamemodebridge

import android.app.Activity
import android.app.AlertDialog
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import com.google.mlkit.vision.barcode.common.Barcode
import com.google.mlkit.vision.codescanner.GmsBarcodeScannerOptions
import com.google.mlkit.vision.codescanner.GmsBarcodeScanning

/**
 * QR 기기 등록 화면 (CLAUDE.md 6장).
 * Google 코드 스캐너는 Google Play 서비스가 카메라 화면을 대신 띄우므로 앱에 카메라 권한이 필요 없음
 */
class RegistrationActivity : Activity() {

    private lateinit var registration: DeviceRegistration
    private lateinit var result: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_registration)
        registration = DeviceRegistration.create(this)
        result = findViewById(R.id.regResult)

        findViewById<Button>(R.id.scanQr).setOnClickListener { scan() }

        val input = findViewById<EditText>(R.id.manualInput)
        findViewById<Button>(R.id.submitManual).setOnClickListener {
            val text = input.text.toString()
            input.text.clear()
            register(text)
        }

        findViewById<Button>(R.id.revoke).setOnClickListener {
            AlertDialog.Builder(this)
                .setTitle("긴급 재등록")
                .setMessage("키 유출이나 기기 분실 시 사용합니다.\n기존 키와 토픽을 즉시 삭제하며, 새로 등록할 때까지 PC 신호를 받을 수 없습니다.")
                .setPositiveButton("삭제") { _, _ ->
                    registration.revoke()
                    result.text = "기존 연결을 삭제했습니다. PC에서 register --revoke 를 실행한 뒤 QR을 스캔하세요."
                    refresh()
                }
                .setNegativeButton("취소", null)
                .show()
        }
        refresh()
    }

    private fun scan() {
        val options = GmsBarcodeScannerOptions.Builder().setBarcodeFormats(Barcode.FORMAT_QR_CODE).build()
        GmsBarcodeScanning.getClient(this, options).startScan()
            .addOnSuccessListener { barcode -> register(barcode.rawValue.orEmpty()) }
            .addOnFailureListener { result.text = "스캐너를 실행할 수 없습니다. 문자열 직접 입력을 사용하세요." }
    }

    private fun register(text: String) {
        val qr = QrPayload.parse(text)
        if (qr == null) {
            result.text = "등록 정보 형식이 올바르지 않습니다. 기존 연결은 그대로 유지됩니다."
            return
        }
        result.text = "새 토픽 구독 중..."
        registration.beginPending(qr) { ok ->
            result.text = if (ok) {
                "새 토픽 구독 성공.\n이제 PC 등록 창에서 [휴대폰 등록 완료]를 누르세요."
            } else {
                "새 토픽 구독 실패. 인터넷 연결을 확인한 뒤 다시 시도하세요. 기존 연결은 그대로 유지됩니다."
            }
            refresh()
        }
    }

    private fun refresh() {
        val s = registration.state()
        val active = if (s.activeTopic != null) "등록됨 (${mask(s.activeTopic)})" else "등록 안 됨"
        val pending = if (s.pendingTopic != null) "\n확정 대기 중인 새 등록: ${mask(s.pendingTopic)} (PC가 새 키로 첫 메시지를 보내면 확정됨)" else ""
        findViewById<TextView>(R.id.regState).text = "현재 연결: $active$pending"
    }

    // 토픽 전체를 화면에 드러내지 않음
    private fun mask(topic: String) = topic.take(8) + "…"
}
