package com.familyshield.app.domain

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

class OutboundLabelTest {
    private val ours = OutboundLabel.PLACEHOLDER_E164
    private val child = "+821012345678"

    @Test
    fun theDirectoryContainsExactlyTheConfiguredNumber() {
        assertEquals(15555550100L, OutboundLabel.identificationNumber(ours))
        assertEquals(OutboundLabel.LABEL, "Family Shield")
        assertFalse(OutboundLabel.LABEL.equals("genuine", ignoreCase = true))
        val labeled = listOfNotNull(OutboundLabel.identificationNumber(ours))
        assertEquals(listOf(15555550100L), labeled)
        assertFalse(labeled.contains(821012345678L))
    }

    @Test
    fun aSecondNumberIsRefused() {
        assertNull(OutboundLabel.identificationNumber("$ours,$child"))
        assertNull(OutboundLabel.identificationNumber("$ours $child"))
        assertNull(OutboundLabel.identificationNumber(""))
        assertNull(OutboundLabel.identificationNumber("not-a-number"))
        assertNull(OutboundLabel.identificationNumber("+0123"))
    }

    @Test
    fun ourCallIsAnnouncedAndEveryCallIsAllowedToRing() {
        val oursPlan = OutboundLabel.plan(ours, ours)
        assertTrue(oursPlan.announceFamilyShield)
        assertAllows(oursPlan)

        val tel = OutboundLabel.plan("tel:+15555550100", ours)
        assertTrue(tel.announceFamilyShield)
        assertFalse(tel.silenceCall)

        val childPlan = OutboundLabel.plan(child, ours)
        assertFalse(childPlan.announceFamilyShield)
        assertAllows(childPlan)

        val neighbor = OutboundLabel.plan("+15555550101", ours)
        assertFalse(neighbor.announceFamilyShield)
        assertFalse(neighbor.silenceCall)

        val missing = OutboundLabel.plan(null, ours)
        assertFalse(missing.announceFamilyShield)
        assertAllows(missing)
        assertFalse(OutboundLabel.plan(ours, "").announceFamilyShield)
    }

    @Test
    fun theServiceRespondsBeforeAnyUiAndDoesNotReadAudio() {
        val service = File("src/main/java/com/familyshield/app/call/OutboundCallScreeningService.kt").readText()
        val body = service.substringAfter("override fun onScreenCall")
        val respond = body.indexOf("respondToCall")
        val show = body.indexOf("startActivity")
        assertTrue(respond >= 0 && show > respond)
        assertTrue(service.contains("setSilenceCall(plan.silenceCall)"))
        assertTrue(service.contains("setDisallowCall(plan.disallowCall)"))
        assertTrue(service.contains("setRejectCall(plan.rejectCall)"))
        assertFalse(service.contains("setShouldScreenCallViaAudioProcessing"))
        assertFalse(service.contains("AudioRecord"))
        assertFalse(service.contains("MediaRecorder"))
        assertFalse(service.lowercase().contains("verified"))

        val label = File("src/main/java/com/familyshield/app/domain/OutboundLabel.kt").readText()
        assertFalse(label.lowercase().contains("verified"))
        val activity = File("src/main/java/com/familyshield/app/call/CallerLabelActivity.kt").readText()
        assertFalse(activity.contains("putExtra"))
        assertFalse(activity.lowercase().contains("verified"))
    }

    @Test
    fun theManifestScreensCallsWithoutContactsOrAudio() {
        val manifest = File("src/main/AndroidManifest.xml").readText()
        assertTrue(manifest.contains("android.permission.BIND_SCREENING_SERVICE"))
        assertTrue(manifest.contains("android.telecom.CallScreeningService"))
        assertTrue(manifest.contains("OutboundCallScreeningService"))
        assertTrue(manifest.contains("CallerLabelActivity"))
        val activity = manifest.substringAfter("CallerLabelActivity").substringBefore("</activity>")
        assertTrue(activity.contains("android:exported=\"false\""))
        val screening = manifest.substringAfter("OutboundCallScreeningService").substringBefore("</service>")
        assertTrue(screening.contains("android:exported=\"true\""))
        assertFalse(manifest.contains("READ_CONTACTS"))
        assertFalse(manifest.contains("RECORD_AUDIO"))
        assertFalse(manifest.contains("READ_CALL_LOG"))
        val gradle = File("build.gradle.kts").readText()
        assertTrue(gradle.contains("fsOutboundCallerId"))
        assertTrue(gradle.contains("+15555550100"))
    }

    private fun assertAllows(plan: OutboundLabel.Plan) {
        assertFalse(plan.disallowCall)
        assertFalse(plan.rejectCall)
        assertFalse(plan.silenceCall)
        assertFalse(plan.skipCallLog)
        assertFalse(plan.skipNotification)
    }
}
