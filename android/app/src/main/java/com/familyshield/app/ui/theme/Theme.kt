package com.familyshield.app.ui.theme

import android.app.Activity
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.Immutable
import androidx.compose.runtime.SideEffect
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.text.ExperimentalTextApi
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.style.LineBreak
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontVariation
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp
import androidx.core.view.WindowCompat
import com.familyshield.app.R
import com.familyshield.app.domain.CaseColor

@OptIn(ExperimentalTextApi::class)
private fun pretendard(weight: Int) = Font(
    R.font.pretendard_variable,
    weight = FontWeight(weight),
    variationSettings = FontVariation.Settings(FontVariation.weight(weight)),
)

val Pretendard = FontFamily(
    pretendard(400),
    pretendard(500),
    pretendard(600),
    pretendard(650),
    pretendard(700),
)

@Immutable
data class FsPalette(
    val bg: Color,
    val surface: Color,
    val text: Color,
    val muted: Color,
    val line: Color,
    val avatar: Color,
    val hero: Color,
    val heroMuted: Color,
    val heroFuture: Color,
    val lime: Color,
    val ink: Color,
    val green: Color,
    val red: Color,
    val yellow: Color,
    val sheet: Color,
    val sheetText: Color,
    val sheetMuted: Color,
    val answerNo: Color,
    val isDark: Boolean,
)

private val Lime = Color(0xFFD6FE39)
private val Ink = Color(0xFF0D1015)
private val AnswerNo = Color(0xFFFF9991)

val LightPalette = FsPalette(
    bg = Color(0xFFF3F0E9),
    surface = Color(0xFFFFFDF8),
    text = Ink,
    muted = Color(0xFF676B65),
    line = Color(0xFFD5D4CB),
    avatar = Color(0xFFE4E1D8),
    hero = Ink,
    heroMuted = Color(0xFFB1B5B0),
    heroFuture = Color(0xFF98A196),
    lime = Lime,
    ink = Ink,
    green = Color(0xFF216B40),
    red = Color(0xFFB83232),
    yellow = Color(0xFF806100),
    sheet = Color(0xFFF3F0E9),
    sheetText = Ink,
    sheetMuted = Color(0xFF5C625C),
    answerNo = AnswerNo,
    isDark = false,
)

val DarkPalette = FsPalette(
    bg = Color(0xFF101419),
    surface = Color(0xFF1D2329),
    text = Color(0xFFF3F0E9),
    muted = Color(0xFFAFB5AE),
    line = Color(0xFF3B4147),
    avatar = Color(0xFF343C43),
    hero = Color(0xFF252C33),
    heroMuted = Color(0xFFB1B5B0),
    heroFuture = Color(0xFF98A196),
    lime = Lime,
    ink = Ink,
    green = Color(0xFFADE3BA),
    red = AnswerNo,
    yellow = Color(0xFFE7D17C),
    sheet = Color(0xFF20272D),
    sheetText = Color(0xFFF3F0E9),
    sheetMuted = Color(0xFFBDC3BA),
    answerNo = AnswerNo,
    isDark = true,
)

val LocalFsPalette = staticCompositionLocalOf { LightPalette }

private fun fs(size: Int, line: Int, weight: Int, tracking: Float = -0.35f) = TextStyle(
    fontFamily = Pretendard,
    fontWeight = FontWeight(weight),
    fontSize = size.sp,
    lineHeight = line.sp,
    letterSpacing = tracking.sp,
    // Phrase keeps Korean words whole, so a particle like 요. is not left alone.
    lineBreak = LineBreak.Paragraph.copy(wordBreak = LineBreak.WordBreak.Phrase),
)

private val FsTypography = Typography(
    displayLarge = fs(64, 76, 600, -1.3f),
    displayMedium = fs(44, 50, 600, -1.1f),
    displaySmall = fs(38, 46, 700, -1.2f),
    headlineLarge = fs(32, 40, 700, -1.1f),
    headlineMedium = fs(26, 36, 700, -0.9f),
    headlineSmall = fs(24, 31, 600, -0.75f),
    titleLarge = fs(20, 28, 650, -0.6f),
    titleMedium = fs(17, 24, 650, -0.35f),
    titleSmall = fs(15, 22, 500, -0.35f),
    bodyLarge = fs(17, 26, 400, -0.35f),
    bodyMedium = fs(15, 22, 400, -0.35f),
    bodySmall = fs(14, 21, 400, -0.2f),
    labelLarge = fs(17, 24, 650, -0.35f),
    labelMedium = fs(13, 20, 500, -0.2f),
    labelSmall = fs(12, 16, 500, 0.4f),
)

@Immutable
data class ResultTone(val container: Color, val content: Color)

@Immutable
data class ResultTones(
    val green: ResultTone,
    val red: ResultTone,
    val yellow: ResultTone,
    val open: ResultTone,
) {
    fun of(color: CaseColor): ResultTone = when (color) {
        CaseColor.GREEN -> green
        CaseColor.RED -> red
        CaseColor.YELLOW -> yellow
        CaseColor.OPEN -> open
    }
}

private fun tones(palette: FsPalette) = ResultTones(
    green = ResultTone(palette.surface, palette.green),
    red = ResultTone(palette.surface, palette.red),
    yellow = ResultTone(palette.surface, palette.yellow),
    open = ResultTone(palette.surface, palette.text),
)

val LocalResultTones = staticCompositionLocalOf { tones(LightPalette) }

@Composable
fun FamilyShieldTheme(dark: Boolean = isSystemInDarkTheme(), content: @Composable () -> Unit) {
    val palette = if (dark) DarkPalette else LightPalette
    val scheme = if (dark) {
        darkColorScheme(
            primary = palette.lime,
            onPrimary = palette.ink,
            background = palette.bg,
            onBackground = palette.text,
            surface = palette.surface,
            onSurface = palette.text,
            surfaceVariant = palette.avatar,
            onSurfaceVariant = palette.muted,
            outline = palette.line,
            error = palette.red,
            onError = palette.ink,
        )
    } else {
        lightColorScheme(
            primary = palette.lime,
            onPrimary = palette.ink,
            background = palette.bg,
            onBackground = palette.text,
            surface = palette.surface,
            onSurface = palette.text,
            surfaceVariant = palette.avatar,
            onSurfaceVariant = palette.muted,
            outline = palette.line,
            error = palette.red,
            onError = palette.surface,
        )
    }
    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as? Activity)?.window ?: return@SideEffect
            window.statusBarColor = palette.bg.toArgb()
            window.navigationBarColor = palette.bg.toArgb()
            WindowCompat.getInsetsController(window, view).isAppearanceLightStatusBars = !dark
            WindowCompat.getInsetsController(window, view).isAppearanceLightNavigationBars = !dark
        }
    }
    MaterialTheme(colorScheme = scheme, typography = FsTypography) {
        CompositionLocalProvider(
            LocalFsPalette provides palette,
            LocalResultTones provides tones(palette),
            content = content,
        )
    }
}
