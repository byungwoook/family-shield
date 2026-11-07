package com.familyshield.app.ui.child

import android.Manifest
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import com.familyshield.app.MainActivity
import com.familyshield.app.R
import com.familyshield.app.domain.AlertPayload

/**
 * The notification for a money-request push. The text is the fixed sentence
 * from the API contract. There is no Yes action, no No action, and no code.
 * Any other field on the payload, including a code, is ignored.
 */
object ChildAlerts {
    const val CHANNEL_ID = "family_shield_requests"

    fun tapIntent(context: Context, caseId: String): Intent =
        Intent(context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP
            putExtra(AlertPayload.EXTRA_KIND, AlertPayload.KIND_MONEY_REQUEST)
            putExtra(AlertPayload.EXTRA_CASE_ID, caseId)
        }

    fun build(context: Context, caseId: String): Notification {
        ensureChannel(context)
        val body = context.getString(R.string.child_notification_body)
        val pending = PendingIntent.getActivity(
            context,
            caseId.hashCode(),
            tapIntent(context, caseId),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        return Notification.Builder(context, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_stat_shield)
            .setContentTitle(context.getString(R.string.app_name))
            .setContentText(body)
            .setStyle(Notification.BigTextStyle().bigText(body))
            .setContentIntent(pending)
            .setAutoCancel(true)
            .setCategory(Notification.CATEGORY_STATUS)
            .build()
    }

    /** Null when this payload is not a money request. The returned notification is what would be posted. */
    fun show(context: Context, data: Map<String, String>): Notification? {
        val alert = AlertPayload.moneyRequest(data) ?: return null
        val notification = build(context, alert.caseId)
        if (!canPost(context)) return notification
        val manager = context.getSystemService(NotificationManager::class.java) ?: return notification
        manager.notify(alert.caseId.hashCode(), notification)
        return notification
    }

    private fun canPost(context: Context): Boolean {
        if (Build.VERSION.SDK_INT < 33) return true
        return context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED
    }

    private fun ensureChannel(context: Context) {
        if (Build.VERSION.SDK_INT < 26) return
        val manager = context.getSystemService(NotificationManager::class.java) ?: return
        val channel = NotificationChannel(
            CHANNEL_ID,
            context.getString(R.string.child_notification_channel),
            NotificationManager.IMPORTANCE_HIGH,
        )
        channel.setShowBadge(true)
        manager.createNotificationChannel(channel)
    }
}
