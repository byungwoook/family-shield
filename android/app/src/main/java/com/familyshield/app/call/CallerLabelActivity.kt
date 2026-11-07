package com.familyshield.app.call

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.view.Gravity
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.familyshield.app.R
import com.familyshield.app.ui.theme.FamilyShieldTheme

/**
 * The caller-id UI the platform documents: an activity launched from
 * [OutboundCallScreeningService.onScreenCall]. It says "Family Shield".
 * It does not take a number and it does not grade the caller.
 */
class CallerLabelActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.setGravity(Gravity.TOP)
        window.setLayout(WindowManager.LayoutParams.MATCH_PARENT, WindowManager.LayoutParams.WRAP_CONTENT)
        // showWhenLocked and turnScreenOn are on the activity in the manifest.
        // These two flags keep the banner from taking the incoming-call screen's focus.
        window.addFlags(
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL,
        )
        setContent {
            FamilyShieldTheme {
                CallerLabel(onDismiss = { finish() })
            }
        }
    }

    companion object {
        fun intent(context: Context): Intent =
            Intent(context, CallerLabelActivity::class.java).addFlags(
                Intent.FLAG_ACTIVITY_NEW_TASK or
                    Intent.FLAG_ACTIVITY_NO_USER_ACTION or
                    Intent.FLAG_ACTIVITY_SINGLE_TOP,
            )
    }
}

@Composable
fun CallerLabel(onDismiss: () -> Unit) {
    Surface(modifier = Modifier.fillMaxWidth().testTag("caller_label"), shadowElevation = 6.dp) {
        Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(stringResource(R.string.app_name), style = MaterialTheme.typography.titleLarge)
            Text(stringResource(R.string.caller_label_body), style = MaterialTheme.typography.bodyLarge)
            TextButton(onClick = onDismiss, modifier = Modifier.testTag("caller_label_dismiss")) {
                Text(stringResource(R.string.action_done))
            }
        }
    }
}
