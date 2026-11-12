package com.familyshield.app.domain

import org.junit.Assert.assertEquals
import org.junit.Test
import java.time.Instant

class V3FormatTest {
    @Test
    fun sixtyEightSecondsIsOneMinuteEightAndTheLimeSegment() {
        val now = Instant.parse("2026-11-11T12:24:00Z")
        val deadline = now.plusSeconds(68)
        val remaining = V3Format.remainingSeconds(deadline, now)
        assertEquals(68L, remaining)
        assertEquals("01:08", V3Format.clock(remaining!!))
        assertEquals(7, V3Format.currentSegment(remaining))
        assertEquals(-1, V3Format.currentSegment(0))
    }

    @Test
    fun subjectParticleFollowsHangulBatchim() {
        assertEquals("가", V3Format.subjectParticle("지우"))
        assertEquals("이", V3Format.subjectParticle("민준"))
        assertEquals("지우가", V3Format.subject("지우", korean = true))
        assertEquals("Mina", V3Format.subject("Mina", korean = false))
    }
}
