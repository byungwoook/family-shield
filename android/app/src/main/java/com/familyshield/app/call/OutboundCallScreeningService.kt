package com.familyshield.app.call

import android.content.Intent
import android.telecom.Call
import android.telecom.CallScreeningService
import com.familyshield.app.BuildConfig
import com.familyshield.app.domain.OutboundLabel

/**
 * Lets every call ring, and shows "Family Shield" only for the configured
 * outbound caller id. [respondToCall] runs before any UI, with no network
 * and no audio, so it finishes inside the platform's 5 second limit.
 * The service does not read call audio.
 */
class OutboundCallScreeningService : CallScreeningService() {
    override fun onScreenCall(details: Call.Details) {
        val plan = OutboundLabel.plan(details.handle?.schemeSpecificPart, BuildConfig.OUTBOUND_CALLER_ID)
        respondToCall(details, response(plan))
        if (plan.announceFamilyShield) {
            try {
                startActivity(CallerLabelActivity.intent(this))
            } catch (_: RuntimeException) {
                // The call is already allowed. Failing to show the label changes nothing.
            }
        }
    }

    private fun response(plan: OutboundLabel.Plan): CallResponse {
        return CallResponse.Builder()
            .setDisallowCall(plan.disallowCall)
            .setRejectCall(plan.rejectCall)
            .setSilenceCall(plan.silenceCall)
            .setSkipCallLog(plan.skipCallLog)
            .setSkipNotification(plan.skipNotification)
            .build()
    }
}

/** The system role request. Only one app can hold [android.app.role.RoleManager.ROLE_CALL_SCREENING]. */
object CallScreeningRole {
    fun supported(): Boolean = android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.Q

    fun isHeld(context: android.content.Context): Boolean {
        if (!supported()) return false
        return try {
            val roles = context.getSystemService(android.app.role.RoleManager::class.java) ?: return false
            roles.isRoleAvailable(android.app.role.RoleManager.ROLE_CALL_SCREENING) &&
                roles.isRoleHeld(android.app.role.RoleManager.ROLE_CALL_SCREENING)
        } catch (_: RuntimeException) {
            false
        }
    }

    fun open(context: android.content.Context): Boolean {
        if (!supported()) return false
        return try {
            val roles = context.getSystemService(android.app.role.RoleManager::class.java) ?: return false
            if (!roles.isRoleAvailable(android.app.role.RoleManager.ROLE_CALL_SCREENING)) return false
            val intent = roles.createRequestRoleIntent(android.app.role.RoleManager.ROLE_CALL_SCREENING)
            if (context !is android.app.Activity) intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            context.startActivity(intent)
            true
        } catch (_: android.content.ActivityNotFoundException) {
            false
        } catch (_: RuntimeException) {
            false
        }
    }
}
