package com.gamemodebridge

import android.app.Activity
import android.os.Bundle
import android.widget.Button
import android.widget.TextView

/**
 * 디버그 전용 시뮬레이션 화면 (CLAUDE.md 7장).
 * 가짜 암호화 메시지를 실제 수신 처리 경로(MessageProcessor)에 그대로 넣음.
 * 시뮬레이터 전용 테스트 키와 별도 순번 저장소를 사용하여 실제 등록 정보에 영향을 주지 않음
 */
class SimulatorActivity : Activity() {

    private val key = EnvelopeFactory.newTestKey()
    private val factory = EnvelopeFactory(key)
    private lateinit var seqStore: PrefsSeqStore
    private lateinit var processor: MessageProcessor
    private lateinit var log: TextView
    private var lastMessage: Map<String, String>? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_simulator)
        seqStore = PrefsSeqStore(this, "gmb_sim_seq")
        // 키를 실행마다 새로 만들므로 순번도 처음부터 시작함
        seqStore.save(0)
        processor = MessageProcessor(AesGcmCryptoManager(key), seqStore, AndroidNotificationHelper(this))
        log = findViewById(R.id.simLog)

        button(R.id.simOn) { send("정상 켜기", factory.message("on", "시뮬레이터 게임", now(), nextSeq())) }
        button(R.id.simOff) { send("정상 끄기", factory.message("off", "시뮬레이터 게임", now(), nextSeq())) }
        button(R.id.simStale) { send("오래된 메시지", factory.message("on", "오래된 게임", now() - 300, nextSeq())) }
        button(R.id.simReplay) {
            val previous = lastMessage
            if (previous == null) append("재전송: 먼저 정상 메시지를 보내세요") else send("재전송", previous)
        }
        button(R.id.simReorder) {
            // 순번 n+1(켜기)과 n+2(끄기)를 만들고 n+2를 먼저 처리함. n+1은 폐기되어야 정상
            val base = seqStore.last()
            val on = factory.message("on", "순서 역전 게임", now(), base + 1)
            val off = factory.message("off", "순서 역전 게임", now(), base + 2)
            send("순서 역전 (끄기 먼저 도착)", off)
            send("순서 역전 (늦게 온 켜기)", on)
        }
        button(R.id.simTamper) {
            send("위변조", EnvelopeFactory.tamper(factory.message("on", "위변조 게임", now(), nextSeq())))
        }
    }

    private fun send(label: String, message: Map<String, String>) {
        val result = processor.process(message)
        // 재전송 버튼은 마지막으로 정상 처리된 메시지를 다시 보내야 순번 검사를 확인할 수 있음
        if (result is ProcessResult.Accepted) lastMessage = message
        append("$label → ${result.describe()}")
    }

    private fun append(line: String) {
        log.text = "$line\n${log.text}"
    }

    private fun button(id: Int, action: () -> Unit) = findViewById<Button>(id).setOnClickListener { action() }

    private fun nextSeq() = seqStore.last() + 1

    private fun now() = System.currentTimeMillis() / 1000
}
