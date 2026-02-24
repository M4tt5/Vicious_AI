package com.example.viciousai

import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Bundle
import android.widget.ImageButton
import android.widget.Toast
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat

class MainActivity : AppCompatActivity() {
    private val PERMISSIONS = arrayOf(
        android.Manifest.permission.RECORD_AUDIO,
        android.Manifest.permission.READ_PHONE_STATE
    )

    private val REQUEST_CODE = 100

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContentView(R.layout.activity_main)
        ViewCompat.setOnApplyWindowInsetsListener(findViewById(R.id.main)) { v, insets ->
            val systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            v.setPadding(systemBars.left, systemBars.top, systemBars.right, systemBars.bottom)
            insets
        }

        findViewById<com.google.android.material.button.MaterialButton>(R.id.startButton)
            .setOnClickListener {
                startAnalysis()
            }

        findViewById<ImageButton>(R.id.helpButton).setOnClickListener {
            showHelpDialog()
        }

        findViewById<com.google.android.material.button.MaterialButton>(R.id.disconnectButton).setOnClickListener {
            disconnection()
        }
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)

        if (requestCode == REQUEST_CODE) {
            if (grantResults.all { it == PackageManager.PERMISSION_GRANTED }) {
                launchAnalysis()
            } else {
                Toast.makeText(
                    this,
                    "Permissions nécessaires pour démarrer l'analyse",
                    Toast.LENGTH_LONG
                ).show()
            }
        }
    }

    private fun disconnection() {
        val intent = Intent(this, LoginActivity::class.java)
        startActivity(intent)

        // ferme l'activité actuelle pour empêcher retour avec bouton back
        finish()
    }

    private fun startAnalysis() {
        val missing = PERMISSIONS.filter {
            checkSelfPermission(it) != PackageManager.PERMISSION_GRANTED
        }

        if (missing.isNotEmpty()) {
            requestPermissions(missing.toTypedArray(), REQUEST_CODE)
        } else {
            launchAnalysis()
        }
    }

    private fun launchAnalysis() {
        val intent = Intent(this, DecisionActivity::class.java)
        startActivity(intent)
    }

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
                intent.data = Uri.parse("package:$packageName")
                startActivity(intent)
            }
            .setNegativeButton("Compris", null)
            .show()
    }

}