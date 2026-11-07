package com.familyshield.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import com.familyshield.app.ui.AppRoot
import com.familyshield.app.ui.theme.FamilyShieldTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val container = appContainer
        setContent {
            FamilyShieldTheme {
                AppRoot(container)
            }
        }
    }
}
