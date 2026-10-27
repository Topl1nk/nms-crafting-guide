# NMSii for Android

The built site (`../dist`) in a WebView (Capacitor 6, offline: everything is in the APK). `NMSii-debug.apk` here is a debug build
(signed with the debug key): install it with `adb install -r NMSii-debug.apk` or by opening it on the phone (allow installs from the file manager).

To rebuild after the site changes (JDK 17 and the Android SDK, `ANDROID_HOME`, are needed):

    cd ..            ; npm run build
    cd apk           ; npx cap sync android
    cd android       ; gradlew.bat assembleDebug
    # the APK: android/app/build/outputs/apk/debug/app-debug.apk

`android/local.properties` holds `sdk.dir` (written once, not part of the project). A release build for a store needs your own keystore.
