package com.familyshield.app.ui

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import com.familyshield.app.ui.child.ChildResetContent
import com.familyshield.app.ui.child.QuestionContent
import com.familyshield.app.ui.theme.FamilyShieldTheme
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [33])
class ChildScreenTest {
    @get:Rule
    val compose = createComposeRule()

    @Test
    fun notNowDoesNotPostYesOrNo() {
        val calls = mutableListOf<String>()
        compose.setContent {
            FamilyShieldTheme {
                QuestionContent(
                    calling = false,
                    revealedCode = null,
                    callFallback = false,
                    busy = false,
                    error = null,
                    onYes = { calls += "yes" },
                    onNo = { calls += "no" },
                    onNotNow = { calls += "not_now" },
                    onReveal = { calls += "reveal" },
                    onHideCode = { calls += "hide" },
                )
            }
        }
        compose.onNodeWithText("Did you send your family a message asking for money?").assertIsDisplayed()
        compose.onNodeWithTag("not_now").performClick()
        assertEquals(listOf("not_now"), calls)
        assertFalse(calls.contains("yes"))
        assertFalse(calls.contains("no"))
    }

    @Test
    fun theOneTimeCodeIsAbsentUntilItIsRevealed() {
        compose.setContent {
            FamilyShieldTheme {
                QuestionContent(
                    calling = true,
                    revealedCode = null,
                    callFallback = false,
                    busy = false,
                    error = null,
                    onYes = {},
                    onNo = {},
                    onNotNow = {},
                    onReveal = {},
                    onHideCode = {},
                )
            }
        }
        compose.onNodeWithTag("reveal_code").assertIsDisplayed()
        compose.onNodeWithTag("one_time_code").assertDoesNotExist()
        compose.onNodeWithText("654321").assertDoesNotExist()
    }

    @Test
    fun resetHidesTheFieldsUntilBiometrics() {
        val calls = mutableListOf<String>()
        compose.setContent {
            FamilyShieldTheme {
                ChildResetContent(
                    unlocked = false,
                    code = "",
                    again = "",
                    busy = false,
                    error = null,
                    onUnlock = { calls += "unlock" },
                    onCode = {},
                    onAgain = {},
                    onSubmit = { calls += "submit" },
                    onClose = {},
                )
            }
        }
        compose.onNodeWithTag("check_code").assertDoesNotExist()
        compose.onNodeWithTag("reset_unlock").performClick()
        assertEquals(listOf("unlock"), calls)
    }
}
