package com.familyshield.app

import com.familyshield.app.data.api.ChildCase
import com.familyshield.app.data.api.Claims
import com.familyshield.app.data.api.Member
import com.familyshield.app.data.api.ParentCase

fun sampleCase(
    id: String = "case-1",
    color: String = "open",
    result: String? = null,
    state: String = "calling",
    name: String = "Mina",
    decidedAt: String? = null,
    patternId: String? = null,
    claims: Claims? = null,
    timeline: List<String> = listOf("start"),
    parentText: String = "",
) = ParentCase(
    id = id,
    familyId = "fam-1",
    childMemberId = "child-1",
    childDisplayName = name,
    state = state,
    result = result,
    color = color,
    parentText = parentText,
    claims = claims,
    patternId = patternId,
    timeline = timeline,
    createdAt = "2026-11-07T00:00:00+00:00",
    updatedAt = "2026-11-07T00:00:01+00:00",
    decidedAt = decidedAt,
)

const val SAMPLE_CASE_ID = "11111111-1111-4111-8111-111111111111"

fun sampleChildCase(
    id: String = SAMPLE_CASE_ID,
    state: String = "waiting_push",
    color: String = "open",
    result: String? = null,
    decidedAt: String? = null,
    codeChannel: String? = null,
) = ChildCase(
    id = id,
    childMemberId = "m1",
    state = state,
    result = result,
    color = color,
    codeChannel = codeChannel,
    createdAt = "2026-11-07T00:00:00+00:00",
    updatedAt = "2026-11-07T00:00:01+00:00",
    decidedAt = decidedAt,
)

fun sampleChild(
    id: String = "child-1",
    name: String = "Mina",
    status: String = "invited",
    linked: Boolean = false,
    confirmedAt: String? = null,
    awaitingConfirm: Boolean = false,
    phoneLast4: String? = null,
    pendingPhoneLast4: String? = null,
    callOnly: Boolean = false,
    phoneVerified: Boolean = false,
    inviteExpiresAt: String? = "2026-11-08T00:00:00+00:00",
) = Member(
    id = id,
    role = "child",
    displayName = name,
    status = status,
    linked = linked,
    phoneLast4 = phoneLast4,
    pendingPhoneLast4 = pendingPhoneLast4,
    phoneVerified = phoneVerified,
    awaitingConfirm = awaitingConfirm,
    inviteExpiresAt = inviteExpiresAt,
    callOnly = callOnly,
    confirmedAt = confirmedAt,
)
