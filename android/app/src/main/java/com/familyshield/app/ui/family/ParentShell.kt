package com.familyshield.app.ui.family

import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.familyshield.app.R
import com.familyshield.app.data.api.CaseSummary
import com.familyshield.app.data.api.Member
import com.familyshield.app.domain.CaseColor
import com.familyshield.app.domain.MemberRules
import com.familyshield.app.domain.Times
import com.familyshield.app.domain.V3Format
import com.familyshield.app.ui.common.ErrorText
import com.familyshield.app.ui.common.NoticeText
import com.familyshield.app.ui.theme.LocalFsPalette
import com.familyshield.app.ui.theme.Pretendard
import com.familyshield.app.ui.v3.ArrowIcon
import com.familyshield.app.ui.v3.CallIcon
import com.familyshield.app.ui.v3.ChevronIcon
import com.familyshield.app.ui.v3.FaceIcon
import com.familyshield.app.ui.v3.InkButton
import com.familyshield.app.ui.v3.HomeTab
import com.familyshield.app.ui.v3.InitialAvatar
import com.familyshield.app.ui.v3.LimeButton
import com.familyshield.app.ui.v3.PhoneIcon
import com.familyshield.app.ui.v3.PlusIcon
import com.familyshield.app.ui.v3.TabBar
import com.familyshield.app.ui.v3.TabLabels
import com.familyshield.app.ui.v3.Waveform
import kotlinx.coroutines.delay
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId
import java.time.format.DateTimeFormatter

@Composable
fun ParentShell(
    familyName: String,
    parentName: String,
    state: FamilyUiState,
    now: Instant,
    initialTab: HomeTab,
    ticking: Boolean,
    onRefresh: () -> Unit,
    onSignOut: () -> Unit,
    onAdd: () -> Unit,
    onVerifyChild: (String) -> Unit,
    onNewCase: () -> Unit,
    onConfirmJoin: (String) -> Unit,
    onRejectJoin: (String) -> Unit,
    onConfirmPhone: (String) -> Unit,
    onRejectPhone: (String) -> Unit,
    onReissue: (String) -> Unit,
    onCallOnly: (String) -> Unit,
    onOpenRecent: (CaseSummary) -> Unit,
) {
    val palette = LocalFsPalette.current
    var tab by rememberSaveable { mutableStateOf(initialTab) }
    var openChildId by rememberSaveable { mutableStateOf<String?>(null) }
    var clock by remember { mutableStateOf(now) }
    LaunchedEffect(ticking) {
        if (!ticking) return@LaunchedEffect
        while (true) {
            clock = Instant.now()
            delay(1000)
        }
    }
    val moment = if (ticking) clock else now
    val children = state.members.filter { MemberRules.isChild(it) }
    val parent = state.members.firstOrNull { it.role == "parent" }
    val shownParent = parentName.ifBlank { parent?.displayName.orEmpty() }
    Column(Modifier.fillMaxSize().background(palette.bg).testTag("family_home")) {
        Box(Modifier.weight(1f)) {
            when (tab) {
                HomeTab.Home -> HomeTabContent(
                    parentName = shownParent,
                    children = children,
                    recent = state.recent,
                    notice = state.notice,
                    error = if (state.members.isNotEmpty()) state.error else null,
                    moment = moment,
                    onNewCase = onNewCase,
                    onAdd = onAdd,
                    onSeeFamily = { tab = HomeTab.Family },
                    onSeeHistory = { tab = HomeTab.History },
                    onOpen = onOpenRecent,
                    onRefresh = onRefresh,
                    onSignOut = onSignOut,
                )
                HomeTab.History -> HistoryTabContent(
                    parentName = shownParent,
                    recent = state.recent,
                    moment = moment,
                    onOpen = onOpenRecent,
                    onRefresh = onRefresh,
                    onSignOut = onSignOut,
                )
                HomeTab.Family -> FamilyTabContent(
                    familyName = familyName,
                    parentName = shownParent,
                    children = children,
                    state = state,
                    now = moment,
                    openId = openChildId,
                    onOpenChild = { openChildId = it },
                    onAdd = onAdd,
                    onVerifyChild = onVerifyChild,
                    onConfirmJoin = onConfirmJoin,
                    onRejectJoin = onRejectJoin,
                    onConfirmPhone = onConfirmPhone,
                    onRejectPhone = onRejectPhone,
                    onReissue = onReissue,
                    onCallOnly = onCallOnly,
                    onRefresh = onRefresh,
                    onSignOut = onSignOut,
                )
            }
        }
        if (tab == HomeTab.Family && openChildId == null) {
            LimeButton(
                label = stringResource(R.string.family_add_child),
                onClick = onAdd,
                modifier = Modifier.padding(horizontal = 20.dp, vertical = 8.dp).testTag("add_child"),
            )
        }
        TabBar(
            selected = tab,
            onSelect = { tab = it },
            labels = TabLabels(
                stringResource(R.string.tab_home),
                stringResource(R.string.tab_history),
                stringResource(R.string.tab_family),
            ),
        )
    }
}

