package com.familyshield.app

import android.content.Context
import com.familyshield.app.data.ApiPushApi
import com.familyshield.app.data.AuthRepository
import com.familyshield.app.data.CaseRepository
import com.familyshield.app.data.FamilyRepository
import com.familyshield.app.data.NoFirebaseToken
import com.familyshield.app.data.PushRegistrar
import com.familyshield.app.data.api.ApiClient
import com.familyshield.app.data.session.EncryptedTokenStore
import com.familyshield.app.data.session.KeystoreKeys
import com.familyshield.app.data.session.SessionManager
import com.familyshield.app.share.ShareInbox
import com.familyshield.app.ui.signin.GoogleSignInClient

/**
 * The app's object graph, built once per process by [FamilyShieldApp]. No DI
 * framework: one API client, one session, and the repositories over them.
 * Nothing here touches the Keystore until the session is loaded.
 */
class AppContainer(context: Context) {
    private val appContext = context.applicationContext

    val session: SessionManager by lazy {
        SessionManager(
            EncryptedTokenStore(
                prefs = appContext.getSharedPreferences(EncryptedTokenStore.PREFS_NAME, Context.MODE_PRIVATE),
                cipher = KeystoreKeys.sessionCipher(),
            ),
        )
    }

    val api: ApiClient by lazy {
        ApiClient(
            baseUrl = BuildConfig.API_BASE_URL,
            tokens = session,
            // Any 401 on an authenticated call: the session is gone, so sign out.
            onUnauthorized = { rejected -> session.signOutIfCurrent(rejected) },
        )
    }

    val auth: AuthRepository by lazy { AuthRepository(api, session) }
    val families: FamilyRepository by lazy { FamilyRepository(api) }
    val cases: CaseRepository by lazy { CaseRepository(api) }
    val shares: ShareInbox by lazy { ShareInbox(appContext) }
    val push: PushRegistrar by lazy { PushRegistrar(ApiPushApi(api), NoFirebaseToken) }
    val google: GoogleSignInClient by lazy { GoogleSignInClient(BuildConfig.GOOGLE_SERVER_CLIENT_ID) }

    /** Debug builds only: the backend's DEV_AUTH login. */
    val devLogin: Boolean get() = BuildConfig.DEV_LOGIN
}
