package com.familyshield.app.ui.caseflow

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Text
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Rect
import androidx.compose.ui.geometry.RoundRect
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Outline
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.unit.Density
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.familyshield.app.R
import com.familyshield.app.data.api.Claims
import com.familyshield.app.data.api.ParentCase
import com.familyshield.app.domain.CaseColor
import com.familyshield.app.domain.CaseCopy
import com.familyshield.app.domain.Times
import com.familyshield.app.domain.V3Format
import com.familyshield.app.ui.common.ErrorText
import com.familyshield.app.ui.common.UiText
import com.familyshield.app.ui.common.copyText
import com.familyshield.app.ui.common.shareText
import com.familyshield.app.ui.theme.LocalFsPalette
import com.familyshield.app.ui.theme.Pretendard
import com.familyshield.app.ui.v3.BackIcon
import com.familyshield.app.ui.v3.CallIcon
import com.familyshield.app.ui.v3.CountdownBar
import com.familyshield.app.ui.v3.FaceIcon
import com.familyshield.app.ui.v3.InkButton
import com.familyshield.app.ui.v3.InitialAvatar
import com.familyshield.app.ui.v3.LimeButton
import com.familyshield.app.ui.v3.PhoneIcon
import java.time.Instant

private val ResultInk = Color(0xFF0D1015)
private val ResultCream = Color(0xFFF3F0E9)
private val AvatarOnInk = Color(0xFFE4E1D8)

