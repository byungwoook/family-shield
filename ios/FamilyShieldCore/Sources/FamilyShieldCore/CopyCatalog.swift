import Foundation

// Parent-path copy. English matches the Android string table and
// docs/PRODUCT_REDESIGN.md. Korean matches the Android values-ko table.
// The sign-in notice names Apple on this platform. Do not generate these
// sentences with a model.
public enum CopyKey: String, CaseIterable, Sendable {
    case appName = "app_name"
    case actionRetry = "action_retry"
    case actionCancel = "action_cancel"
    case actionDone = "action_done"
    case actionCopy = "action_copy"
    case actionShare = "action_share"
    case actionConfirm = "action_confirm"
    case actionReject = "action_reject"
    case actionSignOut = "action_sign_out"
    case actionVerify = "action_verify"
    case copied = "copied"
    case loading = "loading"
    case cdRefresh = "cd_refresh"
    case cdBack = "cd_back"
    case cdMore = "cd_more"
    case cdAddChild = "cd_add_child"
    case cdCopy = "cd_copy"
    case cdShare = "cd_share"
    case cdWarning = "cd_warning"
    case cdStatusGreen = "cd_status_green"
    case cdStatusRed = "cd_status_red"
    case cdStatusYellow = "cd_status_yellow"
    case cdStatusOpen = "cd_status_open"
    case cdChild = "cd_child"
    case signinTagline = "signin_tagline"
    case signinPromise = "signin_promise"
    case rootErrorTitle = "root_error_title"
    case createFamilyTitle = "create_family_title"
    case createFamilyBody = "create_family_body"
    case createFamilyNameLabel = "create_family_name_label"
    case createFamilyButton = "create_family_button"
    case membershipPendingTitle = "membership_pending_title"
    case membershipPendingBody = "membership_pending_body"
    case familyTitleFallback = "family_title_fallback"
    case familyChildrenHeading = "family_children_heading"
    case familyEmptyTitle = "family_empty_title"
    case familyEmptyBody = "family_empty_body"
    case familyAddChild = "family_add_child"
    case familyVerifyMessage = "family_verify_message"
    case familyRecentHeading = "family_recent_heading"
    case familyRecentEmpty = "family_recent_empty"
    case childReady = "child_ready"
    case childReadyNoNumber = "child_ready_no_number"
    case childAwaitingConfirm = "child_awaiting_confirm"
    case childInvited = "child_invited"
    case childInviteExpired = "child_invite_expired"
    case childJoinedNoNumber = "child_joined_no_number"
    case childCallOnlyLinkSent = "child_call_only_link_sent"
    case childNotReady = "child_not_ready"
    case childNewInvite = "child_new_invite"
    case childAddByPhone = "child_add_by_phone"
    case joinRequest = "join_request"
    case joinRequestHint = "join_request_hint"
    case phoneChangeRequest = "phone_change_request"
    case phoneChangeHint = "phone_change_hint"
    case noticeChildConfirmed = "notice_child_confirmed"
    case noticeChildRejected = "notice_child_rejected"
    case noticeNumberChanged = "notice_number_changed"
    case noticeNumberChangedCancelled = "notice_number_changed_cancelled"
    case noticeNumberKept = "notice_number_kept"
    case noticeLinkSent = "notice_link_sent"
    case addChildTitle = "add_child_title"
    case addChildNameLabel = "add_child_name_label"
    case addChildModeApp = "add_child_mode_app"
    case addChildModeAppHint = "add_child_mode_app_hint"
    case addChildModePhone = "add_child_mode_phone"
    case addChildModePhoneHint = "add_child_mode_phone_hint"
    case addChildPhoneLabel = "add_child_phone_label"
    case addChildPhoneExample = "add_child_phone_example"
    case addChildSubmit = "add_child_submit"
    case callOnlyTitle = "call_only_title"
    case callOnlySubmit = "call_only_submit"
    case inviteTitle = "invite_title"
    case inviteBody = "invite_body"
    case inviteExpires = "invite_expires"
    case inviteShareText = "invite_share_text"
    case inviteShareTitle = "invite_share_title"
    case inviteClipLabel = "invite_clip_label"
    case newCaseTitle = "new_case_title"
    case newCaseChildHeading = "new_case_child_heading"
    case newCaseNoChildren = "new_case_no_children"
    case newCaseTextLabel = "new_case_text_label"
    case newCaseTextHint = "new_case_text_hint"
    case newCaseExplain = "new_case_explain"
    case newCaseSubmit = "new_case_submit"
    case newCaseCounter = "new_case_counter"
    case newCaseNotSentYet = "new_case_not_sent_yet"
    case caseTitle = "case_title"
    case caseDontSend = "case_dont_send"
    case openWaitingPush = "open_waiting_push"
    case openCalling = "open_calling"
    case openAwaitingAnswer = "open_awaiting_answer"
    case openStarting = "open_starting"
    case caseCheckedAt = "case_checked_at"
    case caseTimelineHeading = "case_timeline_heading"
    case caseYourTextHeading = "case_your_text_heading"
    case caseUpdateFailed = "case_update_failed"
    case claimsHeading = "claims_heading"
    case claimsIdentity = "claims_identity"
    case claimsAmount = "claims_amount"
    case claimsStory = "claims_story"
    case claimsRedFlags = "claims_red_flags"
    case listSeparator = "list_separator"
    case resultTitleGreen = "result_title_green"
    case resultTitleRed = "result_title_red"
    case resultTitleYellow = "result_title_yellow"
    case resultSent = "result_sent"
    case resultNotSent = "result_not_sent"
    case resultNoNumber = "result_no_number"
    case resultCallFailed = "result_call_failed"
    case resultTimeout = "result_timeout"
    case resultWrong = "result_wrong"
    case resultNoAnswer = "result_no_answer"
    case resultUnreachable = "result_unreachable"
    case resultCodeLocked = "result_code_locked"
    case resultNumberRecent = "result_number_recent"
    case resultYellowGeneric = "result_yellow_generic"
    case patternLineGreen = "pattern_line_green"
    case patternLineInfo = "pattern_line_info"
    case patternFakeArrestBail = "pattern_fake_arrest_bail"
    case patternAccident = "pattern_accident"
    case patternGiftCard = "pattern_gift_card"
    case patternCryptoOrWire = "pattern_crypto_or_wire"
    case patternSecrecy = "pattern_secrecy"
    case patternTuitionOrSchool = "pattern_tuition_or_school"
    case patternNewNumber = "pattern_new_number"
    case familyAlertHeading = "family_alert_heading"
    case familyAlertLead = "family_alert_lead"
    case familyAlertMessage = "family_alert_message"
    case familyAlertMessageWithStory = "family_alert_message_with_story"
    case familyAlertShareTitle = "family_alert_share_title"
    case familyAlertClipLabel = "family_alert_clip_label"
    case timelineStart = "timeline_start"
    case timelinePushAnsweredYes = "timeline_push_answered_yes"
    case timelinePushAnsweredNo = "timeline_push_answered_no"
    case timelinePushFailed = "timeline_push_failed"
    case timelinePushWindowElapsed = "timeline_push_window_elapsed"
    case timelineCallFailed = "timeline_call_failed"
    case timelineCallBusy = "timeline_call_busy"
    case timelineCallNoAnswer = "timeline_call_no_answer"
    case timelineCallEndedBeforeCode = "timeline_call_ended_before_code"
    case timelineCallEndedBeforeAnswer = "timeline_call_ended_before_answer"
    case timelineCodeWindowElapsed = "timeline_code_window_elapsed"
    case timelineUseStaticCode = "timeline_use_static_code"
    case timelineCodeAccepted = "timeline_code_accepted"
    case timelineStaticCodeMismatch = "timeline_static_code_mismatch"
    case timelineCodeDidNotMatch = "timeline_code_did_not_match"
    case timelineOneTimeCodeExpired = "timeline_one_time_code_expired"
    case timelineCodeRejected = "timeline_code_rejected"
    case timelineAnswerYes = "timeline_answer_yes"
    case timelineAnswerNo = "timeline_answer_no"
    case timelineAnswerUnclear = "timeline_answer_unclear"
    case timelineAnswerWindowElapsed = "timeline_answer_window_elapsed"
    case timelinePhoneNumberChanged = "timeline_phone_number_changed"
    case timelineUnknown = "timeline_unknown"
    case caseRowOpen = "case_row_open"
    case caseRowGreen = "case_row_green"
    case caseRowRed = "case_row_red"
    case caseRowYellow = "case_row_yellow"
    case errorNetwork = "error_network"
    case errorNotConfigured = "error_not_configured"
    case errorDecode = "error_decode"
    case errorGeneric = "error_generic"
    case errorServer = "error_server"
    case errorUnauthorized = "error_unauthorized"
    case errorInvalidToken = "error_invalid_token"
    case errorSignInUnavailable = "error_sign_in_unavailable"
    case errorInvalidBody = "error_invalid_body"
    case errorNameRequired = "error_name_required"
    case errorNotFound = "error_not_found"
    case errorNotAParent = "error_not_a_parent"
    case errorAlreadyInAFamily = "error_already_in_a_family"
    case errorInviteNotOpen = "error_invite_not_open"
    case errorMemberNotPending = "error_member_not_pending"
    case errorMemberNotReady = "error_member_not_ready"
    case errorNoPendingNumber = "error_no_pending_number"
    case errorPhoneInUse = "error_phone_in_use"
    case errorInvalidPhone = "error_invalid_phone"
    case errorUnsupportedCountry = "error_unsupported_country"
    case errorNotCallOnly = "error_not_call_only"
    case errorSmsUnavailable = "error_sms_unavailable"
    case errorSmsFailed = "error_sms_failed"
    case errorMemberNotCallable = "error_member_not_callable"
    case errorRateLimited = "error_rate_limited"
    case signinApple = "signin_apple"
    case signinPrivacy = "signin_privacy"
    case signinNoMethod = "signin_no_method"
    case errorAppleFailed = "error_apple_failed"
    case childPlaceholderTitle = "child_placeholder_title"
    case childPlaceholderBody = "child_placeholder_body"
}

