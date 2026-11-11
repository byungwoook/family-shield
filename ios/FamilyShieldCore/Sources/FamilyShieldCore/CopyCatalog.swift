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
    case newCaseAudioAttached = "new_case_audio_attached"
    case newCaseAudioRemove = "new_case_audio_remove"
    case shareAudioTooLarge = "share_audio_too_large"
    case shareAudioEmpty = "share_audio_empty"
    case shareAudioUnsupported = "share_audio_unsupported"
    case shareAudioUnreadable = "share_audio_unreadable"
    case shareWaitingSignin = "share_waiting_signin"
    case shareWaitingFamily = "share_waiting_family"
    case shareNeedsParent = "share_needs_parent"
    case shareDiscard = "share_discard"
    case errorAudioTooLarge = "error_audio_too_large"
    case errorUnsupportedAudio = "error_unsupported_audio"
    case errorEmptyAudio = "error_empty_audio"
    case errorLengthRequired = "error_length_required"
    case haveInvite = "have_invite"
    case haveInviteHint = "have_invite_hint"
    case inviteEntryTitle = "invite_entry_title"
    case inviteEntryBody = "invite_entry_body"
    case inviteEntryLabel = "invite_entry_label"
    case inviteEntrySubmit = "invite_entry_submit"
    case childPhoneTitle = "child_phone_title"
    case childPhoneBody = "child_phone_body"
    case childPhoneLabel = "child_phone_label"
    case childPhoneSubmit = "child_phone_submit"
    case childPhoneAlready = "child_phone_already"
    case childOtpTitle = "child_otp_title"
    case childOtpBody = "child_otp_body"
    case childOtpBodyPlain = "child_otp_body_plain"
    case childOtpLabel = "child_otp_label"
    case childOtpSubmit = "child_otp_submit"
    case childOtpVoice = "child_otp_voice"
    case childOtpResend = "child_otp_resend"
    case childCodeTitle = "child_code_title"
    case childCodeBody = "child_code_body"
    case childCodeLabel = "child_code_label"
    case childCodeAgainLabel = "child_code_again_label"
    case childCodeSubmit = "child_code_submit"
    case childCodeMismatch = "child_code_mismatch"
    case childWaitingTitle = "child_waiting_title"
    case childWaitingBody = "child_waiting_body"
    case childWaitingBodyNumber = "child_waiting_body_number"
    case childWaitingRefresh = "child_waiting_refresh"
    case childHomeIdle = "child_home_idle"
    case childHomeWaiting = "child_home_waiting"
    case childHomeAnswer = "child_home_answer"
    case childHomeReset = "child_home_reset"
    case childQuestion = "child_question"
    case childQuestionHint = "child_question_hint"
    case childYes = "child_yes"
    case childNo = "child_no"
    case childNotNow = "child_not_now"
    case childReveal = "child_reveal"
    case childRevealHint = "child_reveal_hint"
    case childCodeShown = "child_code_shown"
    case childHideCode = "child_hide_code"
    case childFallbackStatic = "child_fallback_static"
    case childResetTitle = "child_reset_title"
    case childResetBody = "child_reset_body"
    case childResetUnlock = "child_reset_unlock"
    case childResetSubmit = "child_reset_submit"
    case childResetDone = "child_reset_done"
    case childCodeExists = "child_code_exists"
    case childResultYes = "child_result_yes"
    case childResultNo = "child_result_no"
    case childResultClosed = "child_result_closed"
    case childNotificationBody = "child_notification_body"
    case childNotificationChannel = "child_notification_channel"
    case biometricTitleAnswer = "biometric_title_answer"
    case biometricTitleCode = "biometric_title_code"
    case biometricTitleReset = "biometric_title_reset"
    case biometricSubtitle = "biometric_subtitle"
    case errorInviteInvalid = "error_invite_invalid"
    case errorInviteExpired = "error_invite_expired"
    case errorNotAChild = "error_not_a_child"
    case errorBiometricRequired = "error_biometric_required"
    case errorPhoneAlreadySet = "error_phone_already_set"
    case errorSameNumber = "error_same_number"
    case errorOtpWrong = "error_otp_wrong"
    case errorOtpExpired = "error_otp_expired"
    case errorInvalidCode = "error_invalid_code"
    case errorNotTheChild = "error_not_the_child"
    case errorOtpRateLimited = "error_otp_rate_limited"
    case errorOtpUnavailable = "error_otp_unavailable"
    case errorOtpSmsFailed = "error_otp_sms_failed"
    case outboundLabelTitle = "outbound_label_title"
    case outboundLabelBody = "outbound_label_body"
    case outboundLabelOpenSettings = "outbound_label_open_settings"
    case outboundLabelUnavailable = "outbound_label_unavailable"
    case outboundLabelOn = "outbound_label_on"
    case outboundLabelOff = "outbound_label_off"
    case callerLabelBody = "caller_label_body"
    case tabHome = "tab_home"
    case tabHistory = "tab_history"
    case tabFamily = "tab_family"
    case homeBrand = "home_brand"
    case homeGreeting = "home_greeting"
    case homeGreetingPlain = "home_greeting_plain"
    case homeHeroKicker = "home_hero_kicker"
    case homeHeroTitle = "home_hero_title"
    case homeSeeAll = "home_see_all"
    case homeUsingApp = "home_using_app"
    case homeLiveTitle = "home_live_title"
    case homeUntilCall = "home_until_call"
    case homeOpenProgress = "home_open_progress"
    case homeStepPush = "home_step_push"
    case homeStepBio = "home_step_bio"
    case homeStepCall = "home_step_call"
    case homeAmountLine = "home_amount_line"
    case progressWaiting = "progress_waiting"
    case progressStepPushTitle = "progress_step_push_title"
    case progressStepPushBody = "progress_step_push_body"
    case progressStepBioTitle = "progress_step_bio_title"
    case progressStepBioBody = "progress_step_bio_body"
    case progressStepCallTitle = "progress_step_call_title"
    case progressStepCallBody = "progress_step_call_body"
    case progressStepCallNone = "progress_step_call_none"
    case progressVoiceLabel = "progress_voice_label"
    case progressTextOnly = "progress_text_only"
    case v3ResultNav = "v3_result_nav"
    case v3Direct = "v3_direct"
    case v3AnswerCaption = "v3_answer_caption"
    case v3YesDetail = "v3_yes_detail"
    case v3NoDetail = "v3_no_detail"
    case v3HeadlineNo = "v3_headline_no"
    case v3HeadlineYes = "v3_headline_yes"
    case v3SheetScam = "v3_sheet_scam"
    case v3SheetYes = "v3_sheet_yes"
    case v3SheetYesBody = "v3_sheet_yes_body"
    case v3Done = "v3_done"
    case v3Share = "v3_share"
    case v3Today = "v3_today"
    case v3Yesterday = "v3_yesterday"
    case historyTitle = "history_title"
    case historyAll = "history_all"
    case historyGreen = "history_green"
    case historyRed = "history_red"
    case historyYellow = "history_yellow"
    case historyEmpty = "history_empty"
    case familyRoleParent = "family_role_parent"
    case familyChildCount = "family_child_count"
    case familyInviteLink = "family_invite_link"
    case familyCanCheck = "family_can_check"
    case familyNumberEnding = "family_number_ending"
    case shareKicker = "share_kicker"
    case shareWho = "share_who"
    case shareAsk = "share_ask"
    case childRequestTitle = "child_request_title"
    case childAskerSubtitle = "child_asker_subtitle"
    case childQuestionShort = "child_question_short"
    case childAmountLabel = "child_amount_label"
    case childAmountSource = "child_amount_source"
    case childSubmitFace = "child_submit_face"
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
        .newCaseAudioAttached: [
            .en: "Voice note attached: %1$s (%2$d KB). It stays on this phone until you tap Verify.",
            .ko: "음성 메시지가 첨부됐어요: %1$s (%2$d KB). 확인하기를 누르기 전에는 이 휴대폰에만 있어요.",
        ],
        .newCaseAudioRemove: [
            .en: "Remove voice note",
            .ko: "음성 메시지 빼기",
        ],
        .shareAudioTooLarge: [
            .en: "That voice note is over 10 MB, so it wasn't attached. You can paste the message instead.",
            .ko: "음성 메시지가 10MB를 넘어서 첨부하지 않았어요. 받은 내용을 글로 붙여 넣을 수 있어요.",
        ],
        .shareAudioEmpty: [
            .en: "That voice note was empty, so it wasn't attached.",
            .ko: "음성 메시지가 비어 있어서 첨부하지 않았어요.",
        ],
        .shareAudioUnsupported: [
            .en: "Family Shield can't read that file as a voice note. You can paste the message instead.",
            .ko: "이 파일은 음성 메시지로 읽을 수 없어요. 받은 내용을 글로 붙여 넣을 수 있어요.",
        ],
        .shareAudioUnreadable: [
            .en: "That voice note couldn't be read. You can paste the message instead.",
            .ko: "음성 메시지를 읽지 못했어요. 받은 내용을 글로 붙여 넣을 수 있어요.",
        ],
        .shareWaitingSignin: [
            .en: "A message is waiting. Sign in as a parent. Nothing is sent until you tap Verify.",
            .ko: "확인할 메시지가 대기 중이에요. 보호자로 로그인하세요. 확인하기를 누르기 전에는 아무것도 전송되지 않아요.",
        ],
        .shareWaitingFamily: [
            .en: "A message is waiting. Create your family, then choose who to ask. Nothing is sent until you tap Verify.",
            .ko: "확인할 메시지가 대기 중이에요. 가족을 만든 뒤 누구에게 물어볼지 고르세요. 확인하기를 누르기 전에는 아무것도 전송되지 않아요.",
        ],
        .shareNeedsParent: [
            .en: "This account is a child, so it can't verify a message. Sign in as a parent. Nothing was sent.",
            .ko: "이 계정은 자녀라서 메시지를 확인할 수 없어요. 보호자 계정으로 로그인해 주세요. 전송된 것은 없어요.",
        ],
        .shareDiscard: [
            .en: "Discard",
            .ko: "지우기",
        ],
        .errorAudioTooLarge: [
            .en: "That voice note is over 10 MB. Try a shorter one, or paste the message.",
            .ko: "음성 메시지가 10MB를 넘어요. 더 짧은 녹음을 보내거나 글로 붙여 넣으세요.",
        ],
        .errorUnsupportedAudio: [
            .en: "That file isn't an audio voice note.",
            .ko: "이 파일은 음성 파일이 아니에요.",
        ],
        .errorEmptyAudio: [
            .en: "That voice note was empty.",
            .ko: "음성 메시지가 비어 있어요.",
        ],
        .errorLengthRequired: [
            .en: "The voice note couldn't be sent. Please try again.",
            .ko: "음성 메시지를 보내지 못했어요. 다시 시도해 주세요.",
        ],
        .haveInvite: [
            .en: "I have an invite code",
            .ko: "초대 코드가 있어요",
        ],
        .haveInviteHint: [
            .en: "A parent sent you a one-time code. You'll join as their child.",
            .ko: "보호자가 보낸 일회용 코드로 자녀로 참여해요.",
        ],
        .inviteEntryTitle: [
            .en: "Join your family",
            .ko: "가족에 참여",
        ],
        .inviteEntryBody: [
            .en: "Enter the invite code your parent sent. This account is for you, not for a younger sibling.",
            .ko: "보호자가 보낸 초대 코드를 입력하세요. 이 계정은 본인용이며, 어린 동생을 위한 계정이 아니에요.",
        ],
        .inviteEntryLabel: [
            .en: "Invite code",
            .ko: "초대 코드",
        ],
        .inviteEntrySubmit: [
            .en: "Join",
            .ko: "참여하기",
        ],
        .childPhoneTitle: [
            .en: "Your mobile number",
            .ko: "휴대폰 번호",
        ],
        .childPhoneBody: [
            .en: "Family Shield texts a 6-digit code to prove this number is yours. Only +1 (US, Canada) and +82 (Korea). Your parent never sees your check code.",
            .ko: "이 번호가 본인 것인지 확인하려고 6자리 코드를 문자로 보내요. +1(미국, 캐나다)과 +82(한국)만 사용할 수 있어요. 보호자는 확인 번호를 볼 수 없어요.",
        ],
        .childPhoneLabel: [
            .en: "Mobile number, with country code",
            .ko: "국가 번호가 포함된 휴대폰 번호",
        ],
        .childPhoneSubmit: [
            .en: "Send the code",
            .ko: "코드 보내기",
        ],
        .childPhoneAlready: [
            .en: "This account already has a phone number.",
            .ko: "이 계정에는 이미 전화번호가 있어요.",
        ],
        .childOtpTitle: [
            .en: "Enter the text code",
            .ko: "문자 코드 입력",
        ],
        .childOtpBody: [
            .en: "We sent a 6-digit code to the number ending %1$s. It expires in 10 minutes.",
            .ko: "끝이 %1$s인 번호로 6자리 코드를 보냈어요. 10분 동안 유효해요.",
        ],
        .childOtpBodyPlain: [
            .en: "We sent a 6-digit code to your phone. It expires in 10 minutes.",
            .ko: "휴대폰으로 6자리 코드를 보냈어요. 10분 동안 유효해요.",
        ],
        .childOtpLabel: [
            .en: "6-digit code",
            .ko: "6자리 코드",
        ],
        .childOtpSubmit: [
            .en: "Verify number",
            .ko: "번호 확인",
        ],
        .childOtpVoice: [
            .en: "Call me with the code instead",
            .ko: "전화로 코드 듣기",
        ],
        .childOtpResend: [
            .en: "Send the text again",
            .ko: "문자 다시 보내기",
        ],
        .childCodeTitle: [
            .en: "Choose a check code",
            .ko: "확인 번호 정하기",
        ],
        .childCodeBody: [
            .en: "Pick 4 digits you'll remember and enter them twice. Your parent never sees them. If you forget them, you can set new ones after a fingerprint or face check.",
            .ko: "기억할 4자리 숫자를 두 번 입력하세요. 보호자는 이 번호를 볼 수 없어요. 잊어버리면 지문이나 얼굴 확인 뒤에 새로 정할 수 있어요.",
        ],
        .childCodeLabel: [
            .en: "4-digit check code",
            .ko: "4자리 확인 번호",
        ],
        .childCodeAgainLabel: [
            .en: "Enter it again",
            .ko: "한 번 더 입력",
        ],
        .childCodeSubmit: [
            .en: "Save check code",
            .ko: "확인 번호 저장",
        ],
        .childCodeMismatch: [
            .en: "Those don't match. Enter the same 4 digits twice.",
            .ko: "두 번호가 달라요. 같은 4자리를 두 번 입력하세요.",
        ],
        .childWaitingTitle: [
            .en: "Waiting for your parent",
            .ko: "보호자의 승인을 기다리는 중",
        ],
        .childWaitingBody: [
            .en: "Ask your parent to confirm you in Family Shield. Until they do, they can't start a check.",
            .ko: "보호자에게 패밀리 쉴드에서 가입을 승인해 달라고 하세요. 승인 전에는 확인을 시작할 수 없어요.",
        ],
        .childWaitingBodyNumber: [
            .en: "Ask your parent to confirm you in Family Shield. Your number ends in %1$s.",
            .ko: "보호자에게 패밀리 쉴드에서 가입을 승인해 달라고 하세요. 번호 끝자리는 %1$s이에요.",
        ],
        .childWaitingRefresh: [
            .en: "Check again",
            .ko: "다시 확인",
        ],
        .childHomeIdle: [
            .en: "No request right now. When your family asks Family Shield to check a message, you'll get a notification. The notification has no Yes or No button and no code. Open it, then confirm with your fingerprint or face to answer.",
            .ko: "지금 확인 요청이 없어요. 가족이 메시지 확인을 요청하면 알림이 와요. 알림에는 예/아니요 버튼도, 코드도 없어요. 알림을 연 다음 지문이나 얼굴로 확인한 뒤 답하세요.",
        ],
        .childHomeWaiting: [
            .en: "Your family is waiting for your answer.",
            .ko: "가족이 답을 기다리고 있어요.",
        ],
        .childHomeAnswer: [
            .en: "Answer",
            .ko: "답하기",
        ],
        .childHomeReset: [
            .en: "Set a new check code",
            .ko: "확인 번호 새로 정하기",
        ],
        .childQuestion: [
            .en: "Did you send your family a message asking for money?",
            .ko: "가족에게 돈을 부탁하는 메시지를 보낸 적이 있나요?",
        ],
        .childQuestionHint: [
            .en: "Only your answer changes the result. Not now leaves the check open, and your family may call you.",
            .ko: "결과 색깔을 바꾸는 것은 본인의 답뿐이에요. 나중에를 누르면 확인은 열린 채로 남고, 가족이 전화할 수 있어요.",
        ],
        .childYes: [
            .en: "Yes",
            .ko: "예",
        ],
        .childNo: [
            .en: "No",
            .ko: "아니요",
        ],
        .childNotNow: [
            .en: "Not now",
            .ko: "나중에",
        ],
        .childReveal: [
            .en: "Show the code for this call",
            .ko: "이 통화의 코드 보기",
        ],
        .childRevealHint: [
            .en: "Your family is calling. The 6-digit code stays hidden until you confirm with your fingerprint or face. It is not in the notification.",
            .ko: "가족이 전화하고 있어요. 6자리 코드는 지문이나 얼굴로 확인하기 전에는 보이지 않아요. 알림에는 코드가 없어요.",
        ],
        .childCodeShown: [
            .en: "Enter this code on the phone keypad, then press 1 for yes or 2 for no. It works once, for 5 minutes, and it is not saved on this phone.",
            .ko: "키패드에 이 코드를 입력한 다음, 맞으면 1, 아니면 2를 누르세요. 이 코드는 한 번만, 5분 동안 쓸 수 있고, 이 휴대폰에 저장되지 않아요.",
        ],
        .childHideCode: [
            .en: "Hide the code",
            .ko: "코드 숨기기",
        ],
        .childFallbackStatic: [
            .en: "This call wants your 4-digit check code. If it asked for 6 digits, press star, then enter your check code.",
            .ko: "이 통화는 4자리 확인 번호를 물어봐요. 6자리를 물어보면 별표(*)를 누른 다음 확인 번호를 입력하세요.",
        ],
        .childResetTitle: [
            .en: "New check code",
            .ko: "새 확인 번호",
        ],
        .childResetBody: [
            .en: "Confirm with your fingerprint or face first. Then enter a new 4-digit code twice. This replaces the old one.",
            .ko: "먼저 지문이나 얼굴로 확인하세요. 그다음 새 4자리 번호를 두 번 입력하세요. 이전 번호는 바뀌어요.",
        ],
        .childResetUnlock: [
            .en: "Confirm with Face ID",
            .ko: "Face ID로 확인",
        ],
        .childResetSubmit: [
            .en: "Save the new code",
            .ko: "새 번호 저장",
        ],
        .childResetDone: [
            .en: "Your check code was updated.",
            .ko: "확인 번호를 바꿨어요.",
        ],
        .childCodeExists: [
            .en: "This account already has a check code. Replacing it needs a fingerprint or face check.",
            .ko: "이 계정에는 이미 확인 번호가 있어요. 바꾸려면 지문이나 얼굴 확인이 필요해요.",
        ],
        .childResultYes: [
            .en: "You answered yes.",
            .ko: "예라고 답했어요.",
        ],
        .childResultNo: [
            .en: "You answered no.",
            .ko: "아니요라고 답했어요.",
        ],
        .childResultClosed: [
            .en: "This check ended without your answer.",
            .ko: "답을 남기지 않은 채로 이 확인이 끝났어요.",
        ],
        .childNotificationBody: [
            .en: "Family Shield needs you to confirm a request.",
            .ko: "패밀리 쉴드에서 확인이 필요한 요청이 있어요.",
        ],
        .childNotificationChannel: [
            .en: "Requests",
            .ko: "확인 요청",
        ],
        .biometricTitleAnswer: [
            .en: "Confirm it's you",
            .ko: "본인 확인",
        ],
        .biometricTitleCode: [
            .en: "Show the call code",
            .ko: "통화 코드 보기",
        ],
        .biometricTitleReset: [
            .en: "Change your check code",
            .ko: "확인 번호 변경",
        ],
        .biometricSubtitle: [
            .en: "Family Shield uses Face ID. The device passcode is there if Face ID isn't available, so a broken Face ID does not trap you.",
            .ko: "패밀리 쉴드는 Face ID를 사용해요. Face ID를 쓸 수 없으면 기기 암호로 확인할 수 있어서, Face ID가 고장 나도 갇히지 않아요.",
        ],
        .errorInviteInvalid: [
            .en: "That invite code isn't valid. Ask your parent for a new one.",
            .ko: "초대 코드가 올바르지 않아요. 보호자에게 새 코드를 요청하세요.",
        ],
        .errorInviteExpired: [
            .en: "That invite code has expired. Ask your parent to send a new one.",
            .ko: "초대 코드가 만료됐어요. 보호자에게 새 코드를 요청하세요.",
        ],
        .errorNotAChild: [
            .en: "This account isn't a child in a family.",
            .ko: "이 계정은 가족의 자녀가 아니에요.",
        ],
        .errorBiometricRequired: [
            .en: "Confirm with your fingerprint or face before changing the check code.",
            .ko: "확인 번호를 바꾸기 전에 지문이나 얼굴로 확인하세요.",
        ],
        .errorPhoneAlreadySet: [
            .en: "This account already has a phone number.",
            .ko: "이 계정에는 이미 전화번호가 있어요.",
        ],
        .errorSameNumber: [
            .en: "That's already your number.",
            .ko: "이미 쓰고 있는 번호예요.",
        ],
        .errorOtpWrong: [
            .en: "That code is wrong. Try again.",
            .ko: "코드가 틀려요. 다시 입력하세요.",
        ],
        .errorOtpExpired: [
            .en: "That code expired. Send a new one.",
            .ko: "코드가 만료됐어요. 새로 받아 주세요.",
        ],
        .errorInvalidCode: [
            .en: "Use exactly 4 digits.",
            .ko: "숫자 4자리를 입력하세요.",
        ],
        .errorNotTheChild: [
            .en: "Only the child can answer this check.",
            .ko: "이 확인에는 자녀만 답할 수 있어요.",
        ],
        .errorOtpRateLimited: [
            .en: "You've reached the limit of 5 text codes in 24 hours. Try again later.",
            .ko: "24시간 동안 보낼 수 있는 문자 코드 5회를 모두 썼어요. 나중에 다시 시도하세요.",
        ],
        .errorOtpUnavailable: [
            .en: "Text codes aren't available on this server right now.",
            .ko: "이 서버에서는 지금 문자 코드를 보낼 수 없어요.",
        ],
        .errorOtpSmsFailed: [
            .en: "The text didn't go through. Please try again.",
            .ko: "문자가 전달되지 않았어요. 다시 시도해 주세요.",
        ],
        .outboundLabelTitle: [
            .en: "Label Family Shield's call",
            .ko: "패밀리 쉴드 전화 표시",
        ],
        .outboundLabelBody: [
            .en: "Optional. The check code works without this. This labels one number, the number Family Shield calls from, as Family Shield, so the phone does not treat that call as an unknown caller. It does not mark your number or any other number as genuine. On Android, only one app can hold call screening, so turning this on replaces another screening app.",
            .ko: "선택 사항입니다. 확인 번호만으로도 됩니다. 패밀리 쉴드가 거는 번호 하나만 Family Shield로 표시해서, 그 전화가 모르는 번호로 조용히 되지 않게 합니다. 본인의 번호나 다른 번호를 진짜라고 표시하지 않습니다. Android에서는 통화 스크리닝을 맡은 앱이 하나뿐이라, 이것을 켜면 다른 스크리닝 앱을 대신합니다.",
        ],
        .outboundLabelOpenSettings: [
            .en: "Open the system setting",
            .ko: "시스템 설정 열기",
        ],
        .outboundLabelUnavailable: [
            .en: "This phone doesn't offer call screening. The check code still works.",
            .ko: "이 휴대폰은 통화 스크리닝을 제공하지 않아요. 확인 번호는 그대로 쓸 수 있어요.",
        ],
        .outboundLabelOn: [
            .en: "Call labeling is on.",
            .ko: "전화 표시가 켜져 있어요.",
        ],
        .outboundLabelOff: [
            .en: "Call labeling is off. The check code still works.",
            .ko: "전화 표시가 꺼져 있어요. 확인 번호는 그대로 쓸 수 있어요.",
        ],
        .callerLabelBody: [
            .en: "Family Shield is calling for your family.",
            .ko: "패밀리 쉴드가 가족을 대신해 전화하고 있어요.",
        ],
        .tabHome: [.en: "Home", .ko: "홈"],
        .tabHistory: [.en: "History", .ko: "확인 기록"],
        .tabFamily: [.en: "Family", .ko: "가족"],
        .homeBrand: [.en: "FAMILY SHIELD", .ko: "FAMILY SHIELD"],
        .homeGreeting: [.en: "Hello, %1$s", .ko: "%1$s님, 안녕하세요"],
        .homeGreetingPlain: [.en: "Hello", .ko: "안녕하세요"],
        .homeHeroKicker: [.en: "BEFORE YOU PAY", .ko: "BEFORE YOU PAY"],
        .homeHeroTitle: [.en: "A request came in.\nCheck it with your child.", .ko: "받은 요청,\n자녀에게 확인하세요"],
        .homeSeeAll: [.en: "See all", .ko: "모두 보기"],
        .homeUsingApp: [.en: "Using the app", .ko: "앱 사용"],
        .homeLiveTitle: [.en: "Checking with %1$s", .ko: "%1$s에게 확인 중"],
        .homeUntilCall: [.en: "Until the call", .ko: "전화 확인까지"],
        .homeOpenProgress: [.en: "See progress", .ko: "진행 상황 보기"],
        .homeStepPush: [.en: "Alert", .ko: "앱 알림"],
        .homeStepBio: [.en: "Identity", .ko: "본인 확인"],
        .homeStepCall: [.en: "Call", .ko: "전화 확인"],
        .homeAmountLine: [.en: "%1$s request", .ko: "%1$s 요청"],
        .progressWaiting: [.en: "Waiting for an answer in the app", .ko: "앱으로 답변을 기다리고 있어요"],
        .progressStepPushTitle: [.en: "Sent an alert in the app", .ko: "앱으로 알림을 보냈어요"],
        .progressStepPushBody: [.en: "Today %1$s", .ko: "오늘 %1$s"],
        .progressStepBioTitle: [.en: "Answer after an identity check", .ko: "본인 확인 후 답변"],
        .progressStepBioBody: [.en: "Continues when %1$s opens the app", .ko: "%1$s님이 앱을 열면 진행돼요"],
        .progressStepCallTitle: [.en: "Call if there is no answer", .ko: "답이 없으면 전화해요"],
        .progressStepCallBody: [.en: "Registered number ending %1$s", .ko: "등록된 번호 끝자리 %1$s로"],
        .progressStepCallNone: [.en: "The registered number", .ko: "등록된 번호로"],
        .progressVoiceLabel: [.en: "Voice message received", .ko: "받은 음성 메시지"],
        .progressTextOnly: [.en: "The original voice file is not on this phone. The text below is the message that was checked.", .ko: "원본 음성은 이 휴대폰에 없어요. 아래는 확인한 메시지예요."],
        .v3ResultNav: [.en: "Result", .ko: "확인 결과"],
        .v3Direct: [.en: "DIRECT ANSWER", .ko: "DIRECT ANSWER"],
        .v3AnswerCaption: [.en: "Answer after an identity check", .ko: "본인 확인 후 답변"],
        .v3YesDetail: [.en: "I sent it", .ko: "제가 보냈어요"],
        .v3NoDetail: [.en: "I didn't send it", .ko: "보내지 않았어요"],
        .v3HeadlineNo: [.en: "%1$s didn't send\nthis request", .ko: "%1$s 보낸\n요청이 아니에요"],
        .v3HeadlineYes: [.en: "This request matches\nwhat %1$s sent", .ko: "%1$s 보낸\n요청이 맞아요"],
        .v3SheetScam: [.en: "This may be a scam", .ko: "사기가 의심돼요"],
        .v3SheetYes: [.en: "Talk before you send", .ko: "보내기 전, 직접 이야기하세요"],
        .v3SheetYesBody: [.en: "Contact %1$s directly and check the request once more.", .ko: "%1$s에게 직접 연락해 요청 내용을 한 번 더 확인하세요."],
        .v3Done: [.en: "Done checking", .ko: "확인 완료"],
        .v3Share: [.en: "Share a warning with your family", .ko: "가족에게 경고 공유"],
        .v3Today: [.en: "Today", .ko: "오늘"],
        .v3Yesterday: [.en: "Yesterday", .ko: "어제"],
        .historyTitle: [.en: "History", .ko: "확인 기록"],
        .historyAll: [.en: "All", .ko: "전체"],
        .historyGreen: [.en: "Confirmed", .ko: "확인됨"],
        .historyRed: [.en: "Suspected scam", .ko: "사기 의심"],
        .historyYellow: [.en: "Not confirmed", .ko: "확인 안 됨"],
        .historyEmpty: [.en: "Nothing in this filter yet.", .ko: "이 필터에는 아직 기록이 없어요."],
        .familyRoleParent: [.en: "Parent who manages the family", .ko: "가족을 관리하는 보호자"],
        .familyChildCount: [.en: "%1$d children", .ko: "자녀 %1$d명"],
        .familyInviteLink: [.en: "Invite", .ko: "초대하기"],
        .familyCanCheck: [.en: "Can answer in the app", .ko: "앱으로 확인 가능"],
        .familyNumberEnding: [.en: "Number ending %1$s", .ko: "번호 끝자리 %1$s"],
        .shareKicker: [.en: "VOICE NOTE", .ko: "VOICE NOTE"],
        .shareWho: [.en: "Who should we ask?", .ko: "누구에게 물어볼까요?"],
        .shareAsk: [.en: "Ask %1$s", .ko: "%1$s에게 확인 요청"],
        .childRequestTitle: [.en: "Family check", .ko: "가족 확인 요청"],
        .childAskerSubtitle: [.en: "%1$s asked you to confirm", .ko: "%1$s님이 확인을 부탁했어요"],
        .childQuestionShort: [.en: "Did you send this request?", .ko: "이 요청, 직접 보냈나요?"],
        .childAmountLabel: [.en: "Amount in the request", .ko: "요청 금액"],
        .childAmountSource: [.en: "From a voice message", .ko: "음성 메시지로 받은 요청"],
        .childSubmitFace: [.en: "Confirm with Face ID and send", .ko: "Face ID로 답변 보내기"],
    ]
}
