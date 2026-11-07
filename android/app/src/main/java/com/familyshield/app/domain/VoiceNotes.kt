package com.familyshield.app.domain

import java.io.File
import java.io.IOException
import java.io.InputStream

/**
 * Voice-note rules for the share intent and for `POST /v1/cases`.
 *
 * The server accepts an audio content type of at most 10 MB (10 485 760 bytes)
 * and requires `Content-Length`. Messengers do not all use the same type: a
 * voice note may arrive as `audio/mp4` (.m4a), `audio/aac`, `audio/ogg` or
 * `audio/opus`, `audio/amr`, `application/ogg`, or `application/octet-stream`
 * with one of those extensions. This object turns those into an audio type
 * the server will store. A container that is often a video (`.mp4`, `.webm`,
 * `.3gp`) is accepted only when the sender already called it audio.
 */
object VoiceNotes {
    /** Contract limit for the `audio` part (`backend` `AUDIO_LIMIT`). */
    const val MAX_BYTES: Long = 10L * 1024L * 1024L

    private val AUDIO_ONLY_EXTENSION = mapOf(
        "m4a" to "audio/mp4",
        "aac" to "audio/aac",
        "ogg" to "audio/ogg",
        "oga" to "audio/ogg",
        "opus" to "audio/opus",
        "amr" to "audio/amr",
        "awb" to "audio/amr",
        "mp3" to "audio/mpeg",
        "wav" to "audio/wav",
        "wave" to "audio/wav",
        "caf" to "audio/x-caf",
        "flac" to "audio/flac",
        "gsm" to "audio/gsm",
    )

    /** The type without parameters: `audio/ogg; codecs=opus` becomes `audio/ogg`. */
    fun baseType(rawMime: String?): String? {
        val base = rawMime?.substringBefore(';')?.trim()?.lowercase().orEmpty()
        return base.ifEmpty { null }
    }

    fun extension(fileName: String?): String? {
        val base = fileName?.substringAfterLast('/')?.substringAfterLast('\\')?.trim().orEmpty()
        val dot = base.lastIndexOf('.')
        if (dot <= 0 || dot == base.lastIndex) return null
        val ext = base.substring(dot + 1).lowercase()
        if (ext.length !in 1..8 || ext.any { !it.isLetterOrDigit() }) return null
        return ext
    }

    /**
     * An audio content type the server accepts, or null when this is not a
     * voice note. [rawMime] may include parameters.
     */
    fun contentType(rawMime: String?, fileName: String?): String? {
        val mime = baseType(rawMime)
        val ext = extension(fileName)
        if (mime != null && mime.startsWith("audio/")) return canonical(mime, ext)
        if (mime == "application/ogg") return if (ext == "opus") "audio/opus" else "audio/ogg"
        if (mime == null || mime == "*/*" || mime == "application/octet-stream" || mime == "binary/octet-stream") {
            return AUDIO_ONLY_EXTENSION[ext]
        }
        // application/mp4 and similar, only when the extension itself is audio.
        // A video type stays null so a video is not uploaded as a voice note.
        if (mime.startsWith("application/")) return AUDIO_ONLY_EXTENSION[ext]
        return null
    }

    private fun canonical(mime: String, ext: String?): String = when (mime) {
        "audio/m4a", "audio/x-m4a", "audio/mp4", "audio/x-mp4" -> "audio/mp4"
        "audio/aac", "audio/x-aac", "audio/mp4a-latm" -> "audio/aac"
        "audio/opus" -> "audio/opus"
        "audio/ogg", "audio/vorbis", "audio/x-ogg" -> if (ext == "opus") "audio/opus" else "audio/ogg"
        "audio/amr", "audio/amr-wb" -> "audio/amr"
        "audio/3gpp", "audio/3gpp2" -> "audio/3gpp"
        "audio/mpeg", "audio/mp3", "audio/mpeg3", "audio/x-mpeg", "audio/x-mp3" -> "audio/mpeg"
        "audio/wav", "audio/x-wav", "audio/wave", "audio/vnd.wave" -> "audio/wav"
        "audio/webm", "audio/x-webm" -> "audio/webm"
        "audio/flac", "audio/x-flac" -> "audio/flac"
        else -> mime
    }

    fun suffix(contentType: String): String = when (contentType) {
        "audio/mp4" -> "m4a"
        "audio/aac" -> "aac"
        "audio/ogg" -> "ogg"
        "audio/opus" -> "opus"
        "audio/amr" -> "amr"
        "audio/mpeg" -> "mp3"
        "audio/wav" -> "wav"
        "audio/webm" -> "webm"
        "audio/3gpp" -> "3gp"
        "audio/flac" -> "flac"
        "audio/x-caf" -> "caf"
        "audio/gsm" -> "gsm"
        else -> "audio"
    }

    /** A short label for the draft screen. Path separators and quotes are removed. */
    fun displayLabel(fileName: String?, contentType: String): String {
        val base = fileName?.substringAfterLast('/')?.substringAfterLast('\\')?.trim().orEmpty()
        val cleaned = buildString {
            for (ch in base) {
                if (ch == '"' || ch == '\r' || ch == '\n') continue
                if (ch < ' ') continue
                append(ch)
                if (length >= 80) break
            }
        }.trim()
        if (cleaned.isEmpty()) return "voice-note.${suffix(contentType)}"
        return cleaned
    }

    /** Multipart filename: ASCII, no path, no header characters. */
    fun uploadName(displayName: String?, contentType: String): String {
        val base = displayName?.substringAfterLast('/')?.substringAfterLast('\\')?.trim().orEmpty()
        val cleaned = buildString {
            for (ch in base) {
                val ascii = ch in 'a'..'z' || ch in 'A'..'Z' || ch in '0'..'9' || ch == '.' || ch == '_' || ch == '-'
                if (ascii) append(ch)
                if (length >= 80) break
            }
        }.trim('.')
        val ext = suffix(contentType)
        if (cleaned.isEmpty() || cleaned.equals(ext, ignoreCase = true)) return "voice-note.$ext"
        if (extension(cleaned) == null) return "$cleaned.$ext"
        return cleaned
    }

    sealed class Copy {
        data class Ok(val bytes: Long) : Copy()
        data object Empty : Copy()
        data object TooLarge : Copy()
        data object Unreadable : Copy()
    }

    /**
     * Copies [input] into [dest] and stops if another byte would pass [limit].
     * Empty, too-large, and unreadable results delete [dest]. The caller closes [input].
     */
    fun copyCapped(input: InputStream, dest: File, limit: Long = MAX_BYTES): Copy {
        dest.parentFile?.mkdirs()
        var written = 0L
        try {
            dest.outputStream().use { out ->
                val buffer = ByteArray(8192)
                while (true) {
                    val read = input.read(buffer)
                    if (read < 0) break
                    if (read == 0) continue
                    if (written + read > limit) {
                        dest.delete()
                        return Copy.TooLarge
                    }
                    out.write(buffer, 0, read)
                    written += read
                }
            }
        } catch (_: IOException) {
            dest.delete()
            return Copy.Unreadable
        }
        if (written == 0L) {
            dest.delete()
            return Copy.Empty
        }
        return Copy.Ok(written)
    }
}
