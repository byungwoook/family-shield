package com.familyshield.app.domain

import java.time.Instant

/** Countdown and name helpers for the v3 screens. The bar is a 90 second clock, not a score. */
object V3Format {
    const val PUSH_WINDOW_SECONDS = 90
    const val SEGMENT_SECONDS = 3

    fun remainingSeconds(deadline: Instant?, now: Instant): Long? {
        deadline ?: return null
        return (deadline.epochSecond - now.epochSecond).coerceAtLeast(0)
    }

    fun clock(seconds: Long): String {
        val safe = seconds.coerceAtLeast(0)
        return "%02d:%02d".format(safe / 60, safe % 60)
    }

    fun segmentCount(
        windowSeconds: Int = PUSH_WINDOW_SECONDS,
        segmentSeconds: Int = SEGMENT_SECONDS,
    ): Int = windowSeconds / segmentSeconds

    /**
     * Index of the lime segment. Past segments are before it, future ones after.
     * -1 when the push window is over.
     */
    fun currentSegment(
        remainingSeconds: Long,
        windowSeconds: Int = PUSH_WINDOW_SECONDS,
        segmentSeconds: Int = SEGMENT_SECONDS,
    ): Int {
        if (remainingSeconds <= 0) return -1
        val elapsed = (windowSeconds - remainingSeconds).coerceIn(0, windowSeconds.toLong())
        val last = segmentCount(windowSeconds, segmentSeconds) - 1
        return (elapsed / segmentSeconds).toInt().coerceIn(0, last)
    }

    /** Korean subject particle. Names outside Hangul use 가, matching the mockup's 지우가. */
    fun subjectParticle(name: String): String {
        val last = name.lastOrNull() ?: return "가"
        if (last.code !in 0xAC00..0xD7A3) return "가"
        val hasBatchim = (last.code - 0xAC00) % 28 != 0
        return if (hasBatchim) "이" else "가"
    }

    fun subject(name: String, korean: Boolean): String =
        if (korean && name.isNotBlank()) name + subjectParticle(name) else name

    fun initial(name: String): String {
        val trimmed = name.trim()
        if (trimmed.isEmpty()) return ""
        return trimmed.first().toString()
    }
}
