package com.familyshield.app

import android.content.Intent
import android.os.Bundle
import androidx.activity.compose.setContent
import androidx.fragment.app.FragmentActivity
import com.familyshield.app.ui.AppRoot
import com.familyshield.app.ui.theme.FamilyShieldTheme

/** FragmentActivity so the child path can show BiometricPrompt. */
class MainActivity : FragmentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val container = appContainer
        // A cold start from the share sheet. The same Intent is ignored after rotation.
        container.shares.ingest(this, intent)
        container.alerts.ingest(intent)
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
        // A notification tap carries kind and case_id, and nothing else.
        appContainer.shares.ingest(this, intent)
        appContainer.alerts.ingest(intent)
    }
}
