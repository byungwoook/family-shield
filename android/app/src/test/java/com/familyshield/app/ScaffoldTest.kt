package com.familyshield.app

import org.junit.Assert.assertTrue
import org.junit.Test

class ScaffoldTest {
    @Test
    fun debugBuildHasADevLogin() {
        assertTrue(BuildConfig.DEV_LOGIN)
    }
}
