package com.example.myapplication

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.FrameLayout
import androidx.activity.ComponentActivity
import androidx.activity.OnBackPressedCallback
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat

class MainActivity : ComponentActivity() {

    private lateinit var web: WebView
    private lateinit var server: AssetServer

    // Whatever the user answers, the daily job is already scheduled; a refusal only means
    // it runs and posts nothing until they allow notifications in settings.
    private val askNotify =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
            if (granted) ForecastWorker.showOnce(this)
        }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        server = AssetServer(assets, "site").start()
        startDailyForecast()

        web = WebView(this).apply {
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            webViewClient = WebViewClient()          // keep navigation inside the app
            loadUrl("http://127.0.0.1:${server.port}/index.html")
        }
        // The WebView sits in a padded frame: Android 15+ draws edge to edge, and the
        // page's own sticky header ignores padding set on the WebView itself.
        val root = FrameLayout(this).apply { addView(web) }
        setContentView(root)
        ViewCompat.setOnApplyWindowInsetsListener(root) { v, insets ->
            val bars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            v.setPadding(bars.left, bars.top, bars.right, bars.bottom)
            insets
        }
        ViewCompat.requestApplyInsets(root)

        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                if (web.canGoBack()) {
                    web.goBack()
                } else {
                    isEnabled = false
                    onBackPressedDispatcher.onBackPressed()
                }
            }
        })
    }

    /**
     * Schedules tomorrow's forecast, and on a fresh install posts one straight away so the
     * user sees what they have just signed up for rather than waiting until 7am.
     */
    private fun startDailyForecast() {
        ForecastWorker.schedule(this)

        val prefs = getSharedPreferences("forecast", Context.MODE_PRIVATE)
        val firstRun = !prefs.getBoolean("greeted", false)
        prefs.edit().putBoolean("greeted", true).apply()

        val needsAsk = Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) !=
            PackageManager.PERMISSION_GRANTED
        when {
            needsAsk -> askNotify.launch(Manifest.permission.POST_NOTIFICATIONS)
            firstRun -> ForecastWorker.showOnce(this)
        }
    }

    override fun onDestroy() {
        server.close()
        super.onDestroy()
    }
}