@Composable
private fun HomeTabContent(
    parentName: String,
    children: List<Member>,
    recent: List<CaseSummary>,
    notice: com.familyshield.app.ui.common.UiText?,
    error: com.familyshield.app.ui.common.UiText?,
    moment: Instant,
    onNewCase: () -> Unit,
    onAdd: () -> Unit,
    onSeeFamily: () -> Unit,
    onSeeHistory: () -> Unit,
    onOpen: (CaseSummary) -> Unit,
    onRefresh: () -> Unit,
    onSignOut: () -> Unit,
) {
    val open = recent.firstOrNull { CaseColor.of(it.color, it.decidedAt) == CaseColor.OPEN }
    val latest = recent.firstOrNull { CaseColor.of(it.color, it.decidedAt) != CaseColor.OPEN }
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 20.dp),
    ) {
        BrandRow(parentName, onRefresh, onSignOut)
        val headline = if (open != null) {
            stringResource(R.string.home_live_title, open.childDisplayName)
        } else {
            greeting(parentName)
        }
        Text(
            headline,
            modifier = Modifier.padding(top = 16.dp, bottom = 20.dp),
            style = androidx.compose.material3.MaterialTheme.typography.headlineMedium,
            color = LocalFsPalette.current.text,
        )
        if (open != null) {
            LiveHero(open, moment, onOpen)
        } else {
            IdleHero(onNewCase)
        }
        notice?.let { NoticeText(it, Modifier.padding(top = 16.dp)) }
        error?.let { ErrorText(it, Modifier.padding(top = 8.dp)) }
        SectionTitle(
            stringResource(R.string.family_title_fallback),
            stringResource(R.string.home_see_all),
            onSeeFamily,
            Modifier.padding(top = 28.dp, bottom = 16.dp),
        )
        if (children.isEmpty()) {
            Text(
                stringResource(R.string.family_empty_title),
                color = LocalFsPalette.current.text,
                fontFamily = Pretendard,
                fontWeight = FontWeight(650),
                fontSize = 17.sp,
            )
            Text(
                stringResource(R.string.family_empty_body),
                color = LocalFsPalette.current.muted,
                fontFamily = Pretendard,
                fontSize = 15.sp,
                modifier = Modifier.padding(top = 8.dp),
            )
        } else {
            Row(horizontalArrangement = Arrangement.spacedBy(18.dp)) {
                children.take(6).forEach { child ->
                    PersonChip(child.displayName, stringResource(R.string.home_using_app))
                }
                AddChip(onAdd)
            }
        }
        SectionTitle(
            stringResource(R.string.family_recent_heading),
            stringResource(R.string.home_see_all),
            onSeeHistory,
            Modifier.padding(top = 28.dp, bottom = 12.dp),
        )
        if (latest == null) {
            Text(stringResource(R.string.family_recent_empty), color = LocalFsPalette.current.muted, fontFamily = Pretendard, fontSize = 15.sp)
        } else {
            CaseCard(latest, moment, onOpen)
        }
        Spacer(Modifier.height(24.dp))
    }
}

