package com.example.viciousai

import android.content.Intent
import android.os.Bundle
import android.widget.Button
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity

class LoginActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContentView(R.layout.activity_login)

        val loginButton = findViewById<Button>(R.id.loginButton)

        loginButton.setOnClickListener {
            startActivity(Intent(this, MainActivity::class.java))
            finish()
        }

        val inscriptionButton = findViewById<Button>(R.id.registerButton)

        inscriptionButton.setOnClickListener {
            startActivity(Intent(this, RegisterActivity::class.java))
            finish()
        }
    }
}