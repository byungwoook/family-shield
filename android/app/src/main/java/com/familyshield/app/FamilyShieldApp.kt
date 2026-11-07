package com.familyshield.app

import android.app.Application
import android.content.Context

class FamilyShieldApp : Application() {
    val container: AppContainer by lazy { AppContainer(this) }
}

/** The container of the running app. */
val Context.appContainer: AppContainer
    get() = (applicationContext as FamilyShieldApp).container