@Composable
private fun IdleHero(onNewCase: () -> Unit) {
    val palette = LocalFsPalette.current
    Column(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(26.dp))
            .background(palette.hero)
            .padding(20.dp),
    ) {
        Text(
            stringResource(R.string.home_hero_kicker),
            color = palette.heroMuted,
            fontFamily = FontFamily.Monospace,
            fontWeight = FontWeight(500),
            fontSize = 12.sp,
            letterSpacing = 0.6.sp,
        )
        Text(
            stringResource(R.string.home_hero_title),
            color = palette.sheet,
            fontFamily = Pretendard,
            fontWeight = FontWeight(600),
            fontSize = 24.sp,
            lineHeight = 31.sp,
            letterSpacing = (-0.75).sp,
            modifier = Modifier.padding(top = 12.dp),
        )
        Waveform(palette.lime, Modifier.padding(top = 18.dp, bottom = 18.dp))
        LimeButton(
            label = stringResource(R.string.family_verify_message),
            onClick = onNewCase,
            modifier = Modifier.testTag("verify_message"),
            trailing = { ArrowIcon(palette.ink) },
        )
    }
}

@Composable
private fun LiveHero(summary: CaseSummary, moment: Instant, onOpen: (CaseSummary) -> Unit) {
    val palette = LocalFsPalette.current
    val waiting = summary.state == "waiting_push"
    val remaining = if (waiting) V3Format.remainingSeconds(Times.parse(summary.deadlineAt), moment) else null
    Column(
        Modifier.fillMaxWidth().clip(RoundedCornerShape(26.dp)).background(palette.hero).padding(20.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            InitialAvatar(summary.childDisplayName, size = 48.dp, background = ColorAvatarOnHero, foreground = palette.ink)
            Column(Modifier.padding(start = 12.dp).weight(1f)) {
                Text(summary.childDisplayName, color = palette.sheet, fontFamily = Pretendard, fontWeight = FontWeight(650), fontSize = 20.sp)
                summary.requestAmount?.let {
                    Text(stringResource(R.string.home_amount_line, it), color = palette.heroMuted, fontFamily = Pretendard, fontSize = 14.sp)
                }
            }
            if (remaining != null) {
                Column(horizontalAlignment = Alignment.End) {
                    Text(stringResource(R.string.home_until_call), color = palette.heroMuted, fontFamily = Pretendard, fontSize = 12.sp)
                    Text(
                        V3Format.clock(remaining),
                        color = palette.lime,
                        fontFamily = Pretendard,
                        fontWeight = FontWeight(600),
                        fontSize = 44.sp,
                        lineHeight = 50.sp,
                    )
                }
            }
        }
        StepTrio(summary.state, Modifier.padding(top = 18.dp, bottom = 16.dp), onHero = true)
        InkButton(
            label = stringResource(R.string.home_open_progress),
            onClick = { onOpen(summary) },
            background = if (palette.isDark) palette.sheet else palette.surface,
            foreground = palette.ink,
        )
    }
}

private val ColorAvatarOnHero = androidx.compose.ui.graphics.Color(0xFFE4E1D8)

@Composable
private fun StepTrio(state: String, modifier: Modifier, onHero: Boolean) {
    val palette = LocalFsPalette.current
    val active = when (state) {
        "calling" -> 2
        "awaiting_answer" -> 1
        else -> 0
    }
    val labels = listOf(
        stringResource(R.string.home_step_push),
        stringResource(R.string.home_step_bio),
        stringResource(R.string.home_step_call),
    )
    Row(modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        labels.forEachIndexed { index, label ->
            val color = when {
                index < active -> palette.lime
                index == active -> palette.lime
                else -> palette.heroFuture
            }
            Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.width(72.dp)) {
                when (index) {
                    0 -> PhoneIcon(color)
                    1 -> FaceIcon(color)
                    else -> CallIcon(color)
                }
                Text(label, color = color, fontFamily = Pretendard, fontSize = 12.sp, fontWeight = FontWeight(500), textAlign = TextAlign.Center)
            }
            if (index < labels.lastIndex) {
                Box(Modifier.weight(1f).height(1.dp).background(if (onHero) palette.heroFuture else palette.line))
            }
        }
    }
}

