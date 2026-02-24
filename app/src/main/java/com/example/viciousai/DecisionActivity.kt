package com.example.viciousai

import android.graphics.Color
import android.os.Bundle
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import com.google.android.material.button.MaterialButton

class DecisionActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.decision_layout)

        val confidenceText = findViewById<TextView>(R.id.confidenceText)
        val stopButton = findViewById<MaterialButton>(R.id.stopButton)

        // Exemple : valeur simulée
        val confidence = (0..100).random()

        confidenceText.text = "$confidence%"

        // Couleur dynamique
        when {
            confidence < 40 -> confidenceText.setTextColor(Color.RED)
            confidence <= 60 -> confidenceText.setTextColor(Color.parseColor("#FFA500"))
            else -> confidenceText.setTextColor(Color.parseColor("#4CAF50"))
        }

        // Bouton retour
        stopButton.setOnClickListener {
            finish()
        }
    }
}
