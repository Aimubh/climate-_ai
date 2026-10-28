package com.example.myapplication

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.ExistingWorkPolicy
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.Worker
import androidx.work.WorkerParameters
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.Date
import java.util.concurrent.TimeUnit

/**
 * Posts tomorrow's forecast once a day.
 *
 * Carries no network constraint on purpose: it must still fire with the radio off, falling
 * back from the live feed to the last fetch to the model run bundled in the APK. Offline is
 * the normal case here, not the error case.
 */
class ForecastWorker(ctx: Context, params: WorkerParameters) : Worker(ctx, params) {

    override fun doWork(): Result {
        val now = Date()
        val day = Forecast.tomorrow(now)
        val prefs = applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

        // 1. the live feed, if the network is there at all
        val live = try {
            fetchLive()
        } catch (e: Exception) {
            emptyList()
        }
        if (live.isNotEmpty()) {
            prefs.edit()
                .putString(KEY_DAYS, encode(live))
                .putString(KEY_SAVED_ON, Forecast.isoDay(now))
                .apply()
        }

        // 2. whatever the last successful fetch left behind
        val saved = decode(prefs.getString(KEY_DAYS, null))
        val savedOn = prefs.getString(KEY_SAVED_ON, null)

        // 3. the run shipped inside the APK, which works with no network ever
        val bundled = readBundled()

        val pick = Forecast.choose(day, live, saved, savedOn, bundled, bundledRunDate())
        val lastHeld = (live + saved + bundled).maxByOrNull { it.date }?.date
        post(Forecast.title(CITY, day), Forecast.body(pick, day, lastHeld))
        return Result.success()
    }

    // ------------------------------------------------------------------ sources

    private fun fetchLive(): List<DayHigh> {
        val url = URL(
            "https://api.open-meteo.com/v1/forecast?latitude=$LAT&longitude=$LON" +
                "&daily=temperature_2m_max,temperature_2m_min,weather_code" +
                "&forecast_days=3&timezone=Asia%2FKolkata"
        )
        val conn = (url.openConnection() as HttpURLConnection).apply {
            connectTimeout = 15_000
            readTimeout = 15_000
        }
        val text = try {
            if (conn.responseCode != 200) return emptyList()
            conn.inputStream.bufferedReader().use { it.readText() }
        } finally {
            conn.disconnect()
        }
        val daily = JSONObject(text).optJSONObject("daily") ?: return emptyList()
        val dates = daily.optJSONArray("time") ?: return emptyList()
        val max = daily.optJSONArray("temperature_2m_max")
        val min = daily.optJSONArray("temperature_2m_min")
        val code = daily.optJSONArray("weather_code")
        return (0 until dates.length()).mapNotNull { i ->
            val high = max?.optDouble(i) ?: return@mapNotNull null
            if (high.isNaN()) return@mapNotNull null
            DayHigh(
                date = dates.optString(i),
                high = high,
                low = min?.optDouble(i)?.takeIf { !it.isNaN() },
                code = code?.optInt(i, -1)?.takeIf { it >= 0 }
            )
        }
    }

    /** The model run bundled with the app: our own next-day numbers, no network needed. */
    private fun readBundled(): List<DayHigh> = try {
        val root = JSONObject(bundledText())
        val cities = root.getJSONArray("cities")
        var out = emptyList<DayHigh>()
        for (i in 0 until cities.length()) {
            val c = cities.getJSONObject(i)
            if (c.optString("city") == CITY) {
                val days = c.optJSONArray("days") ?: JSONArray()
                out = (0 until days.length()).map { j ->
                    val d = days.getJSONObject(j)
                    DayHigh(d.optString("date"), d.optDouble("ours"))
                }
                break
            }
        }
        out
    } catch (e: Exception) {
        emptyList()
    }

    private fun bundledRunDate(): String? = try {
        JSONObject(bundledText()).optString("for_date").takeIf { it.isNotEmpty() }
    } catch (e: Exception) {
        null
    }

