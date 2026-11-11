package com.familyshield.app.ui.v3

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.familyshield.app.domain.V3Format
import com.familyshield.app.ui.theme.LocalFsPalette
import com.familyshield.app.ui.theme.Pretendard

enum class HomeTab { Home, History, Family }

@Composable
fun InitialAvatar(
    name: String,
    modifier: Modifier = Modifier,
    size: Dp = 56.dp,
    background: Color = LocalFsPalette.current.avatar,
    foreground: Color = LocalFsPalette.current.text,
) {
    val letter = V3Format.initial(name)
    Box(
        modifier.size(size).clip(CircleShape).background(background),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            letter,
            color = foreground,
            fontFamily = Pretendard,
            fontWeight = FontWeight(650),
            fontSize = (size.value * 0.34f).sp,
            textAlign = TextAlign.Center,
        )
    }
}

@Composable
fun LimeButton(
    label: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    leading: (@Composable () -> Unit)? = null,
    trailing: (@Composable () -> Unit)? = null,
) {
    val palette = LocalFsPalette.current
    val shape = RoundedCornerShape(16.dp)
    Row(
        modifier
            .fillMaxWidth()
            .height(56.dp)
            .clip(shape)
            .background(if (enabled) palette.lime else palette.line)
            .clickable(enabled = enabled, role = Role.Button, onClick = onClick)
            .padding(horizontal = 20.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.Center,
    ) {
        if (leading != null) {
            leading()
            Spacer(Modifier.width(8.dp))
        }
        Text(
            label,
            color = palette.ink,
            fontFamily = Pretendard,
            fontWeight = FontWeight(650),
            fontSize = 17.sp,
            lineHeight = 24.sp,
        )
        if (trailing != null) {
            Spacer(Modifier.weight(1f))
            trailing()
        }
    }
}

@Composable
fun InkButton(
    label: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    background: Color,
    foreground: Color,
) {
    Row(
        modifier
            .fillMaxWidth()
            .height(56.dp)
            .clip(RoundedCornerShape(16.dp))
            .background(background)
            .clickable(role = Role.Button, onClick = onClick),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.Center,
    ) {
        Text(
            label,
            color = foreground,
            fontFamily = Pretendard,
            fontWeight = FontWeight(650),
            fontSize = 17.sp,
        )
    }
}

@Composable
fun Waveform(
    color: Color,
    modifier: Modifier = Modifier,
    bars: Int = 42,
) {
    Canvas(modifier.height(36.dp).fillMaxWidth()) {
        val gap = 3.dp.toPx()
        val width = ((size.width - gap * (bars - 1)) / bars).coerceAtLeast(2.dp.toPx())
        val mid = size.height / 2f
        for (index in 0 until bars) {
            val wave = kotlin.math.abs(kotlin.math.sin(index * 0.55)) 
            val peak = 0.25f + 0.75f * ((index * 17 % 11) / 10f) * (0.45f + wave.toFloat())
            val h = size.height * peak.coerceIn(0.18f, 1f)
            val x = index * (width + gap)
            drawLine(
                color = color,
                start = Offset(x, mid - h / 2f),
                end = Offset(x, mid + h / 2f),
                strokeWidth = width,
                cap = StrokeCap.Round,
            )
        }
    }
}

@Composable
fun CountdownBar(remainingSeconds: Long, modifier: Modifier = Modifier) {
    val palette = LocalFsPalette.current
    val count = V3Format.segmentCount()
    val current = V3Format.currentSegment(remainingSeconds)
    Row(modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(3.dp)) {
        repeat(count) { index ->
            val color = when {
                current < 0 -> palette.line
                index < current -> palette.text
                index == current -> palette.lime
                else -> palette.line
            }
            Box(
                Modifier
                    .weight(1f)
                    .height(10.dp)
                    .clip(RoundedCornerShape(2.dp))
                    .background(color),
            )
        }
    }
}

@Composable
fun TabBar(selected: HomeTab, onSelect: (HomeTab) -> Unit, labels: TabLabels) {
    val palette = LocalFsPalette.current
    Row(
        Modifier
            .fillMaxWidth()
            .background(palette.bg)
            .border(width = 0.5.dp, color = palette.line)
            .height(64.dp)
            .padding(top = 6.dp),
        horizontalArrangement = Arrangement.SpaceEvenly,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        TabItem(HomeTab.Home, selected, labels.home, onSelect) { HomeIcon(it) }
        TabItem(HomeTab.History, selected, labels.history, onSelect) { HistoryIcon(it) }
        TabItem(HomeTab.Family, selected, labels.family, onSelect) { FamilyIcon(it) }
    }
}

data class TabLabels(val home: String, val history: String, val family: String)

@Composable
private fun TabItem(
    tab: HomeTab,
    selected: HomeTab,
    label: String,
    onSelect: (HomeTab) -> Unit,
    icon: @Composable (Color) -> Unit,
) {
    val palette = LocalFsPalette.current
    val color = if (tab == selected) palette.text else palette.muted
    val tag = when (tab) {
        HomeTab.Home -> "tab_home"
        HomeTab.History -> "tab_history"
        HomeTab.Family -> "tab_family"
    }
    Column(
        Modifier
            .testTag(tag)
            .width(96.dp)
            .height(52.dp)
            .clickable(role = Role.Tab, onClick = { onSelect(tab) })
            .semantics { contentDescription = label }
            .padding(top = 2.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Box(Modifier.size(44.dp, 28.dp), contentAlignment = Alignment.Center) { icon(color) }
        Text(label, color = color, fontFamily = Pretendard, fontWeight = FontWeight(500), fontSize = 12.sp, lineHeight = 16.sp)
    }
}

@Composable
fun StrokeIcon(modifier: Modifier = Modifier, color: Color, draw: androidx.compose.ui.graphics.drawscope.DrawScope.() -> Unit) {
    Canvas(modifier.size(22.dp)) { draw() }
}

@Composable
fun HomeIcon(color: Color) {
    Canvas(Modifier.size(22.dp)) {
        val stroke = Stroke(width = 1.5.dp.toPx(), cap = StrokeCap.Round)
        val w = size.width
        val h = size.height
        drawLine(color, Offset(w * 0.15f, h * 0.48f), Offset(w * 0.5f, h * 0.18f), stroke.width, cap = StrokeCap.Round)
        drawLine(color, Offset(w * 0.5f, h * 0.18f), Offset(w * 0.85f, h * 0.48f), stroke.width, cap = StrokeCap.Round)
        drawLine(color, Offset(w * 0.24f, h * 0.46f), Offset(w * 0.24f, h * 0.82f), stroke.width, cap = StrokeCap.Round)
        drawLine(color, Offset(w * 0.24f, h * 0.82f), Offset(w * 0.76f, h * 0.82f), stroke.width, cap = StrokeCap.Round)
        drawLine(color, Offset(w * 0.76f, h * 0.82f), Offset(w * 0.76f, h * 0.46f), stroke.width, cap = StrokeCap.Round)
    }
}

@Composable
fun HistoryIcon(color: Color) {
    Canvas(Modifier.size(22.dp)) {
        val stroke = 1.5.dp.toPx()
        drawCircle(color, radius = size.minDimension * 0.36f, style = Stroke(stroke))
        drawLine(color, Offset(size.width * 0.5f, size.height * 0.32f), Offset(size.width * 0.5f, size.height * 0.52f), stroke, cap = StrokeCap.Round)
        drawLine(color, Offset(size.width * 0.5f, size.height * 0.52f), Offset(size.width * 0.66f, size.height * 0.62f), stroke, cap = StrokeCap.Round)
    }
}

@Composable
fun FamilyIcon(color: Color) {
    Canvas(Modifier.size(22.dp)) {
        val stroke = Stroke(1.5.dp.toPx())
        drawCircle(color, radius = size.minDimension * 0.16f, center = Offset(size.width * 0.38f, size.height * 0.34f), style = stroke)
        drawCircle(color, radius = size.minDimension * 0.12f, center = Offset(size.width * 0.68f, size.height * 0.38f), style = stroke)
        drawArc(color, 200f, 140f, false, topLeft = Offset(size.width * 0.12f, size.height * 0.48f), size = androidx.compose.ui.geometry.Size(size.width * 0.5f, size.height * 0.42f), style = stroke)
        drawArc(color, 200f, 140f, false, topLeft = Offset(size.width * 0.48f, size.height * 0.52f), size = androidx.compose.ui.geometry.Size(size.width * 0.4f, size.height * 0.36f), style = stroke)
    }
}

@Composable
fun PhoneIcon(color: Color, modifier: Modifier = Modifier) {
    Canvas(modifier.size(20.dp)) {
        val stroke = Stroke(1.6.dp.toPx(), cap = StrokeCap.Round)
        drawRoundRect(
            color,
            topLeft = Offset(size.width * 0.30f, size.height * 0.06f),
            size = androidx.compose.ui.geometry.Size(size.width * 0.40f, size.height * 0.88f),
            cornerRadius = androidx.compose.ui.geometry.CornerRadius(2.dp.toPx()),
            style = stroke,
        )
        drawLine(color, Offset(size.width * 0.42f, size.height * 0.78f), Offset(size.width * 0.58f, size.height * 0.78f), stroke.width, cap = StrokeCap.Round)
    }
}

@Composable
fun FaceIcon(color: Color, modifier: Modifier = Modifier) {
    Canvas(modifier.size(20.dp)) {
        val stroke = Stroke(1.5.dp.toPx(), cap = StrokeCap.Round)
        drawCircle(color, radius = size.minDimension * 0.28f, style = stroke)
        drawLine(color, Offset(size.width * 0.12f, size.height * 0.22f), Offset(size.width * 0.12f, size.height * 0.42f), stroke.width, cap = StrokeCap.Round)
        drawLine(color, Offset(size.width * 0.88f, size.height * 0.22f), Offset(size.width * 0.88f, size.height * 0.42f), stroke.width, cap = StrokeCap.Round)
        drawLine(color, Offset(size.width * 0.12f, size.height * 0.78f), Offset(size.width * 0.12f, size.height * 0.58f), stroke.width, cap = StrokeCap.Round)
        drawLine(color, Offset(size.width * 0.88f, size.height * 0.78f), Offset(size.width * 0.88f, size.height * 0.58f), stroke.width, cap = StrokeCap.Round)
    }
}

@Composable
fun CallIcon(color: Color, modifier: Modifier = Modifier) {
    Canvas(modifier.size(20.dp)) {
        val stroke = Stroke(1.5.dp.toPx(), cap = StrokeCap.Round)
        drawArc(color, 220f, 100f, false, topLeft = Offset(size.width * 0.15f, size.height * 0.15f), size = androidx.compose.ui.geometry.Size(size.width * 0.7f, size.height * 0.7f), style = stroke)
    }
}

@Composable
fun PlayIcon(color: Color, modifier: Modifier = Modifier) {
    Canvas(modifier.size(18.dp)) {
        val path = androidx.compose.ui.graphics.Path().apply {
            moveTo(size.width * 0.28f, size.height * 0.18f)
            lineTo(size.width * 0.78f, size.height * 0.5f)
            lineTo(size.width * 0.28f, size.height * 0.82f)
            close()
        }
        drawPath(path, color)
    }
}

@Composable
fun CloseIcon(color: Color, modifier: Modifier = Modifier) {
    Canvas(modifier.size(18.dp)) {
        val stroke = 1.5.dp.toPx()
        drawLine(color, Offset(size.width * 0.25f, size.height * 0.25f), Offset(size.width * 0.75f, size.height * 0.75f), stroke, cap = StrokeCap.Round)
        drawLine(color, Offset(size.width * 0.75f, size.height * 0.25f), Offset(size.width * 0.25f, size.height * 0.75f), stroke, cap = StrokeCap.Round)
    }
}

@Composable
fun ArrowIcon(color: Color, modifier: Modifier = Modifier) {
    Canvas(modifier.size(18.dp)) {
        val stroke = 1.5.dp.toPx()
        drawLine(color, Offset(size.width * 0.15f, size.height * 0.5f), Offset(size.width * 0.78f, size.height * 0.5f), stroke, cap = StrokeCap.Round)
        drawLine(color, Offset(size.width * 0.52f, size.height * 0.25f), Offset(size.width * 0.78f, size.height * 0.5f), stroke, cap = StrokeCap.Round)
        drawLine(color, Offset(size.width * 0.52f, size.height * 0.75f), Offset(size.width * 0.78f, size.height * 0.5f), stroke, cap = StrokeCap.Round)
    }
}

@Composable
fun ChevronIcon(color: Color, modifier: Modifier = Modifier) {
    Canvas(modifier.size(16.dp)) {
        val stroke = 1.5.dp.toPx()
        drawLine(color, Offset(size.width * 0.35f, size.height * 0.2f), Offset(size.width * 0.65f, size.height * 0.5f), stroke, cap = StrokeCap.Round)
        drawLine(color, Offset(size.width * 0.65f, size.height * 0.5f), Offset(size.width * 0.35f, size.height * 0.8f), stroke, cap = StrokeCap.Round)
    }
}

@Composable
fun PlusIcon(color: Color, modifier: Modifier = Modifier) {
    Canvas(modifier.size(18.dp)) {
        val stroke = 1.5.dp.toPx()
        drawLine(color, Offset(size.width * 0.5f, size.height * 0.2f), Offset(size.width * 0.5f, size.height * 0.8f), stroke, cap = StrokeCap.Round)
        drawLine(color, Offset(size.width * 0.2f, size.height * 0.5f), Offset(size.width * 0.8f, size.height * 0.5f), stroke, cap = StrokeCap.Round)
    }
}

@Composable
fun BackIcon(color: Color, modifier: Modifier = Modifier) {
    Canvas(modifier.size(20.dp)) {
        val stroke = 1.5.dp.toPx()
        drawLine(color, Offset(size.width * 0.62f, size.height * 0.2f), Offset(size.width * 0.32f, size.height * 0.5f), stroke, cap = StrokeCap.Round)
        drawLine(color, Offset(size.width * 0.32f, size.height * 0.5f), Offset(size.width * 0.62f, size.height * 0.8f), stroke, cap = StrokeCap.Round)
    }
}

@Composable
fun CheckIcon(color: Color, modifier: Modifier = Modifier) {
    Canvas(modifier.size(16.dp)) {
        val stroke = 1.7.dp.toPx()
        drawLine(color, Offset(size.width * 0.2f, size.height * 0.52f), Offset(size.width * 0.42f, size.height * 0.74f), stroke, cap = StrokeCap.Round)
        drawLine(color, Offset(size.width * 0.42f, size.height * 0.74f), Offset(size.width * 0.8f, size.height * 0.28f), stroke, cap = StrokeCap.Round)
    }
}