@Composable
private fun HistoryTabContent(
    parentName: String,
    recent: List<CaseSummary>,
    moment: Instant,
    onOpen: (CaseSummary) -> Unit,
    onRefresh: () -> Unit,
    onSignOut: () -> Unit,
) {
    var filter by rememberSaveable { mutableStateOf("all") }
    val decided = recent.filter { CaseColor.of(it.color, it.decidedAt) != CaseColor.OPEN }
    val shown = decided.filter { row ->
        val color = CaseColor.of(row.color, row.decidedAt)
        when (filter) {
            "green" -> color == CaseColor.GREEN
            "red" -> color == CaseColor.RED
            "yellow" -> color == CaseColor.YELLOW
            else -> true
        }
    }
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 20.dp)) {
        BrandRow(parentName, onRefresh, onSignOut)
        Text(
            stringResource(R.string.history_title),
            style = androidx.compose.material3.MaterialTheme.typography.headlineLarge,
            color = LocalFsPalette.current.text,
            modifier = Modifier.padding(top = 12.dp, bottom = 16.dp),
        )
        FilterRow(filter) { filter = it }
        if (shown.isEmpty()) {
            Text(stringResource(R.string.history_empty), color = LocalFsPalette.current.muted, fontFamily = Pretendard, modifier = Modifier.padding(top = 24.dp))
        } else {
            HistoryGroups(shown, moment, onOpen)
        }
        Spacer(Modifier.height(24.dp))
    }
}

@Composable
private fun FilterRow(selected: String, onSelect: (String) -> Unit) {
    val items = listOf(
        "all" to stringResource(R.string.history_all),
        "green" to stringResource(R.string.history_green),
        "red" to stringResource(R.string.history_red),
        "yellow" to stringResource(R.string.history_yellow),
    )
    val palette = LocalFsPalette.current
    Row(horizontalArrangement = Arrangement.spacedBy(16.dp), modifier = Modifier.fillMaxWidth()) {
        items.forEach { (id, label) ->
            val on = id == selected
            Column(Modifier.clickable { onSelect(id) }.padding(bottom = 8.dp)) {
                Text(label, color = if (on) palette.text else palette.muted, fontFamily = Pretendard, fontWeight = if (on) FontWeight(650) else FontWeight(500), fontSize = 15.sp)
                Box(Modifier.padding(top = 8.dp).height(2.dp).width(28.dp).background(if (on) palette.text else palette.bg))
            }
        }
    }
    Box(Modifier.fillMaxWidth().height(0.5.dp).background(palette.line))
}

