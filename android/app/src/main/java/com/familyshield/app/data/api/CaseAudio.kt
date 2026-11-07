package com.familyshield.app.data.api

import java.io.File

/**
 * A voice note already stored in the app. [ApiClient.openCase] sends it as the
 * multipart `audio` part. Building this object does not upload anything.
 */
data class CaseAudio(
    val file: File,
    val uploadName: String,
    val contentType: String,
)
