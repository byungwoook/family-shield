package com.familyshield.app.domain

import java.security.MessageDigest
import java.time.Instant
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.time.format.DateTimeParseException
import java.time.format.FormatStyle
import java.util.Locale

object Nonces {
    /** Lowercase hex SHA-256 of the raw nonce: what Google gets as the request nonce (contract §3). */
    fun sha256Hex(raw: String): String =
        MessageDigest.getInstance("SHA-256")
            .digest(raw.toByteArray(Charsets.UTF_8))
            .joinToString("") { "%02x".format(it) }
}

object ApiLocale {
    /** The only two locales the API accepts: "ko" for a Korean device, else "en". */
    fun of(locale: Locale): String = if (locale.language == "ko") "ko" else "en"
}

/** What the parent typed as a child's number, checked the way the server checks it. */
sealed interface PhoneInput {
    data class Valid(val e164: String) : PhoneInput
    data object Invalid : PhoneInput
    data object UnsupportedCountry : PhoneInput

    companion object {
        private val E164 = Regex("^\\+[1-9][0-9]{1,14}$")
        private val SEPARATORS = Regex("[\\s().\\-]")

        /**
         * Removes spaces, dashes, dots, and brackets. A Korean number written with
         * its trunk zero after the country code ("+82 010 ...") loses that zero,
         * because E.164 has none. Only +1 and +82 are supported (contract §1).
         */
        fun parse(raw: String): PhoneInput {
            var compact = raw.replace(SEPARATORS, "")
            if (compact.startsWith("+820")) compact = "+82" + compact.removePrefix("+820")
            if (!E164.matches(compact)) return Invalid
            if (!compact.startsWith("+1") && !compact.startsWith("+82")) return UnsupportedCountry
            return Valid(compact)
        }
    }
}

object Times {
    fun parse(iso: String?): Instant? = try {
        iso?.let { OffsetDateTime.parse(it).toInstant() }
    } catch (e: DateTimeParseException) {
        null
    }

    /** A short local time ("3:42 PM", "오후 3:42") in the device time zone. */
    fun shortTime(iso: String?, locale: Locale, zone: ZoneId = ZoneId.systemDefault()): String {
        val instant = parse(iso) ?: return ""
        return DateTimeFormatter.ofLocalizedTime(FormatStyle.SHORT).withLocale(locale).withZone(zone).format(instant)
    }

    /** A short local date and time, for the case list. */
    fun shortDateTime(iso: String?, locale: Locale, zone: ZoneId = ZoneId.systemDefault()): String {
        val instant = parse(iso) ?: return ""
        return DateTimeFormatter.ofLocalizedDateTime(FormatStyle.SHORT).withLocale(locale).withZone(zone).format(instant)
    }
}
