package com.familyshield.app.ui

import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.math.pow

/** Locks the scam-share button pairs at WCAG AA for normal text (4.5:1). */
class RedButtonContrastTest {
    @Test
    fun scamShareButtonMeetsAa() {
        // Light sheet uses the light red token with cream text.
        val light = contrast("#F3F0E9", "#B83232")
        // Dark sheet uses the dark red token with ink text. Cream on that red is only 1.81:1.
        val dark = contrast("#0D1015", "#FF9991")
        assertTrue("light cream on #B83232 was $light", light >= 4.5)
        assertTrue("dark ink on #FF9991 was $dark", dark >= 4.5)
    }

    private fun contrast(foreground: String, background: String): Double {
        val lighter = maxOf(luminance(foreground), luminance(background))
        val darker = minOf(luminance(foreground), luminance(background))
        return (lighter + 0.05) / (darker + 0.05)
    }

    private fun luminance(hex: String): Double {
        val raw = hex.removePrefix("#")
        val channels = listOf(0, 2, 4).map { index ->
            val value = raw.substring(index, index + 2).toInt(16) / 255.0
            if (value <= 0.04045) value / 12.92 else ((value + 0.055) / 1.055).pow(2.4)
        }
        return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]
    }
}