public enum AppLocale: String, Sendable, Equatable {
    case en, ko
    public static func resolve(_ locale: Locale = .current) -> AppLocale {
        let code = locale.language.languageCode?.identifier
            ?? locale.identifier.split(separator: "_").first.map(String.init)
        return code == "ko" ? .ko : .en
    }
}

public enum CopyCatalog {
    public static func template(_ key: CopyKey, _ locale: AppLocale) -> String {
        table[key]?[locale] ?? table[key]?[.en] ?? key.rawValue
    }

    public static func text(_ key: CopyKey, _ locale: AppLocale, _ args: CustomStringConvertible...) -> String {
        var result = template(key, locale)
        for (index, arg) in args.enumerated() {
            let n = index + 1
            let value = String(describing: arg)
            result = result.replacingOccurrences(of: "%\(n)$s", with: value)
            result = result.replacingOccurrences(of: "%\(n)$d", with: value)
        }
        return result
    }

    static let table: [CopyKey: [AppLocale: String]] = [
        .appName: [
            .en: "Family Shield",
            .ko: "패밀리 쉴드",
        ],
        .actionRetry: [
            .en: "Try again",
            .ko: "다시 시도",
        ],
        .actionCancel: [
            .en: "Cancel",
            .ko: "취소",
        ],
        .actionDone: [
            .en: "Done",
            .ko: "완료",
        ],
        .actionCopy: [
            .en: "Copy",
            .ko: "복사",
        ],
        .actionShare: [
            .en: "Share",
            .ko: "공유",
        ],
        .actionConfirm: [
            .en: "Confirm",
            .ko: "승인",
        ],
        .actionReject: [
            .en: "Reject",
            .ko: "거절",
        ],
        .actionSignOut: [
            .en: "Sign out",
            .ko: "로그아웃",
        ],
        .actionVerify: [
            .en: "Verify",
            .ko: "확인하기",
        ],
        .copied: [
            .en: "Copied",
            .ko: "복사했어요",
        ],
        .loading: [
            .en: "Loading…",
            .ko: "불러오는 중…",
        ],
        .cdRefresh: [
            .en: "Refresh",
            .ko: "새로고침",
        ],
        .cdBack: [
            .en: "Back",
            .ko: "뒤로",
        ],
        .cdMore: [
            .en: "More options",
            .ko: "더보기",
        ],
        .cdAddChild: [
            .en: "Add a child",
            .ko: "자녀 추가",
        ],
        .cdCopy: [
            .en: "Copy",
            .ko: "복사",
        ],
        .cdShare: [
            .en: "Share",
            .ko: "공유",
        ],
        .cdWarning: [
            .en: "Warning",
            .ko: "경고",
        ],
        .cdStatusGreen: [
            .en: "Confirmed",
            .ko: "확인됨",
        ],
        .cdStatusRed: [
            .en: "Scam",
            .ko: "사기",
        ],
        .cdStatusYellow: [
            .en: "Not confirmed",
            .ko: "확인 안 됨",
        ],
        .cdStatusOpen: [
            .en: "Checking",
            .ko: "확인 중",
        ],
        .cdChild: [
            .en: "Child",
            .ko: "자녀",
        ],
        .signinTagline: [
            .en: "Before you send money, check with your child that the request really came from them.",
            .ko: "돈을 보내기 전에, 그 요청이 정말 자녀에게서 온 것인지 자녀에게 직접 확인하세요.",
        ],
        .signinPromise: [
            .en: "Family Shield never tells you to send money. Only your child's own answer turns a check green or red.",
            .ko: "패밀리 쉴드는 절대 돈을 보내라고 하지 않아요. 자녀 본인의 답변만이 확인 결과를 초록색이나 빨간색으로 바꿀 수 있어요.",
        ],
        .rootErrorTitle: [
            .en: "Couldn't load your account",
            .ko: "계정 정보를 불러오지 못했어요",
        ],
        .createFamilyTitle: [
            .en: "Create your family",
            .ko: "가족 만들기",
        ],
        .createFamilyBody: [
            .en: "You'll add your children next. Each child joins with a one-time invite code, or by a text link if they won't install the app.",
            .ko: "다음 단계에서 자녀를 추가해요. 자녀는 한 번만 쓸 수 있는 초대 코드로 가입하거나, 앱을 설치하지 않는다면 문자로 받은 링크로 등록할 수 있어요.",
        ],
        .createFamilyNameLabel: [
            .en: "Family name",
            .ko: "가족 이름",
        ],
        .createFamilyButton: [
            .en: "Create family",
            .ko: "가족 만들기",
        ],
        .membershipPendingTitle: [
            .en: "Your family membership isn't active yet",
            .ko: "아직 가족 가입이 완료되지 않았어요",
        ],
        .membershipPendingBody: [
            .en: "Ask the parent who created the family to check the Family Shield app.",
            .ko: "가족을 만든 보호자에게 패밀리 쉴드 앱을 확인해 달라고 요청하세요.",
        ],
        .familyTitleFallback: [
            .en: "Your family",
            .ko: "우리 가족",
        ],
        .familyChildrenHeading: [
            .en: "Children",
            .ko: "자녀",
        ],
        .familyEmptyTitle: [
            .en: "No children yet",
            .ko: "아직 자녀가 없어요",
        ],
        .familyEmptyBody: [
            .en: "Add a child to start. They join with a one-time invite code, or by a text link if they won't install the app.",
            .ko: "자녀를 추가해서 시작하세요. 자녀는 한 번만 쓸 수 있는 초대 코드로 가입하거나, 앱을 설치하지 않는다면 문자로 받은 링크로 등록할 수 있어요.",
        ],
        .familyAddChild: [
            .en: "Add a child",
            .ko: "자녀 추가",
        ],
        .familyVerifyMessage: [
            .en: "Verify a message",
            .ko: "메시지 확인하기",
        ],
        .familyRecentHeading: [
            .en: "Recent checks",
            .ko: "최근 확인",
        ],
        .familyRecentEmpty: [
            .en: "No checks yet.",
            .ko: "아직 확인한 메시지가 없어요.",
        ],
        .childReady: [
            .en: "Number ending %2$s · Ready to verify",
            .ko: "번호 끝자리 %2$s · 확인할 수 있어요",
        ],
        .childReadyNoNumber: [
            .en: "Ready to verify",
            .ko: "확인할 수 있어요",
        ],
        .childAwaitingConfirm: [
            .en: "Can't verify yet: confirm %1$s first.",
            .ko: "아직 확인할 수 없어요: 먼저 %1$s의 가입을 승인해 주세요.",
        ],
        .childInvited: [
            .en: "Can't verify yet: %1$s hasn't joined. Their invite code works until %2$s.",
            .ko: "아직 확인할 수 없어요: %1$s 본인이 아직 가입하지 않았어요. 초대 코드는 %2$s까지 쓸 수 있어요.",
        ],
        .childInviteExpired: [
            .en: "Can't verify yet: %1$s hasn't joined, and the invite code expired.",
            .ko: "아직 확인할 수 없어요: %1$s 본인이 가입하지 않았고, 초대 코드가 만료됐어요.",
        ],
        .childJoinedNoNumber: [
            .en: "Can't verify yet: %1$s joined but hasn't verified a phone number.",
            .ko: "아직 확인할 수 없어요: %1$s 본인이 가입했지만 아직 전화번호를 인증하지 않았어요.",
        ],
        .childCallOnlyLinkSent: [
            .en: "Can't verify yet: we texted a link to the number ending %2$s. %1$s needs to tap Allow and choose a check code.",
            .ko: "아직 확인할 수 없어요: 끝자리가 %2$s인 번호로 링크를 보냈어요. %1$s 본인이 '허용'을 누르고 확인 번호를 정해야 해요.",
        ],
        .childNotReady: [
            .en: "Can't verify yet: %1$s isn't set up.",
            .ko: "아직 확인할 수 없어요: %1$s 본인의 설정이 끝나지 않았어요.",
        ],
        .childNewInvite: [
            .en: "New invite code",
            .ko: "새 초대 코드",
        ],
        .childAddByPhone: [
            .en: "Add by phone number (no app)",
            .ko: "전화번호로 추가 (앱 없이)",
        ],
        .joinRequest: [
            .en: "%1$s wants to join. Number ending %2$s.",
            .ko: "%1$s의 가입 요청이 왔어요. 번호 끝자리: %2$s.",
        ],
        .joinRequestHint: [
            .en: "Confirm only if you recognize this number. If you don't, reject it.",
            .ko: "아는 번호일 때만 승인하세요. 모르는 번호라면 거절하세요.",
        ],
        .phoneChangeRequest: [
            .en: "%1$s wants to change their number to one ending %2$s.",
            .ko: "%1$s 본인이 번호를 끝자리 %2$s인 번호로 바꾸려고 해요.",
        ],
        .phoneChangeHint: [
            .en: "Calls go to the new number only after you confirm. Confirming ends any check for %1$s that is still open.",
            .ko: "승인해야만 새 번호로 전화를 걸어요. 승인하면 %1$s에 대해 진행 중인 확인은 모두 끝나요.",
        ],
        .noticeChildConfirmed: [
            .en: "%1$s can now be verified.",
            .ko: "이제 %1$s 본인에게 확인할 수 있어요.",
        ],
        .noticeChildRejected: [
            .en: "%1$s's request was rejected.",
            .ko: "%1$s의 가입 요청을 거절했어요.",
        ],
        .noticeNumberChanged: [
            .en: "%1$s's number now ends %2$s.",
            .ko: "%1$s의 번호가 끝자리 %2$s인 번호로 바뀌었어요.",
        ],
        .noticeNumberChangedCancelled: [
            .en: "%1$s's number now ends %2$s. Checks that were still open for %1$s were stopped.",
            .ko: "%1$s의 번호가 끝자리 %2$s인 번호로 바뀌었어요. %1$s에 대해 진행 중이던 확인은 중단됐어요.",
        ],
        .noticeNumberKept: [
            .en: "%1$s's number stays the same.",
            .ko: "%1$s의 번호는 그대로 유지돼요.",
        ],
        .noticeLinkSent: [
            .en: "We texted a link to the number ending %2$s. %1$s needs to tap Allow and choose a 4-digit check code.",
            .ko: "끝자리가 %2$s인 번호로 링크를 보냈어요. %1$s 본인이 '허용'을 누르고 네 자리 확인 번호를 정해야 해요.",
        ],
        .addChildTitle: [
            .en: "Add a child",
            .ko: "자녀 추가",
        ],
        .addChildNameLabel: [
            .en: "Child's name",
            .ko: "자녀 이름",
        ],
        .addChildModeApp: [
            .en: "They'll use the Family Shield app",
            .ko: "패밀리 쉴드 앱을 사용해요",
        ],
        .addChildModeAppHint: [
            .en: "You'll get a one-time invite code to send them.",
            .ko: "자녀에게 보낼 일회용 초대 코드를 받아요.",
        ],
        .addChildModePhone: [
            .en: "Add by phone number (no app)",
            .ko: "전화번호로 추가 (앱 없이)",
        ],
        .addChildModePhoneHint: [
            .en: "We text them a link. They tap Allow and choose a 4-digit check code; you never see it. Only +1 (US, Canada) and +82 (Korea) numbers.",
            .ko: "자녀에게 문자로 링크를 보내요. 자녀가 '허용'을 누르고 네 자리 확인 번호를 정해요. 보호자는 그 번호를 볼 수 없어요. +1(미국, 캐나다)과 +82(한국) 번호만 쓸 수 있어요.",
        ],
        .addChildPhoneLabel: [
            .en: "Their mobile number, with country code",
            .ko: "자녀 휴대폰 번호 (국가 번호 포함)",
        ],
        .addChildPhoneExample: [
            .en: "e.g. +1 555 123 4567 or +82 10 1234 5678",
            .ko: "예: +82 10 1234 5678 또는 +1 555 123 4567",
        ],
        .addChildSubmit: [
            .en: "Add",
            .ko: "추가",
        ],
        .callOnlyTitle: [
            .en: "Add %1$s by phone number",
            .ko: "전화번호로 %1$s 추가하기",
        ],
        .callOnlySubmit: [
            .en: "Send the link",
            .ko: "링크 보내기",
        ],
        .inviteTitle: [
            .en: "Invite code for %1$s",
            .ko: "%1$s의 초대 코드",
        ],
        .inviteBody: [
            .en: "Send this code to %1$s over a chat you already trust, like a KakaoTalk or iMessage thread you've used before. It works once, for 24 hours. We show it only now.",
            .ko: "이 코드를 이미 믿고 쓰는 대화방(예: 전에 쓰던 카카오톡이나 iMessage 대화)으로 %1$s에게 보내세요. 이 코드는 24시간 동안 한 번만 쓸 수 있어요. 코드는 지금 한 번만 보여 드려요.",
        ],
        .inviteExpires: [
            .en: "Works until %1$s.",
            .ko: "%1$s까지 쓸 수 있어요.",
        ],
        .inviteShareText: [
            .en: "Your Family Shield invite code: %1$s\nInstall Family Shield, sign in, and enter this code. It works once, within 24 hours.",
            .ko: "패밀리 쉴드 초대 코드: %1$s\n패밀리 쉴드를 설치하고 로그인한 뒤 이 코드를 입력하세요. 24시간 안에 한 번만 쓸 수 있어요.",
        ],
        .inviteShareTitle: [
            .en: "Send the invite code",
            .ko: "초대 코드 보내기",
        ],
        .inviteClipLabel: [
            .en: "Family Shield invite code",
            .ko: "패밀리 쉴드 초대 코드",
        ],
        .newCaseTitle: [
            .en: "Verify a message",
            .ko: "메시지 확인하기",
        ],
        .newCaseChildHeading: [
            .en: "Who does the message say it's from?",
            .ko: "누가 보낸 메시지라고 하나요?",
        ],
        .newCaseNoChildren: [
            .en: "No child can be verified yet. A child needs to join, verify their number, and be confirmed by you first.",
            .ko: "아직 확인할 수 있는 자녀가 없어요. 자녀가 가입하고 번호를 인증한 뒤, 보호자가 승인해야 해요.",
        ],
        .newCaseTextLabel: [
            .en: "The message (optional)",
            .ko: "받은 메시지 (선택)",
        ],
        .newCaseTextHint: [
            .en: "Paste the message you got, if you like. It is used only to point out known scam patterns, and it is deleted 30 days after the check.",
            .ko: "받은 메시지를 원하면 붙여 넣으세요. 알려진 사기 수법을 알려 드리는 데만 쓰고, 확인이 끝나고 30일 뒤에 삭제해요.",
        ],
        .newCaseExplain: [
            .en: "We ask your child in the Family Shield app first, then call the number they verified. Only their answer decides the result. Don't send money while we check.",
            .ko: "먼저 패밀리 쉴드 앱으로 자녀에게 묻고, 답이 없으면 자녀가 인증한 번호로 전화해요. 결과는 자녀 본인의 답변으로만 정해져요. 확인하는 동안 돈을 보내지 마세요.",
        ],
        .newCaseSubmit: [
            .en: "Verify",
            .ko: "확인하기",
        ],
        .newCaseCounter: [
            .en: "%1$d / %2$d",
            .ko: "%1$d / %2$d",
        ],
        .newCaseNotSentYet: [
            .en: "Nothing is sent until you tap Verify.",
            .ko: "확인하기를 누르기 전에는 아무것도 전송되지 않아요.",
        ],
        .caseTitle: [
            .en: "Check for %1$s",
            .ko: "%1$s 확인",
        ],
        .caseDontSend: [
            .en: "Don't send money yet.",
            .ko: "아직 돈을 보내지 마세요.",
        ],
        .openWaitingPush: [
            .en: "We asked %1$s to confirm in the Family Shield app. If there's no answer in 90 seconds, we'll call the number they verified.",
            .ko: "패밀리 쉴드 앱으로 %1$s에게 확인을 요청했어요. 90초 안에 답이 없으면 인증된 번호로 전화할게요.",
        ],
        .openCalling: [
            .en: "We're calling %1$s on the number they verified. They enter a code on the keypad, then tell us whether they sent the message.",
            .ko: "인증된 번호로 %1$s에게 전화하고 있어요. 키패드로 번호를 입력한 뒤, 메시지를 보냈는지 답하게 돼요.",
        ],
        .openAwaitingAnswer: [
            .en: "%1$s entered the right code. Waiting for their answer.",
            .ko: "%1$s 본인이 맞는 번호를 입력했어요. 답변을 기다리고 있어요.",
        ],
        .openStarting: [
            .en: "Starting the check with %1$s…",
            .ko: "%1$s에게 확인을 시작하고 있어요…",
        ],
        .caseCheckedAt: [
            .en: "Checked at %1$s",
            .ko: "%1$s에 확인",
        ],
        .caseTimelineHeading: [
            .en: "What happened",
            .ko: "진행 내역",
        ],
        .caseYourTextHeading: [
            .en: "The message you checked",
            .ko: "확인한 메시지",
        ],
        .caseUpdateFailed: [
            .en: "Can't update right now. We'll keep trying.",
            .ko: "지금은 업데이트할 수 없어요. 계속 다시 시도할게요.",
        ],
        .claimsHeading: [
            .en: "What the voice note claims (this does NOT prove who it is)",
            .ko: "음성 메시지의 주장 (이것으로 누구인지 증명되지 않아요)",
        ],
        .claimsIdentity: [
            .en: "Says it's: %1$s",
            .ko: "자신이 누구라고 하나요: %1$s",
        ],
        .claimsAmount: [
            .en: "Asks for: %1$s",
            .ko: "요구 금액: %1$s",
        ],
        .claimsStory: [
            .en: "Story: %1$s",
            .ko: "내용: %1$s",
        ],
        .claimsRedFlags: [
            .en: "Red flags: %1$s",
            .ko: "의심스러운 점: %1$s",
        ],
        .listSeparator: [
            .en: "; ",
            .ko: "; ",
        ],
        .resultTitleGreen: [
            .en: "Confirmed",
            .ko: "확인됨",
        ],
        .resultTitleRed: [
            .en: "Scam",
            .ko: "사기",
        ],
        .resultTitleYellow: [
            .en: "Not confirmed",
            .ko: "확인 안 됨",
        ],
        .resultSent: [
            .en: "%1$s confirmed they sent it. The request really came from %1$s. Talk to %1$s directly before sending anything.",
            .ko: "%1$s 본인이 보냈다고 확인했어요. 이 요청은 실제로 %1$s에게서 온 거예요. 무엇이든 보내기 전에 %1$s에게 직접 연락해서 이야기해 보세요.",
        ],
        .resultNotSent: [
            .en: "%1$s confirmed they did not send this. Do not send money and do not reply to whoever contacted you.",
            .ko: "%1$s 본인이 이 메시지를 보내지 않았다고 확인했어요. 돈을 보내지 말고, 연락해 온 사람에게 답장하지 마세요.",
        ],
        .resultNoNumber: [
            .en: "There is no verified number for %1$s, so no call was made. Don't send money. Call your child on the number you already know.",
            .ko: "%1$s의 인증된 번호가 없어서 전화를 걸지 않았어요. 돈을 보내지 마세요. 이미 알고 있는 번호로 자녀에게 직접 전화해 보세요.",
        ],
        .resultCallFailed: [
            .en: "We couldn't reach %1$s. Don't send money. Try calling them on the number you already know.",
            .ko: "%1$s에게 연락이 닿지 않았어요. 돈을 보내지 마세요. 이미 알고 있는 번호로 직접 전화해 보세요.",
        ],
        .resultTimeout: [
            .en: "%1$s hasn't entered the check code yet. They may just be busy. Don't send money until you reach them yourself.",
            .ko: "%1$s 본인이 아직 확인 번호를 입력하지 않았어요. 바빠서 그럴 수도 있어요. 직접 연락이 닿기 전까지는 돈을 보내지 마세요.",
        ],
        .resultWrong: [
            .en: "The check code entered at %2$s was wrong. Don't send money. Call your child on the number you already know.",
            .ko: "%2$s에 입력된 확인 번호가 틀렸어요. 돈을 보내지 마세요. 이미 알고 있는 번호로 자녀에게 직접 전화해 보세요.",
        ],
        .resultNoAnswer: [
            .en: "%1$s entered the check code but didn't say whether they sent that message. Don't send money until you talk to %1$s directly.",
            .ko: "%1$s 본인이 확인 번호는 입력했지만, 그 메시지를 보냈는지는 답하지 않았어요. %1$s에게 직접 확인하기 전까지는 돈을 보내지 마세요.",
        ],
        .resultUnreachable: [
            .en: "We couldn't reach %1$s: the Family Shield app on their phone can't get our request, and there is no verified number to call. Don't send money. Call your child on the number you already know.",
            .ko: "%1$s에게 연락할 수 없었어요. 휴대폰의 패밀리 쉴드 앱으로 요청을 보낼 수 없고, 전화할 인증된 번호도 없어요. 돈을 보내지 마세요. 이미 알고 있는 번호로 자녀에게 직접 전화해 보세요.",
        ],
        .resultCodeLocked: [
            .en: "We couldn't check %1$s's code. Don't send money. They can set a new check code in the app.",
            .ko: "%1$s의 확인 번호를 확인할 수 없었어요. 돈을 보내지 마세요. 자녀가 앱에서 새 확인 번호를 설정할 수 있어요.",
        ],
        .resultNumberRecent: [
            .en: "%1$s said yes on a call to a number that was registered or changed in the last 24 hours. That is not confirmed. Don't send money. Talk to %1$s on the number you already knew, or wait and check again from the app.",
            .ko: "%1$s 본인이 최근 24시간 안에 등록되거나 바뀐 번호로 건 전화에서 '네'라고 답했어요. 이것은 확인된 것이 아니에요. 돈을 보내지 마세요. 원래 알던 번호로 %1$s에게 연락하거나, 잠시 기다렸다가 앱에서 다시 확인해 보세요.",
        ],
        .resultYellowGeneric: [
            .en: "We couldn't confirm it was %1$s. Don't send money. Call them on a number you already know.",
            .ko: "%1$s 본인인지 확인하지 못했어요. 돈을 보내지 마세요. 이미 알고 있는 번호로 직접 전화해 보세요.",
        ],
        .patternLineGreen: [
            .en: "This message looked like a known pattern (%1$s), but %2$s confirmed they sent it. Avoid gift cards, crypto, and wire transfers; they are hard to reverse.",
            .ko: "이 메시지는 알려진 수법(%1$s)과 비슷했지만, %2$s 본인이 보냈다고 확인했어요. 기프트카드, 암호화폐, 전신송금은 되돌리기 어려우니 피하세요.",
        ],
        .patternLineInfo: [
            .en: "This message looks like a known scam pattern: %1$s. That alone decides nothing; only %2$s's own answer does.",
            .ko: "이 메시지는 알려진 사기 수법과 비슷해요: %1$s. 이것만으로는 아무것도 정해지지 않아요. 결과는 %2$s 본인의 답변으로만 정해져요.",
        ],
        .patternFakeArrestBail: [
            .en: "a fake arrest and bail demand",
            .ko: "체포·보석금을 핑계로 한 송금 요구",
        ],
        .patternAccident: [
            .en: "an accident or injury emergency",
            .ko: "사고·부상을 핑계로 한 급한 송금 요구",
        ],
        .patternGiftCard: [
            .en: "payment in gift cards",
            .ko: "기프트카드로 보내라는 요구",
        ],
        .patternCryptoOrWire: [
            .en: "crypto or wire transfer",
            .ko: "암호화폐·전신송금 요구",
        ],
        .patternSecrecy: [
            .en: "a request to keep it secret",
            .ko: "다른 가족에게 알리지 말라는 요구",
        ],
        .patternTuitionOrSchool: [
            .en: "a tuition or school fee",
            .ko: "등록금·학교 비용 요구",
        ],
        .patternNewNumber: [
            .en: "a 'new phone number' story",
            .ko: "번호가 바뀌었다는 이야기",
        ],
        .familyAlertHeading: [
            .en: "Warn your family",
            .ko: "가족에게 알리세요",
        ],
        .familyAlertLead: [
            .en: "Scammers who copy one person's voice often try other relatives next. Copy this into your family group chat:",
            .ko: "한 사람의 목소리를 흉내 낸 사기범은 다음으로 다른 가족에게 연락하는 경우가 많아요. 아래 내용을 가족 단체 대화방에 붙여 넣으세요.",
        ],
        .familyAlertMessage: [
            .en: "⚠️ Family alert: someone is pretending to be %1$s, possibly with an AI copy of their voice, to ask for money. %1$s confirmed it wasn't them. If you get a call, voice note or text from \"%1$s\" asking for money, don't pay. Hang up and call %1$s on their saved number. Never pay by gift cards, crypto or wire transfer.",
            .ko: "⚠️ 가족 알림: 누군가 %1$s인 척하며 돈을 요구하고 있어요. AI로 목소리를 흉내 냈을 수도 있어요. %1$s 본인은 보내지 않았다고 확인했어요. %1$s의 이름으로 돈을 요구하는 전화, 음성 메시지, 문자를 받으면 돈을 보내지 마세요. 전화를 끊고 저장된 번호로 %1$s에게 직접 전화하세요. 기프트카드, 암호화폐, 전신송금으로는 절대 보내지 마세요.",
        ],
        .familyAlertMessageWithStory: [
            .en: "⚠️ Family alert: someone is pretending to be %1$s, possibly with an AI copy of their voice, to ask for money. %1$s confirmed it wasn't them. The story used: \"%2$s\". If you get a call, voice note or text from \"%1$s\" asking for money, don't pay. Hang up and call %1$s on their saved number. Never pay by gift cards, crypto or wire transfer.",
            .ko: "⚠️ 가족 알림: 누군가 %1$s인 척하며 돈을 요구하고 있어요. AI로 목소리를 흉내 냈을 수도 있어요. %1$s 본인은 보내지 않았다고 확인했어요. 사용된 수법: \"%2$s\". %1$s의 이름으로 돈을 요구하는 전화, 음성 메시지, 문자를 받으면 돈을 보내지 마세요. 전화를 끊고 저장된 번호로 %1$s에게 직접 전화하세요. 기프트카드, 암호화폐, 전신송금으로는 절대 보내지 마세요.",
        ],
        .familyAlertShareTitle: [
            .en: "Share the warning",
            .ko: "경고 공유하기",
        ],
        .familyAlertClipLabel: [
            .en: "Family Shield warning",
            .ko: "패밀리 쉴드 경고",
        ],
        .timelineStart: [
            .en: "Check started",
            .ko: "확인 시작",
        ],
        .timelinePushAnsweredYes: [
            .en: "Answered Yes in the app",
            .ko: "앱에서 '네'라고 답함",
        ],
        .timelinePushAnsweredNo: [
            .en: "Answered No in the app",
            .ko: "앱에서 '아니요'라고 답함",
        ],
        .timelinePushFailed: [
            .en: "The app on their phone couldn't get the request",
            .ko: "자녀 휴대폰의 앱이 요청을 받지 못함",
        ],
        .timelinePushWindowElapsed: [
            .en: "No answer in the app within 90 seconds",
            .ko: "90초 안에 앱에서 답이 없음",
        ],
        .timelineCallFailed: [
            .en: "The call couldn't be placed",
            .ko: "전화를 걸지 못함",
        ],
        .timelineCallBusy: [
            .en: "The line was busy",
            .ko: "통화 중이었음",
        ],
        .timelineCallNoAnswer: [
            .en: "Nobody picked up",
            .ko: "전화를 받지 않음",
        ],
        .timelineCallEndedBeforeCode: [
            .en: "The call ended before a code was entered",
            .ko: "번호를 입력하기 전에 통화가 끝남",
        ],
        .timelineCallEndedBeforeAnswer: [
            .en: "The call ended before 1 or 2 was pressed",
            .ko: "1이나 2를 누르기 전에 통화가 끝남",
        ],
        .timelineCodeWindowElapsed: [
            .en: "No code within 3 minutes",
            .ko: "3분 안에 번호를 입력하지 않음",
        ],
        .timelineUseStaticCode: [
            .en: "Switched to the 4-digit check code",
            .ko: "네 자리 확인 번호로 전환함",
        ],
        .timelineCodeAccepted: [
            .en: "The right code was entered",
            .ko: "맞는 번호를 입력함",
        ],
        .timelineStaticCodeMismatch: [
            .en: "Wrong check code",
            .ko: "확인 번호가 틀림",
        ],
        .timelineCodeDidNotMatch: [
            .en: "Wrong one-time code",
            .ko: "일회용 번호가 틀림",
        ],
        .timelineOneTimeCodeExpired: [
            .en: "The one-time code had expired",
            .ko: "일회용 번호가 만료됨",
        ],
        .timelineCodeRejected: [
            .en: "Code refused: the check code is locked",
            .ko: "번호 거부됨: 확인 번호가 잠김",
        ],
        .timelineAnswerYes: [
            .en: "Pressed 1: yes, they sent it",
            .ko: "1을 누름: 보낸 게 맞음",
        ],
        .timelineAnswerNo: [
            .en: "Pressed 2: no, they didn't send it",
            .ko: "2를 누름: 보내지 않음",
        ],
        .timelineAnswerUnclear: [
            .en: "Didn't press 1 or 2",
            .ko: "1이나 2를 누르지 않음",
        ],
        .timelineAnswerWindowElapsed: [
            .en: "No answer within 45 seconds",
            .ko: "45초 안에 답이 없음",
        ],
        .timelinePhoneNumberChanged: [
            .en: "Stopped because the phone number changed",
            .ko: "전화번호가 바뀌어서 중단됨",
        ],
        .timelineUnknown: [
            .en: "Status updated",
            .ko: "상태가 바뀜",
        ],
        .caseRowOpen: [
            .en: "Checking…",
            .ko: "확인 중…",
        ],
        .caseRowGreen: [
            .en: "Confirmed",
            .ko: "확인됨",
        ],
        .caseRowRed: [
            .en: "Scam",
            .ko: "사기",
        ],
        .caseRowYellow: [
            .en: "Not confirmed",
            .ko: "확인 안 됨",
        ],
        .errorNetwork: [
            .en: "Can't reach Family Shield. Check your connection and try again.",
            .ko: "패밀리 쉴드에 연결할 수 없어요. 인터넷 연결을 확인하고 다시 시도해 주세요.",
        ],
        .errorNotConfigured: [
            .en: "This build has no server address.",
            .ko: "이 빌드에는 서버 주소가 없어요.",
        ],
        .errorDecode: [
            .en: "The server sent something this version of the app doesn't understand. Please update the app.",
            .ko: "이 버전의 앱이 이해할 수 없는 응답을 받았어요. 앱을 업데이트해 주세요.",
        ],
        .errorGeneric: [
            .en: "Something went wrong. Please try again.",
            .ko: "문제가 생겼어요. 다시 시도해 주세요.",
        ],
        .errorServer: [
            .en: "Family Shield is having trouble. Please try again in a moment.",
            .ko: "패밀리 쉴드 서버에 문제가 있어요. 잠시 후 다시 시도해 주세요.",
        ],
        .errorUnauthorized: [
            .en: "Please sign in again.",
            .ko: "다시 로그인해 주세요.",
        ],
        .errorInvalidToken: [
            .en: "Sign-in didn't work. Please try again.",
            .ko: "로그인하지 못했어요. 다시 시도해 주세요.",
        ],
        .errorSignInUnavailable: [
            .en: "Google sign-in isn't set up on this server.",
            .ko: "이 서버에는 Google 로그인이 설정되어 있지 않아요.",
        ],
        .errorInvalidBody: [
            .en: "Something in the form isn't right. Check it and try again.",
            .ko: "입력한 내용에 문제가 있어요. 확인하고 다시 시도해 주세요.",
        ],
        .errorNameRequired: [
            .en: "Enter a name.",
            .ko: "이름을 입력하세요.",
        ],
        .errorNotFound: [
            .en: "We couldn't find that. It may have been removed.",
            .ko: "찾을 수 없어요. 삭제되었을 수 있어요.",
        ],
        .errorNotAParent: [
            .en: "This account belongs to a child, so it can't do that.",
            .ko: "자녀 계정이라서 이 작업을 할 수 없어요.",
        ],
        .errorAlreadyInAFamily: [
            .en: "This account is already in a family.",
            .ko: "이 계정은 이미 가족에 속해 있어요.",
        ],
        .errorInviteNotOpen: [
            .en: "This child already joined, so a new invite code isn't needed.",
            .ko: "이 자녀는 이미 가입해서 새 초대 코드가 필요 없어요.",
        ],
        .errorMemberNotPending: [
            .en: "This request was already handled.",
            .ko: "이미 처리된 요청이에요.",
        ],
        .errorMemberNotReady: [
            .en: "This child hasn't verified a number yet, so they can't be confirmed.",
            .ko: "이 자녀는 아직 번호를 인증하지 않아서 승인할 수 없어요.",
        ],
        .errorNoPendingNumber: [
            .en: "There's no number change waiting.",
            .ko: "기다리는 번호 변경 요청이 없어요.",
        ],
        .errorPhoneInUse: [
            .en: "That number is already used by someone in Family Shield.",
            .ko: "이 번호는 이미 패밀리 쉴드에서 다른 사람이 쓰고 있어요.",
        ],
        .errorInvalidPhone: [
            .en: "That doesn't look like a mobile number. Include the country code, for example +1 555 123 4567 or +82 10 1234 5678.",
            .ko: "휴대폰 번호 형식이 아니에요. +82 10 1234 5678 또는 +1 555 123 4567처럼 국가 번호를 포함해 주세요.",
        ],
        .errorUnsupportedCountry: [
            .en: "Only US and Canada (+1) and Korean (+82) numbers can be added for now.",
            .ko: "지금은 미국·캐나다(+1)와 한국(+82) 번호만 추가할 수 있어요.",
        ],
        .errorNotCallOnly: [
            .en: "This child can't be added by phone number: they already have the app or a number.",
            .ko: "이 자녀는 이미 앱을 쓰고 있거나 번호가 있어서 전화번호로 추가할 수 없어요.",
        ],
        .errorSmsUnavailable: [
            .en: "Text messages aren't available on this server right now, so no link was sent.",
            .ko: "지금 이 서버에서는 문자를 보낼 수 없어서 링크를 보내지 못했어요.",
        ],
        .errorSmsFailed: [
            .en: "The number was saved, but the text didn't go through. Please try again later.",
            .ko: "번호는 저장됐지만 문자가 전송되지 않았어요. 잠시 후 다시 시도해 주세요.",
        ],
        .errorMemberNotCallable: [
            .en: "This child can't be checked right now. They need to be confirmed by you and have a verified number or the app.",
            .ko: "지금은 이 자녀에게 확인할 수 없어요. 보호자의 승인과 함께 인증된 번호나 앱이 있어야 해요.",
        ],
        .errorRateLimited: [
            .en: "You've reached the limit for now: 5 checks per child and 10 in total in 24 hours. Don't send money; call your child on the number you already know.",
            .ko: "지금은 확인 횟수 한도에 도달했어요. 24시간 동안 자녀당 5번, 전체 10번까지 확인할 수 있어요. 돈을 보내지 말고, 이미 알고 있는 번호로 자녀에게 전화해 보세요.",
        ],
        .signinApple: [
            .en: "Sign in with Apple",
            .ko: "Apple로 로그인",
        ],
        .signinPrivacy: [
            .en: "Pilot notice: Family Shield, Cartesia (voice-note transcription), Twilio (calls and text codes), Anthropic (reading the message for patterns), and Apple (sign-in and notifications) process what a check needs. We do not build a voiceprint.",
            .ko: "시범 안내: 패밀리 쉴드, Cartesia(음성 메모 받아쓰기), Twilio(전화와 문자 인증), Anthropic(메시지에서 패턴 읽기), Apple(로그인과 알림)이 확인에 필요한 내용을 처리합니다. 목소리 지문은 만들지 않습니다.",
        ],
        .signinNoMethod: [
            .en: "This build has no way to sign in. It needs the Sign in with Apple capability.",
            .ko: "이 빌드에는 로그인 방법이 없어요. Apple로 로그인 기능이 필요해요.",
        ],
        .errorAppleFailed: [
            .en: "Apple sign-in didn't finish. Please try again.",
            .ko: "Apple 로그인이 완료되지 않았어요. 다시 시도해 주세요.",
        ],
        .childPlaceholderTitle: [
            .en: "This account is a child",
            .ko: "이 계정은 자녀예요",
        ],
        .childPlaceholderBody: [
            .en: "The child screens are not in this version of the iOS app yet. Sign out, and use the invite on the child update when it is installed.",
            .ko: "이 iOS 버전에는 아직 자녀 화면이 없어요. 로그아웃한 뒤, 자녀 화면이 들어간 버전에서 초대 코드를 사용하세요.",
        ],
    ]
}
