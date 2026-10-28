package com.example.myapplication

import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Date
import java.util.Locale

/**
 * Picking what tomorrow's notification should say, and saying it honestly.
 *
 * Deliberately free of Android imports so it runs in a plain JVM test: everything that
 * touches the network, storage or the notification tray lives in ForecastWorker.
 */

/** One day's figures, whatever their origin. */
data class DayHigh(
    val date: String,            // yyyy-MM-dd
    val high: Double,
    val low: Double? = null,
    val code: Int? = null        // WMO weather code, when the source carries one
)

/** Where a figure came from. Live is freshest; bundled is the shipped model run. */
enum class Origin { LIVE, SAVED, BUNDLED }

/** A figure plus the provenance the notification has to admit to. */
data class Pick(val day: DayHigh, val origin: Origin, val asOf: String?)

object Forecast {

    private fun iso() = SimpleDateFormat("yyyy-MM-dd", Locale.US)

    fun isoDay(d: Date): String = iso().format(d)

    fun tomorrow(now: Date): String {
        val c = Calendar.getInstance()
        c.time = now
        c.add(Calendar.DAY_OF_YEAR, 1)
        return isoDay(c.time)
    }

    /** "2026-10-29" -> "Thu 29 Oct"; anything unparseable comes back unchanged. */
    fun pretty(isoDate: String): String = try {
        SimpleDateFormat("EEE d MMM", Locale.US).format(iso().parse(isoDate)!!)
    } catch (e: Exception) {
        isoDate
    }

    /**
     * The freshest source that actually covers [day].
     *
     * A source that does not reach [day] is skipped, never stretched: an old run's last day
     * is not tomorrow's weather, and quoting it as such is the one thing this must not do.
     * Returns null when nothing covers [day], which the caller reports as a gap.
     */
    fun choose(
        day: String,
        live: List<DayHigh>,
        saved: List<DayHigh>,
        savedAsOf: String?,
        bundled: List<DayHigh>,
        runDate: String?
    ): Pick? {
        live.firstOrNull { it.date == day }?.let { return Pick(it, Origin.LIVE, null) }
        saved.firstOrNull { it.date == day }?.let { return Pick(it, Origin.SAVED, savedAsOf) }
        bundled.firstOrNull { it.date == day }?.let { return Pick(it, Origin.BUNDLED, runDate) }
        return null
    }

    /** WMO weather code to something a person reads at a glance. */
    fun spell(code: Int?): String = when (code) {
        null -> ""
        0 -> "clear"
        1 -> "mostly clear"
        2 -> "partly cloudy"
        3 -> "overcast"
        45, 48 -> "fog"
        51, 53, 55 -> "drizzle"
        56, 57 -> "freezing drizzle"
        61, 63 -> "rain"
        65 -> "heavy rain"
        66, 67 -> "freezing rain"
        71, 73, 75, 77 -> "snow"
        80, 81 -> "showers"
        82 -> "heavy showers"
        85, 86 -> "snow showers"
        95 -> "thunderstorms"
        96, 99 -> "thunderstorms with hail"
        else -> ""
    }

    private fun deg(v: Double) = "${Math.round(v)}°"

    fun title(city: String, day: String): String = "$city, ${pretty(day)}"

    /**
     * The body line. Every variant names where the number came from, because a saved figure
     * read as a live one is worse than no notification at all.
     */
    fun body(pick: Pick?, day: String, lastHeld: String?): String {
        if (pick == null) {
            val tail = if (lastHeld == null) "Open the app once online to fetch one."
            else "What we hold runs out on ${pretty(lastHeld)}. Open the app once online to refresh."
            return "No forecast for ${pretty(day)} yet. $tail"
        }
        val d = pick.day
        val range = if (d.low != null) "${deg(d.high)} / ${deg(d.low)}" else "high ${deg(d.high)}"
        val sky = spell(d.code).let { if (it.isEmpty()) "" else ", $it" }
        val where = when (pick.origin) {
            Origin.LIVE -> "live feed"
            Origin.SAVED -> "saved ${pick.asOf?.let { pretty(it) } ?: "earlier"}, offline now"
            Origin.BUNDLED -> "our model run of ${pick.asOf?.let { pretty(it) } ?: "record"}, offline"
        }
        return "$range$sky · $where"
    }

    /** Milliseconds from [now] to the next [hour] o'clock, local time. */
    fun millisUntil(hour: Int, now: Date): Long {
        val c = Calendar.getInstance()
        c.time = now
        c.set(Calendar.HOUR_OF_DAY, hour)
        c.set(Calendar.MINUTE, 0)
        c.set(Calendar.SECOND, 0)
        c.set(Calendar.MILLISECOND, 0)
        if (!c.time.after(now)) c.add(Calendar.DAY_OF_YEAR, 1)
        return c.timeInMillis - now.time
    }
}
