package com.familyshield.app.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.Immutable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color
import com.familyshield.app.domain.CaseColor

private val LightColors = lightColorScheme(
    primary = Color(0xFF1F5FAD),
    onPrimary = Color.White,
    primaryContainer = Color(0xFFD6E3FF),
    onPrimaryContainer = Color(0xFF001B3E),
    secondary = Color(0xFF555F71),
    background = Color(0xFFFAF9FD),
    surface = Color(0xFFFAF9FD),
    error = Color(0xFFBA1A1A),
)

private val DarkColors = darkColorScheme(
    primary = Color(0xFFAAC7FF),
    onPrimary = Color(0xFF002F65),
    primaryContainer = Color(0xFF00468E),
    onPrimaryContainer = Color(0xFFD6E3FF),
    secondary = Color(0xFFBDC7DC),
    background = Color(0xFF111318),
    surface = Color(0xFF111318),
    error = Color(0xFFFFB4AB),
)

/** Container and content colours for one result colour. Text on them meets WCAG AA in both themes. */
@Immutable
data class ResultTone(val container: Color, val content: Color)

@Immutable
data class ResultTones(val green: ResultTone, val red: ResultTone, val yellow: ResultTone, val open: ResultTone) {
    fun of(color: CaseColor): ResultTone = when (color) {
        CaseColor.GREEN -> green
        CaseColor.RED -> red
        CaseColor.YELLOW -> yellow
        CaseColor.OPEN -> open
    }
}

private val LightTones = ResultTones(
    green = ResultTone(Color(0xFFD3F5DA), Color(0xFF0B3D1A)),
    red = ResultTone(Color(0xFFFFDAD6), Color(0xFF5C0A0A)),
    yellow = ResultTone(Color(0xFFFFEDB3), Color(0xFF3D2E00)),
    open = ResultTone(Color(0xFFE3E7F2), Color(0xFF1A1C22)),
)

private val DarkTones = ResultTones(
    green = ResultTone(Color(0xFF14522A), Color(0xFFD3F5DA)),
    red = ResultTone(Color(0xFF7A1717), Color(0xFFFFDAD6)),
    yellow = ResultTone(Color(0xFF5C4600), Color(0xFFFFEDB3)),
    open = ResultTone(Color(0xFF2E3138), Color(0xFFE3E7F2)),
)

val LocalResultTones = staticCompositionLocalOf { LightTones }

/** The app theme. Dark follows the system setting. */
@Composable
fun FamilyShieldTheme(dark: Boolean = isSystemInDarkTheme(), content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = if (dark) DarkColors else LightColors) {
        androidx.compose.runtime.CompositionLocalProvider(
            LocalResultTones provides if (dark) DarkTones else LightTones,
            content = content,
        )
    }
}