    private fun bundledText(): String =
        applicationContext.assets.open(BUNDLED).bufferedReader().use { it.readText() }

    // ------------------------------------------------------------------ storage

    private fun encode(days: List<DayHigh>): String {
        val arr = JSONArray()
        days.forEach { d ->
            arr.put(
                JSONObject()
                    .put("date", d.date)
                    .put("high", d.high)
                    .put("low", d.low ?: JSONObject.NULL)
                    .put("code", d.code ?: JSONObject.NULL)
            )
        }
        return arr.toString()
    }

    private fun decode(text: String?): List<DayHigh> = try {
        if (text == null) emptyList() else {
            val arr = JSONArray(text)
            (0 until arr.length()).map { i ->
                val o = arr.getJSONObject(i)
                DayHigh(
                    date = o.optString("date"),
                    high = o.optDouble("high"),
                    low = if (o.isNull("low")) null else o.optDouble("low"),
                    code = if (o.isNull("code")) null else o.optInt("code")
                )
            }
        }
    } catch (e: Exception) {
        emptyList()
    }

    // ------------------------------------------------------------- notification

    private fun post(title: String, body: String) {
        val ctx = applicationContext
        val manager = ctx.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            manager.createNotificationChannel(
                NotificationChannel(CHANNEL, "Daily forecast", NotificationManager.IMPORTANCE_DEFAULT)
                    .apply { description = "Tomorrow's prediction, once a day." }
            )
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            ContextCompat.checkSelfPermission(ctx, Manifest.permission.POST_NOTIFICATIONS)
            != PackageManager.PERMISSION_GRANTED
        ) return      // not allowed to notify; the app asks on next launch

        val open = PendingIntent.getActivity(
            ctx, 0, Intent(ctx, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        val n = NotificationCompat.Builder(ctx, CHANNEL)
            .setSmallIcon(R.drawable.ic_stat_forecast)
            .setContentTitle(title)
            .setContentText(body)
            .setStyle(NotificationCompat.BigTextStyle().bigText(body))
            .setContentIntent(open)
            .setAutoCancel(true)
            .setPriority(NotificationCompat.PRIORITY_DEFAULT)
            .build()
        try {
            NotificationManagerCompat.from(ctx).notify(NOTE_ID, n)
        } catch (e: SecurityException) {
            // permission revoked between the check and here
        }
    }

    companion object {
        const val CITY = "Mumbai"
        private const val LAT = "19.076"
        private const val LON = "72.877"
        private const val BUNDLED = "site/assets/forecast.json"
        private const val CHANNEL = "daily-forecast"
        private const val PREFS = "forecast"
        private const val KEY_DAYS = "days"
        private const val KEY_SAVED_ON = "saved_on"
        private const val NOTE_ID = 1
        private const val DAILY = "daily-forecast"
        private const val ONCE = "forecast-now"

        /** The hour the notification lands, local time. */
        const val HOUR = 7

        /** Runs every day at [HOUR], online or not, and survives reboot through WorkManager. */
        fun schedule(ctx: Context) {
            val req = PeriodicWorkRequestBuilder<ForecastWorker>(1, TimeUnit.DAYS)
                .setInitialDelay(Forecast.millisUntil(HOUR, Date()), TimeUnit.MILLISECONDS)
                .build()
            WorkManager.getInstance(ctx)
                .enqueueUniquePeriodicWork(DAILY, ExistingPeriodicWorkPolicy.UPDATE, req)
        }

        /** One notification now, so a new install shows what it is about to start doing. */
        fun showOnce(ctx: Context) {
            WorkManager.getInstance(ctx).enqueueUniqueWork(
                ONCE, ExistingWorkPolicy.KEEP, OneTimeWorkRequestBuilder<ForecastWorker>().build()
            )
        }
    }
}
