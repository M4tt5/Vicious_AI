package com.example.viciousai

import android.content.Intent
import android.os.Bundle
import android.util.Patterns
import android.view.View
import android.widget.CheckBox
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.google.android.material.button.MaterialButton
import com.google.android.material.textfield.TextInputEditText
import com.google.android.material.textfield.TextInputLayout
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.auth.FirebaseAuthUserCollisionException
import com.google.firebase.auth.FirebaseAuthWeakPasswordException

class RegisterActivity : AppCompatActivity() {

    private lateinit var auth: FirebaseAuth

    // ── Vues ──────────────────────────────────────────────────────────────────
    private lateinit var emailLayout:    TextInputLayout
    private lateinit var passwordLayout: TextInputLayout
    private lateinit var confirmLayout:  TextInputLayout
    private lateinit var emailEdit:      TextInputEditText
    private lateinit var passwordEdit:   TextInputEditText
    private lateinit var confirmEdit:    TextInputEditText
    private lateinit var consentCheck:   CheckBox
    private lateinit var registerButton: MaterialButton
    private lateinit var backLogin:      TextView

    // ── Lifecycle ─────────────────────────────────────────────────────────────

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_inscription)

        auth = FirebaseAuth.getInstance()

        emailLayout    = findViewById(R.id.emailLayout)
        passwordLayout = findViewById(R.id.passwordLayout)
        confirmLayout  = findViewById(R.id.confirmLayout)
        emailEdit      = emailLayout.editText    as TextInputEditText
        passwordEdit   = passwordLayout.editText as TextInputEditText
        confirmEdit    = confirmLayout.editText  as TextInputEditText
        consentCheck   = findViewById(R.id.consentCheck)
        registerButton = findViewById(R.id.registerButton)
        backLogin      = findViewById(R.id.backLogin)

        registerButton.setOnClickListener { handleRegister() }

        backLogin.setOnClickListener {
            startActivity(Intent(this, LoginActivity::class.java))
            finish()
        }
    }

    // ── Inscription ───────────────────────────────────────────────────────────

    private fun handleRegister() {
        // Réinitialise les erreurs précédentes
        emailLayout.error    = null
        passwordLayout.error = null
        confirmLayout.error  = null

        val email    = emailEdit.text.toString().trim()
        val password = passwordEdit.text.toString()
        val confirm  = confirmEdit.text.toString()

        // ── Validation des champs ─────────────────────────────────────────────
        if (!validateInputs(email, password, confirm)) return

        // ── Validation du consentement ────────────────────────────────────────
        if (!consentCheck.isChecked) {
            Toast.makeText(
                this,
                "Vous devez accepter les conditions d'utilisation pour créer un compte.",
                Toast.LENGTH_LONG
            ).show()
            return
        }

        // ── Création du compte Firebase ───────────────────────────────────────
        setLoading(true)

        auth.createUserWithEmailAndPassword(email, password)
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

    private fun validateInputs(email: String, password: String, confirm: String): Boolean {
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
        } else if (password.length < 6) {
            passwordLayout.error = "Le mot de passe doit contenir au moins 6 caractères"
            valid = false
        }

        if (confirm.isEmpty()) {
            confirmLayout.error = "Veuillez confirmer votre mot de passe"
            valid = false
        } else if (password != confirm) {
            confirmLayout.error = "Les mots de passe ne correspondent pas"
            valid = false
        }

        return valid
    }

    // ── Erreurs Firebase ──────────────────────────────────────────────────────

    private fun handleFirebaseError(exception: Exception) {
        when (exception) {
            is FirebaseAuthUserCollisionException ->
                emailLayout.error = "Un compte existe déjà avec cet email"

            is FirebaseAuthWeakPasswordException ->
                passwordLayout.error = "Mot de passe trop faible"

            else ->
                Toast.makeText(this, "Erreur : ${exception.message}", Toast.LENGTH_LONG).show()
        }
    }

    // ── État du bouton pendant la requête ─────────────────────────────────────

    private fun setLoading(loading: Boolean) {
        registerButton.isEnabled = !loading
        registerButton.text      = if (loading) "Création en cours…" else "S'inscrire"
    }
}