package com.example.viciousai

import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.telephony.PhoneStateListener
import android.telephony.TelephonyCallback
import android.telephony.TelephonyManager
import android.widget.ImageButton
import android.widget.Toast
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import java.util.concurrent.Executors
import androidx.core.net.toUri
import com.google.firebase.auth.FirebaseAuth

class MainActivity : AppCompatActivity() {

    private var isCallActive = true
    private var callListenerRegistered = false

    private val PERMISSIONS = arrayOf(
        android.Manifest.permission.RECORD_AUDIO,
        android.Manifest.permission.READ_PHONE_STATE
    )

    private val REQUEST_CODE = 100

    // ── TelephonyCallback (Android 12+) ───────────────────────────────────────
    private val telephonyCallback: Any? by lazy {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            object : TelephonyCallback(), TelephonyCallback.CallStateListener {
                override fun onCallStateChanged(state: Int) {
                    handleCallState(state)
                }
            }
        } else null
    }

    // ── PhoneStateListener (< Android 12, fallback) ───────────────────────────
    @Suppress("DEPRECATION")
    private val legacyPhoneStateListener = object : PhoneStateListener() {
        @Deprecated("Deprecated in Java")
        override fun onCallStateChanged(state: Int, phoneNumber: String?) {
            handleCallState(state)
        }
    }

    private fun handleCallState(state: Int) {
        //isCallActive = (state == TelephonyManager.CALL_STATE_OFFHOOK)
    }

    // ── Lifecycle ─────────────────────────────────────────────────────────────

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContentView(R.layout.activity_main)

        ViewCompat.setOnApplyWindowInsetsListener(findViewById(R.id.main)) { v, insets ->
            val systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            v.setPadding(systemBars.left, systemBars.top, systemBars.right, systemBars.bottom)
            insets
        }

        // Ne PAS enregistrer le listener ici — READ_PHONE_STATE peut ne pas
        // être encore accordée. On le fait uniquement si la permission est déjà
        // présente (relancement de l'app après un premier accord).
        if (hasPermission(android.Manifest.permission.READ_PHONE_STATE)) {
            registerCallStateListener()
        }

        findViewById<com.google.android.material.button.MaterialButton>(R.id.startButton)
            .setOnClickListener { handleStartButton() }

        findViewById<ImageButton>(R.id.helpButton)
            .setOnClickListener { showHelpDialog() }

        findViewById<com.google.android.material.button.MaterialButton>(R.id.disconnectButton)
            .setOnClickListener { disconnection() }
    }

    override fun onDestroy() {
        FirebaseAuth.getInstance().signOut()
        super.onDestroy()
        unregisterCallStateListener()
    }

    // ── Permissions ───────────────────────────────────────────────────────────

    private fun hasPermission(permission: String): Boolean =
        checkSelfPermission(permission) == PackageManager.PERMISSION_GRANTED

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)

        if (requestCode != REQUEST_CODE) return

        if (grantResults.all { it == PackageManager.PERMISSION_GRANTED }) {
            // Permissions accordées → on peut maintenant enregistrer le listener
            registerCallStateListener()

            if (isCallActive) {
                launchAnalysis()
            } else {
                Toast.makeText(this, "Pas d'appel en cours", Toast.LENGTH_SHORT).show()
            }
        } else {
            Toast.makeText(
                this,
                "Permissions nécessaires pour démarrer l'analyse",
                Toast.LENGTH_LONG
            ).show()
        }
    }

    // ── Enregistrement / désenregistrement du listener ────────────────────────

    private fun registerCallStateListener() {
        if (callListenerRegistered) return   // évite un double enregistrement
        val telephonyManager = getSystemService(TELEPHONY_SERVICE) as TelephonyManager

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            @Suppress("UNCHECKED_CAST")
            telephonyManager.registerTelephonyCallback(
                Executors.newSingleThreadExecutor(),
                telephonyCallback as TelephonyCallback
            )
        } else {
            @Suppress("DEPRECATION")
            telephonyManager.listen(
                legacyPhoneStateListener,
                PhoneStateListener.LISTEN_CALL_STATE
            )
        }
        callListenerRegistered = true
    }

    private fun unregisterCallStateListener() {
        if (!callListenerRegistered) return
        val telephonyManager = getSystemService(TELEPHONY_SERVICE) as TelephonyManager

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            @Suppress("UNCHECKED_CAST")
            telephonyManager.unregisterTelephonyCallback(telephonyCallback as TelephonyCallback)
        } else {
            @Suppress("DEPRECATION")
            telephonyManager.listen(legacyPhoneStateListener, PhoneStateListener.LISTEN_NONE)
        }
        callListenerRegistered = false
    }

    // ── Navigation ────────────────────────────────────────────────────────────

    private fun disconnection() {
        FirebaseAuth.getInstance().signOut()
        startActivity(Intent(this, LoginActivity::class.java))
        finish()
    }

    private fun launchAnalysis() {
        startActivity(Intent(this, DecisionActivity::class.java))
    }

    // ── Bouton Start ──────────────────────────────────────────────────────────

    private fun handleStartButton() {

        val missing = PERMISSIONS.filter { !hasPermission(it) }

        if (missing.isNotEmpty()) {
            requestPermissions(missing.toTypedArray(), REQUEST_CODE)
            return
        }

        //On ne vérifie plus l'état d'appel (Android bloque)
        launchAnalysis()
    }

    // ── Dialogue d'aide ───────────────────────────────────────────────────────

    private fun showHelpDialog() {
        val message = """
Comment fonctionne Vicious AI ?

Nous analysons l'appel grâce à une intelligence artificielle que nous faisons fonctionner sur nos serveurs afin de garantir le respect de vos données personnelles.

L'analyse fournit un pourcentage de confiance entre 0% et 100% permettant d'évaluer la situation.

IMPORTANT — Permissions :

Si vous refusez les permissions lors du premier lancement, Android enregistre ce choix et l'application ne pourra plus les redemander automatiquement.

Pour les réactiver :

1) Ouvrez les paramètres de votre téléphone
2) Allez dans Applications → Vicious AI
3) Ouvrez l'onglet "Autorisations"
4) Activez Microphone et Téléphone

Sans ces permissions, l'analyse ne pourra pas fonctionner.
        """.trimIndent()

        AlertDialog.Builder(this)
            .setTitle("Aide")
            .setMessage(message)
            .setPositiveButton("Ouvrir les paramètres") { _, _ ->
                val intent = Intent(android.provider.Settings.ACTION_APPLICATION_DETAILS_SETTINGS)
                intent.data = "package:$packageName".toUri()
                startActivity(intent)
            }
            .setNegativeButton("Compris", null)
            .show()
    }
}