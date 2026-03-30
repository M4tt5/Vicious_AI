package com.example.viciousai

import android.media.MediaRecorder
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.view.View
import android.widget.ProgressBar
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import com.google.android.material.button.MaterialButton
import com.google.firebase.auth.FirebaseAuth
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.asRequestBody
import org.json.JSONObject
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.UUID
import java.util.concurrent.TimeUnit

class DecisionActivity : AppCompatActivity() {

    // ── Constantes ────────────────────────────────────────────────────────────
    companion object {
        private const val TAG              = "ViciousAI_Audio"
        private const val SEGMENT_DURATION = 5_000L
        private const val SAMPLE_RATE      = 44_100
        private const val BIT_RATE         = 128_000

        // 🔧 Remplace par ton IP locale, ex: "http://192.168.1.42:8000"
        private const val SERVER_URL = "http://192.168.X.X:8000"
    }

    // ── État ──────────────────────────────────────────────────────────────────
    private var isRecording  = false
    private var segmentIndex = 0
    private var recorder: MediaRecorder? = null
    private var currentFile: File? = null
    private val sessionId = UUID.randomUUID().toString()

    // ── HTTP ──────────────────────────────────────────────────────────────────
    private val httpClient = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .build()

    // ── Handler pour la boucle de segmentation ────────────────────────────────
    private val handler = Handler(Looper.getMainLooper())
    private val segmentRunnable = object : Runnable {
        override fun run() {
            if (isRecording) {
                rotateSegment()
                handler.postDelayed(this, SEGMENT_DURATION)
            }
        }
    }

    // ── Vues ──────────────────────────────────────────────────────────────────
    private lateinit var statusText:       TextView
    private lateinit var segmentText:      TextView
    private lateinit var scoreText:        TextView
    private lateinit var transcriptText:   TextView
    private lateinit var reasoningText:    TextView
    private lateinit var scoreProgress:    ProgressBar
    private lateinit var uploadSpinner:    ProgressBar
    private lateinit var startButton:      MaterialButton
    private lateinit var stopButton:       MaterialButton

    // ── Badges tactiques ──────────────────────────────────────────────────────
    private lateinit var badgeUrgency:       TextView
    private lateinit var badgeAuthority:     TextView
    private lateinit var badgeSensitive:     TextView
    private lateinit var badgeImpersonation: TextView

