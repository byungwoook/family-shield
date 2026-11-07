package com.familyshield.app.ui

import android.app.Notification
import android.content.Intent
import com.familyshield.app.SAMPLE_CASE_ID
import com.familyshield.app.data.AlertInbox
import com.familyshield.app.domain.AlertPayload
import com.familyshield.app.ui.child.ChildAlerts
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [33])
class ChildNotificationTest {
    @Test
    fun theNotificationHasNoActionsAndNoCode() {
        val context = RuntimeEnvironment.getApplication()
        val code = "654321"
        val notification = ChildAlerts.show(
            context,
            mapOf(
                "kind" to "money_request",
                "case_id" to SAMPLE_CASE_ID,
                "code" to code,
                "digits" to "2580",
            ),
        )
        checkNotNull(notification)
        assertTrue(notification.actions == null || notification.actions.isEmpty())
        val text = notification.extras.getCharSequence(Notification.EXTRA_TEXT).toString()
        val big = notification.extras.getCharSequence(Notification.EXTRA_BIG_TEXT)?.toString().orEmpty()
        val title = notification.extras.getCharSequence(Notification.EXTRA_TITLE).toString()
        assertEquals("Family Shield needs you to confirm a request.", text)
        assertEquals(text, big)
        assertEquals("Family Shield", title)
        assertFalse(text.contains(code))
        assertFalse(big.contains(code))
        assertFalse(title.contains(code))
        assertFalse(Regex("\\d{4,}").containsMatchIn("$title $text $big"))
        val tap = ChildAlerts.tapIntent(context, SAMPLE_CASE_ID)
        assertEquals("money_request", tap.getStringExtra(AlertPayload.EXTRA_KIND))
        assertEquals(SAMPLE_CASE_ID, tap.getStringExtra(AlertPayload.EXTRA_CASE_ID))
        assertNull(tap.getStringExtra("code"))
        assertEquals(setOf(AlertPayload.EXTRA_KIND, AlertPayload.EXTRA_CASE_ID), tap.extras?.keySet())
    }

    @Test
    fun anAlertIntentKeepsTheCaseIdAndDropsACodeExtra() {
        val inbox = AlertInbox()
        inbox.ingest(Intent().apply { putExtra("code", "654321") })
        assertNull(inbox.currentCaseId())
        inbox.ingest(
            Intent().apply {
                putExtra("kind", "money_request")
                putExtra("case_id", SAMPLE_CASE_ID)
                putExtra("code", "654321")
            },
        )
        assertEquals(SAMPLE_CASE_ID, inbox.currentCaseId())
        assertEquals(1, inbox.generation.value)
    }

    @Test
    fun aPayloadThatIsNotAMoneyRequestIsNotPosted() {
        val context = RuntimeEnvironment.getApplication()
        assertNull(
            ChildAlerts.show(
                context,
                mapOf("kind" to "number_change_confirmed", "family_id" to SAMPLE_CASE_ID, "code" to "654321"),
            ),
        )
    }
}