@Composable
fun ProgressScreen(case: ParentCase, pollError: Boolean, onBack: () -> Unit, now: Instant) {
    val palette = LocalFsPalette.current
    val locale = LocalConfiguration.current.locales[0]
    val name = case.childDisplayName.ifBlank { stringResource(R.string.cd_child) }
    val waiting = case.state == "waiting_push"
    val remaining = if (waiting) V3Format.remainingSeconds(Times.parse(case.deadlineAt), now) else null
    val amount = case.claims?.amount.known()
    Column(
        Modifier.fillMaxSize().background(palette.bg).verticalScroll(rememberScrollState()).padding(horizontal = 20.dp).testTag("case_screen"),
    ) {
        Row(Modifier.fillMaxWidth().padding(top = 8.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(
                Modifier.size(44.dp).testTag("back").clickable(onClick = onBack),
                contentAlignment = Alignment.Center,
            ) { BackIcon(palette.text) }
            Text(
                stringResource(R.string.case_title, name),
                modifier = Modifier.weight(1f),
                color = palette.text,
                fontFamily = Pretendard,
                fontWeight = FontWeight(650),
                fontSize = 17.sp,
                textAlign = androidx.compose.ui.text.style.TextAlign.Center,
            )
            Spacer(Modifier.width(44.dp))
        }
        Row(Modifier.padding(top = 20.dp), verticalAlignment = Alignment.CenterVertically) {
            InitialAvatar(name, size = 56.dp)
            Column(Modifier.padding(start = 12.dp)) {
                Text(name, color = palette.text, fontFamily = Pretendard, fontWeight = FontWeight(650), fontSize = 20.sp)
                amount?.let { Text(stringResource(R.string.home_amount_line, it), color = palette.muted, fontFamily = Pretendard, fontSize = 14.sp) }
            }
        }
        if (remaining != null) {
            Column(Modifier.fillMaxWidth().padding(top = 28.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                Text(stringResource(R.string.home_until_call), color = palette.muted, fontFamily = Pretendard, fontSize = 14.sp)
                Text(
                    V3Format.clock(remaining),
                    color = palette.text,
                    fontFamily = Pretendard,
                    fontWeight = FontWeight(600),
                    fontSize = 64.sp,
                    lineHeight = 76.sp,
                )
                CountdownBar(remaining, Modifier.padding(top = 12.dp))
                Text(
                    stringResource(R.string.progress_waiting),
                    color = palette.text,
                    fontFamily = Pretendard,
                    fontSize = 16.sp,
                    modifier = Modifier.padding(top = 12.dp),
                )
            }
        } else {
            Text(
                stringResource(CaseCopy.openLine(case.state), name),
                color = palette.text,
                fontFamily = Pretendard,
                fontSize = 17.sp,
                modifier = Modifier.padding(top = 24.dp),
            )
        }
        Column(
            Modifier.padding(top = 24.dp).fillMaxWidth().clip(RoundedCornerShape(24.dp)).background(palette.surface).padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            StepLine(0, case.state, stringResource(R.string.progress_step_push_title), stringResource(R.string.progress_step_push_body, Times.shortTime(case.createdAt, locale)))
            StepLine(1, case.state, stringResource(R.string.progress_step_bio_title), stringResource(R.string.progress_step_bio_body, name))
            val callBody = case.phoneLast4?.let { stringResource(R.string.progress_step_call_body, it) } ?: stringResource(R.string.progress_step_call_none)
            StepLine(2, case.state, stringResource(R.string.progress_step_call_title), callBody)
        }
        if (case.parentText.isNotBlank()) {
            Text(stringResource(R.string.progress_voice_label), color = palette.text, fontFamily = Pretendard, fontWeight = FontWeight(650), fontSize = 16.sp, modifier = Modifier.padding(top = 24.dp))
            Text(stringResource(R.string.progress_text_only), color = palette.muted, fontFamily = Pretendard, fontSize = 14.sp, modifier = Modifier.padding(top = 4.dp))
            Text(case.parentText, color = palette.text, fontFamily = Pretendard, fontSize = 15.sp, modifier = Modifier.padding(top = 8.dp))
        }
        Text(
            stringResource(R.string.case_dont_send),
            color = palette.text,
            fontFamily = Pretendard,
            fontWeight = FontWeight(650),
            fontSize = 17.sp,
            modifier = Modifier.fillMaxWidth().padding(top = 28.dp, bottom = 8.dp).testTag("dont_send"),
            textAlign = androidx.compose.ui.text.style.TextAlign.Center,
        )
        case.claims?.takeIf { it.hasAnything() }?.let { claims ->
            Text(stringResource(R.string.claims_heading), color = palette.text, fontFamily = Pretendard, fontWeight = FontWeight(650), modifier = Modifier.padding(top = 8.dp))
            claims.claimedIdentity.known()?.let { Text(stringResource(R.string.claims_identity, it), color = palette.muted, fontFamily = Pretendard) }
            claims.amount.known()?.let { Text(stringResource(R.string.claims_amount, it), color = palette.muted, fontFamily = Pretendard) }
            claims.story.known()?.let { Text(stringResource(R.string.claims_story, it), color = palette.muted, fontFamily = Pretendard) }
        }
        if (case.timeline.isNotEmpty()) {
            Text(stringResource(R.string.case_timeline_heading), color = palette.muted, fontFamily = Pretendard, modifier = Modifier.padding(top = 12.dp))
            case.timeline.forEach { step ->
                Text(stringResource(CaseCopy.timelineStep(step)), color = palette.muted, fontFamily = Pretendard, fontSize = 13.sp)
            }
        }
        if (pollError) ErrorText(UiText(R.string.case_update_failed))
        Spacer(Modifier.height(24.dp))
    }
}

@Composable
private fun StepLine(index: Int, state: String, title: String, body: String) {
    val palette = LocalFsPalette.current
    val active = when (state) {
        "calling" -> 2
        "awaiting_answer" -> 1
        else -> 0
    }
    val color = if (index <= active) palette.text else palette.muted
    Row(verticalAlignment = Alignment.Top) {
        when (index) {
            0 -> PhoneIcon(color)
            1 -> FaceIcon(color)
            else -> CallIcon(color)
        }
        Column(Modifier.padding(start = 12.dp)) {
            Text(title, color = color, fontFamily = Pretendard, fontWeight = FontWeight(650), fontSize = 16.sp)
            Text(body, color = palette.muted, fontFamily = Pretendard, fontSize = 14.sp)
        }
    }
}

@Composable
fun ResultScreen(case: ParentCase, color: CaseColor, onBack: () -> Unit) {
    val palette = LocalFsPalette.current
    val locale = LocalConfiguration.current.locales[0]
    val context = LocalContext.current
    val name = case.childDisplayName.ifBlank { stringResource(R.string.cd_child) }
    val korean = locale.language == "ko"
    val subject = V3Format.subject(name, korean)
    val confirmed = color == CaseColor.GREEN
    val bubble = if (confirmed) palette.lime else palette.answerNo
    val headline = if (confirmed) stringResource(R.string.v3_headline_yes, subject) else stringResource(R.string.v3_headline_no, subject)
    val word = if (confirmed) stringResource(R.string.child_yes) else stringResource(R.string.child_no)
    val detail = if (confirmed) stringResource(R.string.v3_yes_detail) else stringResource(R.string.v3_no_detail)
    val whenLabel = Times.shortTime(case.decidedAt, locale)
    val amount = case.claims?.amount.known()
    val copy = CaseCopy.result(color, case.result)
    val story = case.claims?.story.known()
    val message = if (story == null) {
        stringResource(R.string.family_alert_message, name)
    } else {
        stringResource(R.string.family_alert_message_with_story, name, story)
    }
    var detailsOpen by remember { mutableStateOf(false) }
    Column(Modifier.fillMaxSize().background(ResultInk).testTag("case_screen")) {
        Row(Modifier.fillMaxWidth().padding(top = 8.dp, start = 8.dp, end = 20.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(
                Modifier.size(44.dp).testTag("back").clickable(onClick = onBack),
                contentAlignment = Alignment.Center,
            ) { BackIcon(ResultCream) }
            Text(
                stringResource(R.string.v3_result_nav),
                modifier = Modifier.weight(1f),
                color = ResultCream,
                fontFamily = Pretendard,
                fontWeight = FontWeight(650),
                fontSize = 17.sp,
                textAlign = androidx.compose.ui.text.style.TextAlign.Center,
            )
            Spacer(Modifier.width(44.dp))
        }
        Column(
            Modifier
                .weight(1f)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 20.dp),
        ) {
            Text(stringResource(R.string.v3_direct), color = palette.heroMuted, fontFamily = FontFamily.Monospace, fontSize = 12.sp, letterSpacing = 0.6.sp, modifier = Modifier.padding(top = 12.dp))
            Row(
                Modifier.fillMaxWidth().padding(top = 16.dp, start = 15.dp, end = 15.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.width(72.dp)) {
                    InitialAvatar(name, size = 72.dp, background = AvatarOnInk, foreground = ResultInk)
                    Text(name, color = ResultCream, fontFamily = Pretendard, fontSize = 14.sp, modifier = Modifier.padding(top = 6.dp))
                }
                Column(
                    Modifier
                        .padding(start = 16.dp)
                        .weight(1f)
                        .heightIn(min = 128.dp)
                        .background(bubble, AnswerBubbleShape())
                        .padding(start = 30.dp, end = 20.dp, top = 16.dp, bottom = 16.dp),
                    horizontalAlignment = Alignment.Start,
                ) {
                    Text(stringResource(R.string.v3_answer_caption), color = ResultInk, fontFamily = Pretendard, fontWeight = FontWeight(500), fontSize = 12.sp, lineHeight = 18.sp)
                    Text(word, color = ResultInk, fontFamily = Pretendard, fontWeight = FontWeight(700), fontSize = 38.sp, lineHeight = 46.sp)
                    Text(detail, color = ResultInk, fontFamily = Pretendard, fontSize = 14.sp, lineHeight = 21.sp)
                }
            }
            Text(headline, color = ResultCream, fontFamily = Pretendard, fontWeight = FontWeight(700), fontSize = 38.sp, lineHeight = 46.sp, modifier = Modifier.padding(top = 28.dp))
            Row(Modifier.fillMaxWidth().padding(top = 12.dp)) {
                amount?.let { Text(stringResource(R.string.home_amount_line, it), color = palette.heroMuted, fontFamily = Pretendard, fontSize = 14.sp, modifier = Modifier.weight(1f)) }
                if (whenLabel.isNotBlank()) Text(whenLabel, color = palette.heroMuted, fontFamily = Pretendard, fontSize = 14.sp)
            }
        }
        Column(
            Modifier
                .padding(horizontal = 20.dp)
                .navigationBarsPadding()
                .padding(bottom = 20.dp)
                .heightIn(max = 520.dp)
                .clip(RoundedCornerShape(24.dp))
                .background(palette.sheet)
                .verticalScroll(rememberScrollState())
                .padding(20.dp)
                .testTag("result_card"),
        ) {
            val sheetTitle = if (confirmed) stringResource(R.string.v3_sheet_yes) else stringResource(R.string.v3_sheet_scam)
            val shortLine = if (confirmed) {
                stringResource(R.string.v3_sheet_yes_body, name)
            } else {
                stringResource(R.string.v3_sheet_scam_line)
            }
            Text(sheetTitle, color = palette.sheetText, fontFamily = Pretendard, fontWeight = FontWeight(700), fontSize = 20.sp, lineHeight = 28.sp, modifier = Modifier.testTag("result_title"))
            Text(shortLine, color = palette.sheetMuted, fontFamily = Pretendard, fontSize = 15.sp, lineHeight = 22.sp, modifier = Modifier.padding(top = 8.dp))
            Text(
                stringResource(if (detailsOpen) R.string.v3_details_hide else R.string.v3_details),
                color = palette.sheetText,
                fontFamily = Pretendard,
                fontWeight = FontWeight(500),
                fontSize = 15.sp,
                modifier = Modifier
                    .padding(top = 4.dp)
                    .heightIn(min = 44.dp)
                    .clickable { detailsOpen = !detailsOpen }
                    .testTag("result_details"),
            )
            if (detailsOpen) {
                if (copy != null) {
                    Text(
                        stringResource(copy.body, name, whenLabel),
                        color = palette.sheetMuted,
                        fontFamily = Pretendard,
                        fontSize = 15.sp,
                        lineHeight = 22.sp,
                        modifier = Modifier.padding(bottom = 8.dp).testTag("result_body"),
                    )
                }
                if (!confirmed) {
                    Text(stringResource(R.string.family_alert_heading), color = palette.sheetText, fontFamily = Pretendard, fontWeight = FontWeight(650), fontSize = 16.sp)
                    Text(message, color = palette.sheetMuted, fontFamily = Pretendard, fontSize = 15.sp, lineHeight = 22.sp, modifier = Modifier.padding(top = 6.dp).testTag("family_alert"))
                    Text(
                        stringResource(R.string.action_copy),
                        color = palette.sheetMuted,
                        fontFamily = Pretendard,
                        modifier = Modifier
                            .padding(top = 8.dp, bottom = 8.dp)
                            .heightIn(min = 44.dp)
                            .testTag("alert_copy")
                            .clickable {
                                copyText(context, context.getString(R.string.family_alert_clip_label), message)
                            },
                    )
                }
            }
            if (confirmed) {
                LimeButton(stringResource(R.string.v3_done), onClick = onBack, modifier = Modifier.padding(top = 8.dp))
            } else {
                InkButton(
                    label = stringResource(R.string.v3_share),
                    onClick = { shareText(context, context.getString(R.string.family_alert_share_title), message) },
                    // Same #FF9991 and ink as the 아니요 bubble, in both themes. Contrast is 9.27:1.
                    background = palette.answerNo,
                    foreground = palette.ink,
                    modifier = Modifier.padding(top = 8.dp),
                )
            }
        }
    }
}

@Composable
fun YellowScreen(case: ParentCase, onBack: () -> Unit) {
    val palette = LocalFsPalette.current
    val locale = LocalConfiguration.current.locales[0]
    val name = case.childDisplayName.ifBlank { stringResource(R.string.cd_child) }
    val whenLabel = Times.shortTime(case.decidedAt, locale)
    val copy = CaseCopy.result(CaseColor.YELLOW, case.result)
    Column(Modifier.fillMaxSize().background(palette.bg).verticalScroll(rememberScrollState()).padding(20.dp).testTag("case_screen")) {
        Box(Modifier.size(44.dp).testTag("back").clickable(onClick = onBack), contentAlignment = Alignment.Center) {
            BackIcon(palette.text)
        }
        Text(stringResource(R.string.cd_status_yellow), color = palette.yellow, fontFamily = Pretendard, fontWeight = FontWeight(700), fontSize = 32.sp, modifier = Modifier.padding(top = 16.dp).testTag("result_title"))
        if (copy != null) {
            Text(stringResource(copy.body, name, whenLabel), color = palette.text, fontFamily = Pretendard, fontSize = 17.sp, modifier = Modifier.padding(top = 12.dp).testTag("result_body"))
        }
    }
}

/** Rounded answer bubble with a short tail toward the avatar. Body radius 22pt, tail about 10pt. */
private class AnswerBubbleShape : Shape {
    override fun createOutline(size: Size, layoutDirection: LayoutDirection, density: Density): Outline {
        val tail = with(density) { 10.dp.toPx() }
        val radius = with(density) { 22.dp.toPx() }
        val path = Path().apply {
            addRoundRect(
                RoundRect(
                    Rect(tail, 0f, size.width, size.height),
                    CornerRadius(radius),
                ),
            )
            val cy = size.height / 2f
            moveTo(tail, cy - tail * 0.9f)
            lineTo(0f, cy)
            lineTo(tail, cy + tail * 0.75f)
            close()
        }
        return Outline.Generic(path)
    }
}

private fun Claims.hasAnything(): Boolean =
    claimedIdentity.known() != null || amount.known() != null || story.known() != null || redFlags.any { it.known() != null }

private fun String?.known(): String? = this?.trim()?.takeIf { it.isNotEmpty() && !it.equals("unknown", ignoreCase = true) }
