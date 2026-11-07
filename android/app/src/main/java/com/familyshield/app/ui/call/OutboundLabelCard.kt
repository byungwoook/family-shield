package com.familyshield.app.ui.call

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import com.familyshield.app.R
import com.familyshield.app.call.CallScreeningRole

/** Optional. The check code works without call screening. */
@Composable
fun OutboundLabelCard(modifier: Modifier = Modifier) {
    val context = LocalContext.current
    var held by remember { mutableStateOf(CallScreeningRole.isHeld(context)) }
    val lifecycleOwner = LocalLifecycleOwner.current
    DisposableEffect(lifecycleOwner, context) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) held = CallScreeningRole.isHeld(context)
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }
    Column(modifier.testTag("outbound_label"), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(stringResource(R.string.outbound_label_title), style = MaterialTheme.typography.titleMedium)
        Text(
            stringResource(if (held) R.string.outbound_label_on else R.string.outbound_label_off),
            style = MaterialTheme.typography.bodyMedium,
        )
        Text(stringResource(R.string.outbound_label_body), style = MaterialTheme.typography.bodyMedium)
        if (CallScreeningRole.supported()) {
            TextButton(
                onClick = { CallScreeningRole.open(context) },
                modifier = Modifier.testTag("open_call_screening"),
            ) {
                Text(stringResource(R.string.outbound_label_open_settings))
            }
        } else {
            Text(stringResource(R.string.outbound_label_unavailable))
        }
    }
}