@Composable
private fun FamilyTabContent(
    familyName: String,
    parentName: String,
    children: List<Member>,
    state: FamilyUiState,
    now: Instant,
    openId: String?,
    onOpenChild: (String?) -> Unit,
    onAdd: () -> Unit,
    onVerifyChild: (String) -> Unit,
    onConfirmJoin: (String) -> Unit,
    onRejectJoin: (String) -> Unit,
    onConfirmPhone: (String) -> Unit,
    onRejectPhone: (String) -> Unit,
    onReissue: (String) -> Unit,
    onCallOnly: (String) -> Unit,
    onRefresh: () -> Unit,
    onSignOut: () -> Unit,
) {
    val palette = LocalFsPalette.current
    val opened = children.firstOrNull { it.id == openId }
    if (opened != null) {
        Column(Modifier.fillMaxSize().background(palette.bg).verticalScroll(rememberScrollState()).padding(horizontal = 20.dp)) {
            Row(Modifier.fillMaxWidth().padding(top = 8.dp), verticalAlignment = Alignment.CenterVertically) {
                Box(
                    Modifier.size(44.dp).clickable { onOpenChild(null) },
                    contentAlignment = Alignment.Center,
                ) { com.familyshield.app.ui.v3.BackIcon(palette.text) }
                Text(
                    opened.displayName.ifBlank { stringResource(R.string.cd_child) },
                    modifier = Modifier.weight(1f),
                    color = palette.text,
                    fontFamily = Pretendard,
                    fontWeight = FontWeight(650),
                    fontSize = 17.sp,
                    textAlign = androidx.compose.ui.text.style.TextAlign.Center,
                )
                Spacer(Modifier.size(44.dp))
            }
            ChildCard(
                member = opened,
                now = now,
                busy = state.busy,
                onVerify = { onVerifyChild(opened.id) },
                onConfirmJoin = { onConfirmJoin(opened.id) },
                onRejectJoin = { onRejectJoin(opened.id) },
                onConfirmPhone = { onConfirmPhone(opened.id) },
                onRejectPhone = { onRejectPhone(opened.id) },
                onReissue = { onReissue(opened.id) },
                onCallOnly = { onCallOnly(opened.id) },
            )
        }
        return
    }
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 20.dp)) {
        BrandRow(parentName, onRefresh, onSignOut)
        Text(
            familyName.ifBlank { stringResource(R.string.family_title_fallback) },
            style = androidx.compose.material3.MaterialTheme.typography.headlineLarge,
            color = palette.text,
            modifier = Modifier.padding(top = 12.dp, bottom = 16.dp),
        )
        state.notice?.let { NoticeText(it) }
        if (state.error != null) ErrorText(state.error)
        Row(
            Modifier.fillMaxWidth().clip(RoundedCornerShape(24.dp)).background(palette.surface).padding(16.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            InitialAvatar(parentName.ifBlank { familyName }, size = 52.dp)
            Column(Modifier.padding(start = 12.dp)) {
                Text(parentName.ifBlank { familyName }, color = palette.text, fontFamily = Pretendard, fontWeight = FontWeight(650), fontSize = 20.sp)
                Text(stringResource(R.string.family_role_parent), color = palette.muted, fontFamily = Pretendard, fontSize = 14.sp)
            }
        }
        Row(Modifier.fillMaxWidth().padding(top = 28.dp, bottom = 12.dp), verticalAlignment = Alignment.CenterVertically) {
            Text(stringResource(R.string.family_child_count, children.size), color = palette.text, fontFamily = Pretendard, fontWeight = FontWeight(650), fontSize = 20.sp, modifier = Modifier.weight(1f))
            Text(
                stringResource(R.string.family_invite_link),
                color = palette.muted,
                fontFamily = Pretendard,
                fontSize = 15.sp,
                modifier = Modifier.clickable(onClick = onAdd),
            )
        }
        if (children.isEmpty()) {
            Text(stringResource(R.string.family_empty_title), color = palette.text, fontFamily = Pretendard, fontWeight = FontWeight(650), fontSize = 17.sp)
        } else {
            Column(Modifier.clip(RoundedCornerShape(24.dp)).background(palette.surface)) {
                children.forEachIndexed { index, member ->
                    if (index > 0) Box(Modifier.padding(start = 76.dp).fillMaxWidth().height(0.5.dp).background(palette.line))
                    FamilyMemberRow(member) { onOpenChild(member.id) }
                }
            }
        }
        Spacer(Modifier.height(16.dp))
    }
}

