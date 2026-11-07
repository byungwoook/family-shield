package com.familyshield.app

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import com.familyshield.app.ui.AppRoot
import com.familyshield.app.ui.theme.FamilyShieldTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val container = appContainer
        // A cold start from the share sheet. The same Intent is ignored after rotation.
        container.shares.ingest(this, intent)
        setContent {
            FamilyShieldTheme {
                AppRoot(container)
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        // singleTop: a share while the app is open updates the draft in this activity.
        appContainer.shares.ingest(this, intent)
    }
}
