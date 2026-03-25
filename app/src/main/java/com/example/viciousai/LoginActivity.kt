package com.example.viciousai

import android.content.Intent
import android.os.Bundle
import android.util.Patterns
import android.widget.Toast
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import com.google.android.material.button.MaterialButton
import com.google.android.material.textfield.TextInputEditText
import com.google.android.material.textfield.TextInputLayout
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.auth.FirebaseAuthInvalidCredentialsException
import com.google.firebase.auth.FirebaseAuthInvalidUserException

class LoginActivity : AppCompatActivity() {

    private lateinit var auth: FirebaseAuth

    // ── Vues ──────────────────────────────────────────────────────────────────
    private lateinit var emailLayout:    TextInputLayout
    private lateinit var passwordLayout: TextInputLayout
    private lateinit var emailEdit:      TextInputEditText
    private lateinit var passwordEdit:   TextInputEditText
    private lateinit var loginButton:    MaterialButton
    private lateinit var registerButton: MaterialButton

    // ── Lifecycle ─────────────────────────────────────────────────────────────

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContentView(R.layout.activity_login)

        auth = FirebaseAuth.getInstance()

        emailLayout    = findViewById(R.id.emailLayout)
        passwordLayout = findViewById(R.id.passwordLayout)
        emailEdit      = emailLayout.editText    as TextInputEditText
        passwordEdit   = passwordLayout.editText as TextInputEditText
        loginButton    = findViewById(R.id.loginButton)
        registerButton = findViewById(R.id.registerButton)

        loginButton.setOnClickListener    { handleLogin()    }
        registerButton.setOnClickListener {
            startActivity(Intent(this, RegisterActivity::class.java))
            finish()
        }
    }

    override fun onStart() {
        super.onStart()
        // Redirige directement si déjà connecté
        if (FirebaseAuth.getInstance().currentUser != null) {
            startActivity(Intent(this, MainActivity::class.java))
            finish()
        }
    }

    // ── Connexion ─────────────────────────────────────────────────────────────

    private fun handleLogin() {
        emailLayout.error    = null
        passwordLayout.error = null

        val email    = emailEdit.text.toString().trim()
        val password = passwordEdit.text.toString()   // pas de trim() sur le mot de passe

        // Validation locale
        if (!validateInputs(email, password)) return

        setLoading(true)

        auth.signInWithEmailAndPassword(email, password)
            .addOnSuccessListener {
                setLoading(false)
                startActivity(Intent(this, MainActivity::class.java))
                finish()
            }
            .addOnFailureListener { exception ->
                setLoading(false)
                handleFirebaseError(exception)
            }
    }

    // ── Validation locale ─────────────────────────────────────────────────────

    private fun validateInputs(email: String, password: String): Boolean {
        var valid = true

        if (email.isEmpty()) {
            emailLayout.error = "L'adresse email est requise"
            valid = false
        } else if (!Patterns.EMAIL_ADDRESS.matcher(email).matches()) {
            emailLayout.error = "Adresse email invalide"
            valid = false
        }

        if (password.isEmpty()) {
            passwordLayout.error = "Le mot de passe est requis"
            valid = false
        }

        return valid
    }

    // ── Erreurs Firebase ──────────────────────────────────────────────────────

    private fun handleFirebaseError(exception: Exception) {
        when (exception) {
            is FirebaseAuthInvalidUserException ->
                emailLayout.error = "Aucun compte associé à cet email"

            is FirebaseAuthInvalidCredentialsException ->
                passwordLayout.error = "Mot de passe incorrect"

            else ->
                Toast.makeText(
                    this,
                    "Erreur de connexion. Vérifiez votre réseau.",
                    Toast.LENGTH_LONG
                ).show()
        }
    }

    // ── État de chargement ────────────────────────────────────────────────────

    private fun setLoading(loading: Boolean) {
        loginButton.isEnabled = !loading
        loginButton.text      = if (loading) "Connexion…" else "Se connecter"
    }
}