@Composable
private fun FamilyMemberRow(member: Member, onOpen: () -> Unit) {
    val palette = LocalFsPalette.current
    val ready = MemberRules.canVerify(member)
    val name = member.displayName.ifBlank { stringResource(R.string.cd_child) }
    Row(
        Modifier
            .fillMaxWidth()
            .clickable(onClick = onOpen)
            .testTag("child_${member.id}")
            .padding(horizontal = 16.dp, vertical = 14.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        InitialAvatar(name, size = 48.dp)
        Column(Modifier.padding(start = 12.dp).weight(1f)) {
            Text(name, color = palette.text, fontFamily = Pretendard, fontWeight = FontWeight(650), fontSize = 17.sp)
            if (ready) {
                Text(stringResource(R.string.family_can_check), color = palette.muted, fontFamily = Pretendard, fontSize = 14.sp)
            }
            member.phoneLast4?.let {
                Text(stringResource(R.string.family_number_ending, it), color = palette.muted, fontFamily = Pretendard, fontSize = 14.sp)
            }
        }
        com.familyshield.app.ui.v3.ChevronIcon(palette.muted)
    }
}

@Composable
private fun BrandRow(name: String, onRefresh: () -> Unit, onSignOut: () -> Unit) {
    val palette = LocalFsPalette.current
    var open by remember { mutableStateOf(false) }
    Row(Modifier.fillMaxWidth().padding(top = 8.dp), verticalAlignment = Alignment.CenterVertically) {
        Text(
            stringResource(R.string.home_brand),
            color = palette.muted,
            fontFamily = FontFamily.Monospace,
            fontSize = 12.sp,
            letterSpacing = 0.8.sp,
            modifier = Modifier.weight(1f),
        )
        Box {
            InitialAvatar(
                name,
                size = 40.dp,
                background = palette.ink,
                foreground = palette.bg,
                modifier = Modifier.clickable { open = true },
            )
            DropdownMenu(expanded = open, onDismissRequest = { open = false }) {
                DropdownMenuItem(
                    text = { Text(stringResource(R.string.cd_refresh)) },
                    onClick = { open = false; onRefresh() },
                    modifier = Modifier.testTag("refresh"),
                )
                DropdownMenuItem(
                    text = { Text(stringResource(R.string.action_sign_out)) },
                    onClick = { open = false; onSignOut() },
                    modifier = Modifier.testTag("sign_out"),
                )
            }
        }
    }
}

@Composable
private fun SectionTitle(title: String, action: String, onAction: () -> Unit, modifier: Modifier = Modifier) {
    val palette = LocalFsPalette.current
    Row(modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Text(title, color = palette.text, fontFamily = Pretendard, fontWeight = FontWeight(700), fontSize = 20.sp, modifier = Modifier.weight(1f))
        Text(action, color = palette.muted, fontFamily = Pretendard, fontSize = 14.sp, modifier = Modifier.clickable(onClick = onAction))
    }
}

@Composable
private fun PersonChip(name: String, caption: String) {
    val palette = LocalFsPalette.current
    Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.width(72.dp)) {
        InitialAvatar(name, size = 64.dp)
        Text(name, color = palette.text, fontFamily = Pretendard, fontWeight = FontWeight(650), fontSize = 15.sp, modifier = Modifier.padding(top = 8.dp), textAlign = TextAlign.Center, maxLines = 1)
        Text(caption, color = palette.muted, fontFamily = Pretendard, fontSize = 12.sp, textAlign = TextAlign.Center)
    }
}

@Composable
private fun AddChip(onClick: () -> Unit) {
    val palette = LocalFsPalette.current
    Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.width(72.dp).clickable(onClick = onClick)) {
        Box(
            Modifier.size(64.dp).clip(CircleShape).border(1.dp, palette.line, CircleShape),
            contentAlignment = Alignment.Center,
        ) { PlusIcon(palette.muted) }
        Text(stringResource(R.string.family_add_child), color = palette.text, fontFamily = Pretendard, fontWeight = FontWeight(650), fontSize = 13.sp, modifier = Modifier.padding(top = 8.dp), textAlign = TextAlign.Center)
        Text(stringResource(R.string.family_invite_link), color = palette.muted, fontFamily = Pretendard, fontSize = 12.sp)
    }
}