    // ── Lifecycle ─────────────────────────────────────────────────────────────

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_decision)

        statusText       = findViewById(R.id.statusText)
        segmentText      = findViewById(R.id.segmentText)
        scoreText        = findViewById(R.id.scoreText)
        transcriptText   = findViewById(R.id.transcriptText)
        reasoningText    = findViewById(R.id.reasoningText)
        scoreProgress    = findViewById(R.id.scoreProgress)
        uploadSpinner    = findViewById(R.id.uploadSpinner)
        startButton      = findViewById(R.id.startRecordingButton)
        stopButton       = findViewById(R.id.stopRecordingButton)
        badgeUrgency     = findViewById(R.id.badgeUrgency)
        badgeAuthority   = findViewById(R.id.badgeAuthority)
        badgeSensitive   = findViewById(R.id.badgeSensitive)
        badgeImpersonation = findViewById(R.id.badgeImpersonation)

        stopButton.isEnabled     = false
        uploadSpinner.visibility = View.GONE

        startButton.setOnClickListener { startRecordingLoop() }
        stopButton.setOnClickListener  { stopRecordingLoop()  }

        Log.i(TAG, "Session ID : $sessionId")

        //----- Pour obtenir un token de session pour les test serveur ------
        //FirebaseAuth.getInstance().currentUser?.getIdToken(false)
        //    ?.addOnSuccessListener { result ->
        //        Log.d("TOKEN_TEST", "idToken : ${result.token}")
        //    }
    }

    override fun onDestroy() {
        super.onDestroy()
        if (isRecording) stopRecordingLoop()
    }

    // ── Token Firebase ────────────────────────────────────────────────────────

    private fun getFirebaseToken(onToken: (String?) -> Unit) {
        val user = FirebaseAuth.getInstance().currentUser
        if (user == null) {
            onToken(null)
            return
        }
        user.getIdToken(false)
            .addOnSuccessListener { result -> onToken(result.token) }
            .addOnFailureListener { onToken(null) }
    }

    // ── Logique d'enregistrement ──────────────────────────────────────────────

    private fun startRecordingLoop() {
        isRecording  = true
        segmentIndex = 0

        startButton.isEnabled = false
        stopButton.isEnabled  = true
        statusText.text       = "Enregistrement en cours…"
        transcriptText.text   = ""
        reasoningText.text    = ""
        resetBadges()

        Log.i(TAG, "═══ Démarrage session $sessionId ═══")

        startNewSegment()
        handler.postDelayed(segmentRunnable, SEGMENT_DURATION)
    }

    private fun stopRecordingLoop() {
        isRecording = false
        handler.removeCallbacks(segmentRunnable)

        val lastFile = stopAndReleaseRecorder()

        startButton.isEnabled = false
        stopButton.isEnabled  = false
        statusText.text       = "Finalisation…"
        segmentText.text      = ""

        if (lastFile != null) {
            uploadSegment(lastFile, onComplete = { endSession() })
        } else {
            endSession()
        }
    }

    private fun rotateSegment() {
        val finishedFile = stopAndReleaseRecorder()
        finishedFile?.let { uploadSegment(it, onComplete = null) }
        startNewSegment()
    }

    private fun startNewSegment() {
        segmentIndex++
        val file = File(getOutputDir(), "segment_${segmentIndex}_${timestamp()}.m4a")
        currentFile = file
        recorder    = createRecorder(file).also { it.start() }
        Log.d(TAG, "▶ Segment #$segmentIndex démarré → ${file.name}")
        segmentText.text = "Segment #$segmentIndex en cours…"
    }

    private fun stopAndReleaseRecorder(): File? {
        val savedFile = currentFile
        return try {
            recorder?.apply { stop(); release() }
            Log.d(TAG, "■ Segment #$segmentIndex sauvegardé (${savedFile?.length()?.div(1024)} Ko)")
            savedFile
        } catch (e: RuntimeException) {
            Log.e(TAG, "✘ Erreur stop segment #$segmentIndex : ${e.message}")
            savedFile?.delete()
            null
        } finally {
            recorder    = null
            currentFile = null
        }
    }

    // ── Envoi d'un segment au serveur ─────────────────────────────────────────

    private fun uploadSegment(file: File, onComplete: (() -> Unit)?) {
        val segNum = segmentIndex

        getFirebaseToken { token ->
            if (token == null) {
                Log.e(TAG, "Segment #$segNum — token Firebase indisponible")
                onComplete?.invoke()
                return@getFirebaseToken
            }

            CoroutineScope(Dispatchers.IO).launch {
                withContext(Dispatchers.Main) { uploadSpinner.visibility = View.VISIBLE }

                try {
                    val requestBody = MultipartBody.Builder()
                        .setType(MultipartBody.FORM)
                        .addFormDataPart(
                            "file", file.name,
                            file.asRequestBody("audio/mp4".toMediaTypeOrNull())
                        )
                        .addFormDataPart("session_id", sessionId)
                        .build()

                    val request = Request.Builder()
                        .url("$SERVER_URL/stream-audio")
                        .addHeader("Authorization", "Bearer $token")
                        .post(requestBody)
                        .build()

                    val response = httpClient.newCall(request).execute()
                    val body     = response.body?.string() ?: ""

                    Log.d(TAG, "Segment #$segNum réponse [${response.code}] : $body")

                    if (response.isSuccessful) {
                        val json               = JSONObject(body)
                        val fullTranscription  = json.optString("full_transcription", "")
                        val chunkTranscription = json.optString("chunk_transcription", "")
                        val analysis           = json.optJSONObject("chunk_analysis")

                        handleChunkResult(segNum, fullTranscription, chunkTranscription, analysis)
                    } else {
                        Log.e(TAG, "Segment #$segNum erreur serveur : ${response.code}")
                    }

                } catch (e: Exception) {
                    Log.e(TAG, "Segment #$segNum échec réseau : ${e.message}")
                } finally {
                    file.delete()
                    withContext(Dispatchers.Main) {
                        uploadSpinner.visibility = View.GONE
                        onComplete?.invoke()
                    }
                }
            }
        }
    }

    // ── Fin de session ────────────────────────────────────────────────────────

    private fun endSession() {
        getFirebaseToken { token ->
            if (token == null) {
                Log.e(TAG, "End-session — token Firebase indisponible")
                runOnUiThread {
                    statusText.text       = "Erreur d'authentification"
                    startButton.isEnabled = true
                }
                return@getFirebaseToken
            }

            CoroutineScope(Dispatchers.IO).launch {
                try {
                    val requestBody = MultipartBody.Builder()
                        .setType(MultipartBody.FORM)
                        .addFormDataPart("session_id", sessionId)
                        .build()

                    val request = Request.Builder()
                        .url("$SERVER_URL/end-session")
                        .addHeader("Authorization", "Bearer $token")
                        .post(requestBody)
                        .build()

                    val response = httpClient.newCall(request).execute()
                    val body     = response.body?.string() ?: ""

                    Log.i(TAG, "End-session [${response.code}] : $body")

                    if (response.isSuccessful) {
                        val json         = JSONObject(body)
                        val globalScore  = json.optInt("global_risk_score", -1)
                        val fullText     = json.optString("full_transcription", "")
                        val lastAnalysis = json.optJSONObject("last_analysis")
                        val reasoning    = lastAnalysis?.optString("reasoning", "") ?: ""
                        val tactics      = lastAnalysis?.optJSONObject("tactics_detected")

                        Log.i(TAG, "Score final : $globalScore")

                        withContext(Dispatchers.Main) {
                            statusText.text       = "Analyse terminée"
                            startButton.isEnabled = true
                            updateScoreUI(
                                score      = globalScore,
                                transcript = fullText,
                                reasoning  = reasoning,
                                tactics    = tactics,
                                isFinal    = true
                            )
                        }
                    } else {
                        withContext(Dispatchers.Main) {
                            statusText.text       = "Erreur serveur (${response.code})"
                            startButton.isEnabled = true
                        }
                    }

                } catch (e: Exception) {
                    Log.e(TAG, "End-session échec : ${e.message}")
                    withContext(Dispatchers.Main) {
                        statusText.text       = "Erreur réseau"
                        startButton.isEnabled = true
                    }
                }
            }
        }
    }

    // ── Mise à jour de l'UI ───────────────────────────────────────────────────

    private fun handleChunkResult(
        segNum: Int,
        fullTranscription: String,
        chunkTranscription: String,
        analysis: JSONObject?
    ) {
        if (analysis == null) return

        val score    = analysis.optInt("risk_score", -1)
        val reasoning = analysis.optString("reasoning", "")
        val tactics  = analysis.optJSONObject("tactics_detected")

        Log.i(TAG, "Segment #$segNum — score: $score | chunk: \"$chunkTranscription\"")

        CoroutineScope(Dispatchers.Main).launch {
            segmentText.text = "Segment #$segNum analysé"
            updateScoreUI(
                score      = score,
                transcript = fullTranscription,
                reasoning  = reasoning,
                tactics    = tactics,
                isFinal    = false
            )
        }
    }

    private fun updateScoreUI(
        score: Int,
        transcript: String,
        reasoning: String,
        tactics: JSONObject?,
        isFinal: Boolean
    ) {
        if (score < 0) return

        // Score et barre
        scoreProgress.progress = score
        scoreText.text = if (isFinal) "Score final : $score%" else "Score de risque : $score%"

        val color = when {
            score >= 70 -> getColor(android.R.color.holo_red_light)
            score >= 40 -> getColor(android.R.color.holo_orange_light)
            else        -> getColor(android.R.color.holo_green_light)
        }
        scoreText.setTextColor(color)

        // Transcription et raisonnement
        if (transcript.isNotBlank()) transcriptText.text = transcript
        if (reasoning.isNotBlank())  reasoningText.text  = reasoning

        // Badges tactiques
        tactics?.let { updateTacticsBadges(it) }
    }

    // ── Gestion des badges ────────────────────────────────────────────────────

    private fun updateTacticsBadges(tactics: JSONObject) {
        setBadge(badgeUrgency,       tactics.optBoolean("urgency",              false))
        setBadge(badgeAuthority,     tactics.optBoolean("authority",            false))
        setBadge(badgeSensitive,     tactics.optBoolean("sensitive_information",false))
        setBadge(badgeImpersonation, tactics.optBoolean("impersonation",        false))
    }

    private fun setBadge(badge: TextView, active: Boolean) {
        if (active) {
            badge.setBackgroundResource(R.drawable.badge_active)
            badge.setTextColor(getColor(android.R.color.holo_red_light))
        } else {
            badge.setBackgroundResource(R.drawable.badge_inactive)
            badge.setTextColor(0xFF888888.toInt())
        }
    }

    private fun resetBadges() {
        listOf(badgeUrgency, badgeAuthority, badgeSensitive, badgeImpersonation).forEach {
            it.setBackgroundResource(R.drawable.badge_inactive)
            it.setTextColor(0xFF888888.toInt())
        }
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private fun getOutputDir(): File =
        File(filesDir, "audio_segments").also { if (!it.exists()) it.mkdirs() }

    private fun timestamp(): String =
        SimpleDateFormat("HHmmss", Locale.getDefault()).format(Date())

    private fun createRecorder(outputFile: File): MediaRecorder =
        MediaRecorder(this).apply {
            setAudioSource(MediaRecorder.AudioSource.MIC)
            setOutputFormat(MediaRecorder.OutputFormat.MPEG_4)
            setAudioEncoder(MediaRecorder.AudioEncoder.AAC)
            setAudioSamplingRate(SAMPLE_RATE)
            setAudioEncodingBitRate(BIT_RATE)
            setOutputFile(outputFile.absolutePath)
            prepare()
        }
}