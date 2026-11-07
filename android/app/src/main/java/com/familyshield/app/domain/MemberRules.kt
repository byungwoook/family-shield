package com.familyshield.app.domain

import com.familyshield.app.data.api.Member
import java.time.Instant

/** Where a child is in enrollment, read from one roster row (contract §5 members, §7 flows). */
enum class ChildStage {
    /** Active and confirmed by a parent: Verify is allowed. */
    READY,
    /** Accepted the invite and verified a number: the parent must confirm or reject. */
    AWAITING_CONFIRM,
    /** Invite code outstanding and still valid. */
    INVITED,
    /** Invite code past its 24 hours (the server does not clear the time). */
    INVITE_EXPIRED,
    /** Accepted the invite but has not verified a number yet. */
    JOINED_NO_NUMBER,
    /** No-app child: the text link was sent, waiting for them to tap Allow. */
    CALL_ONLY_LINK_SENT,
    /** Anything else that is not callable yet. */
    NOT_READY,
}

object MemberRules {

    fun isChild(member: Member): Boolean = member.role == "child"

    /**
     * The contract's UI rule: enable Verify only for `role=child`,
     * `status=active`, and `confirmed_at` set. The server is still the final
     * judge (`400 member_not_callable`).
     */
    fun canVerify(member: Member): Boolean =
        isChild(member) && member.status == "active" && member.confirmedAt != null

    fun stage(member: Member, now: Instant = Instant.now()): ChildStage = when {
        canVerify(member) -> ChildStage.READY
        member.awaitingConfirm -> ChildStage.AWAITING_CONFIRM
        member.callOnly && member.status == "invited" -> ChildStage.CALL_ONLY_LINK_SENT
        member.status == "invited" && member.linked && !member.phoneVerified -> ChildStage.JOINED_NO_NUMBER
        member.status == "invited" && !member.linked -> {
            val expires = Times.parse(member.inviteExpiresAt)
            if (expires != null && !expires.isAfter(now)) ChildStage.INVITE_EXPIRED else ChildStage.INVITED
        }
        else -> ChildStage.NOT_READY
    }

    /** A new invite code makes sense only before a child account accepted one, and never for a no-app child. */
    fun canReissueInvite(member: Member): Boolean =
        isChild(member) && member.status == "invited" && !member.linked && !member.callOnly

    /** "Add by phone number (no app)": an invited child with no account and no number yet. */
    fun canAddCallOnly(member: Member): Boolean =
        isChild(member) && member.status == "invited" && !member.linked && member.phoneLast4 == null

    /** A child number change waiting for a parent (shown with Confirm / Reject). */
    fun hasPendingNumber(member: Member): Boolean = isChild(member) && member.pendingPhoneLast4 != null
}