@Composable
private fun CaseCard(summary: CaseSummary, moment: Instant, onOpen: (CaseSummary) -> Unit) {
    val palette = LocalFsPalette.current
    val color = CaseColor.of(summary.color, summary.decidedAt)
    val status = when (color) {
        CaseColor.GREEN -> stringResource(R.string.history_green) to palette.green
        CaseColor.RED -> stringResource(R.string.history_red) to palette.red
        CaseColor.YELLOW -> stringResource(R.string.history_yellow) to palette.yellow
        CaseColor.OPEN -> stringResource(R.string.cd_status_open) to palette.text
    }
    val description = status.first
    Row(
        Modifier
            .padding(bottom = 10.dp)
            .fillMaxWidth()
            .clip(RoundedCornerShape(20.dp))
            .background(palette.surface)
            .clickable(role = Role.Button) { onOpen(summary) }
            .semantics { contentDescription = description }
            .testTag("case_${summary.id}")
            .padding(14.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        InitialAvatar(summary.childDisplayName, size = 44.dp)
        Column(Modifier.padding(start = 12.dp).weight(1f)) {
            Text(
                stringResource(R.string.case_title, summary.childDisplayName),
                color = palette.text,
                fontFamily = Pretendard,
                fontWeight = FontWeight(650),
                fontSize = 17.sp,
            )
            summary.requestAmount?.let {
                Text(stringResource(R.string.home_amount_line, it), color = palette.muted, fontFamily = Pretendard, fontSize = 14.sp)
            }
        }
        Column(horizontalAlignment = Alignment.End) {
            Text(status.first, color = status.second, fontFamily = Pretendard, fontWeight = FontWeight(650), fontSize = 14.sp)
            Text(whenLabel(summary, moment), color = palette.muted, fontFamily = Pretendard, fontSize = 13.sp)
        }
    }
}

@Composable
private fun greeting(name: String): String =
    if (name.isBlank()) stringResource(R.string.home_greeting_plain) else stringResource(R.string.home_greeting, name)

@Composable
private fun whenLabel(summary: CaseSummary, moment: Instant): String {
    val locale = LocalConfiguration.current.locales[0]
    val zone = ZoneId.systemDefault()
    val instant = Times.parse(summary.decidedAt ?: summary.createdAt) ?: return ""
    val day = instant.atZone(zone).toLocalDate()
    val today = moment.atZone(zone).toLocalDate()
    val time = Times.shortTime(summary.decidedAt ?: summary.createdAt, locale, zone)
    val yesterday = stringResource(R.string.v3_yesterday)
    val todayLabel = stringResource(R.string.v3_today)
    return when (day) {
        today -> "$todayLabel $time"
        today.minusDays(1) -> "$yesterday $time"
        else -> time
    }
}

private fun groupByDay(rows: List<CaseSummary>, moment: Instant): List<Pair<String, List<CaseSummary>>> {
    val zone = ZoneId.systemDefault()
    val today = moment.atZone(zone).toLocalDate()
    val grouped = linkedMapOf<LocalDate, MutableList<CaseSummary>>()
    rows.forEach { row ->
        val instant = Times.parse(row.decidedAt ?: row.createdAt) ?: return@forEach
        val day = instant.atZone(zone).toLocalDate()
        grouped.getOrPut(day) { mutableListOf() }.add(row)
    }
    return grouped.map { (day, items) ->
        val label = when (day) {
            today -> "today"
            today.minusDays(1) -> "yesterday"
            else -> day.format(DateTimeFormatter.ofPattern("M월 d일"))
        }
        label to items
    }
}

@Composable
private fun HistoryGroups(rows: List<CaseSummary>, moment: Instant, onOpen: (CaseSummary) -> Unit) {
    // Labels that need string resources are resolved here, not in groupByDay.
    val palette = LocalFsPalette.current
    groupByDay(rows, moment).forEach { (key, items) ->
        val label = when (key) {
            "today" -> stringResource(R.string.v3_today)
            "yesterday" -> stringResource(R.string.v3_yesterday)
            else -> key
        }
        Text(label, color = palette.muted, fontFamily = Pretendard, fontSize = 14.sp, modifier = Modifier.padding(top = 20.dp, bottom = 8.dp))
        items.forEach { CaseCard(it, moment, onOpen) }
    }
}
