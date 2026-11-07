package com.familyshield.app

import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/** The share sheet only offers Family Shield for the types milestone 13 accepts. */
class ShareManifestTest {
    @Test
    fun activityReceivesSendForAudioAndPlainText() {
        val manifest = File("src/main/AndroidManifest.xml").readText()
        assertTrue(manifest.contains("android.intent.action.SEND"))
        assertTrue(manifest.contains("android:mimeType=\"audio/*\""))
        assertTrue(manifest.contains("android:mimeType=\"text/plain\""))
        assertTrue(manifest.contains("android:mimeType=\"application/ogg\""))
        assertTrue(manifest.contains("android:launchMode=\"singleTop\""))
        // A catch-all binary type would put Family Shield on every file share.
        assertTrue(!manifest.contains("application/octet-stream"))
        assertTrue(!manifest.contains("video/*"))
    }
}