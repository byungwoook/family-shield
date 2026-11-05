import org.jetbrains.kotlin.gradle.dsl.JvmTarget

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.kotlin.serialization)
}

// -PfsApiBase=https://api.example.com points a build at a backend. Debug defaults
// to the emulator's view of the host machine; release has no default on purpose.
val apiBase = providers.gradleProperty("fsApiBase").orNull
// The OAuth "server" (web) client id the Google ID token is requested for. It is
// the backend's GOOGLE_SERVER_CLIENT_ID. Blank: Google sign-in is hidden.
val googleServerClientId = providers.gradleProperty("fsGoogleServerClientId").getOrElse("")

fun quoted(value: String) = "\"" + value.replace("\\", "\\\\").replace("\"", "\\\"") + "\""

android {
    namespace = "com.familyshield.app"
    compileSdk = 36

    defaultConfig {
        applicationId = providers.gradleProperty("fsApplicationId").getOrElse("com.familyshield.app")
        minSdk = 26
        targetSdk = 36
        versionCode = 1
        versionName = "0.1.0"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        buildConfigField("String", "GOOGLE_SERVER_CLIENT_ID", quoted(googleServerClientId))
    }

    buildTypes {
        debug {
            buildConfigField("String", "API_BASE_URL", quoted(apiBase ?: "http://10.0.2.2:8000"))
            // The backend's DEV_AUTH login, for running against a local server
            // before the Google client id exists. Never in release.
            buildConfigField("boolean", "DEV_LOGIN", "true")
        }
        release {
            buildConfigField("String", "API_BASE_URL", quoted(apiBase ?: ""))
            buildConfigField("boolean", "DEV_LOGIN", "false")
            isMinifyEnabled = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    buildFeatures {
        buildConfig = true
        compose = true
    }

    testOptions {
        unitTests.isIncludeAndroidResources = true
        unitTests.isReturnDefaultValues = true
    }
}

kotlin {
    compilerOptions {
        jvmTarget.set(JvmTarget.JVM_17)
    }
}

dependencies {
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.lifecycle.viewmodel.compose)
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.compose.material3)
    implementation(libs.androidx.navigation.compose)
    implementation(libs.androidx.datastore.preferences)
    implementation(libs.kotlinx.serialization.json)
    implementation(libs.kotlinx.coroutines.android)
    implementation(libs.okhttp)
    implementation(libs.androidx.credentials)
    implementation(libs.androidx.credentials.play.services)
    implementation(libs.google.identity.googleid)
    debugImplementation(libs.androidx.compose.ui.tooling)
    debugImplementation(libs.androidx.compose.ui.test.manifest)

    testImplementation(libs.junit)
    testImplementation(kotlin("test"))
    testImplementation(libs.kotlinx.coroutines.test)
    testImplementation(libs.okhttp.mockwebserver)
    testImplementation(libs.robolectric)
    testImplementation(platform(libs.androidx.compose.bom))
    testImplementation(libs.androidx.compose.ui.test.junit4)
}
