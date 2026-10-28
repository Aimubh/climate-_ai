package com.example.myapplication

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.Calendar
import java.util.Date

/**
 * The notification's one job is to be right about where its number came from.
 * These cover the fallback order and the refusal to pass stale figures off as live.
 */
class ForecastTest {

    private val live = listOf(DayHigh("2026-10-29", 33.0, 26.0, 61))
    private val saved = listOf(DayHigh("2026-10-29", 34.0, 27.0, 2))
    private val bundled = listOf(
        DayHigh("2026-10-29", 35.1),
        DayHigh("2026-11-02", 32.2)
    )

    private fun at(y: Int, m: Int, d: Int, h: Int = 12, min: Int = 0): Date {
        val c = Calendar.getInstance()
        c.set(y, m - 1, d, h, min, 0)
        c.set(Calendar.MILLISECOND, 0)
        return c.time
    }

    @Test
    fun `live beats everything`() {
        val p = Forecast.choose("2026-10-29", live, saved, "2026-10-28", bundled, "2026-10-27")!!
        assertEquals(Origin.LIVE, p.origin)
        assertEquals(33.0, p.day.high, 0.001)
    }

    @Test
    fun `falls back to the last fetch when offline`() {
        val p = Forecast.choose(
            "2026-10-29", emptyList(), saved, "2026-10-28", bundled, "2026-10-27"
        )!!
        assertEquals(Origin.SAVED, p.origin)
        assertEquals(34.0, p.day.high, 0.001)
        assertTrue(Forecast.body(p, "2026-10-29", null).contains("offline now"))
    }

    @Test
    fun `falls back to the bundled run with nothing saved`() {
        val p = Forecast.choose(
            "2026-10-29", emptyList(), emptyList(), null, bundled, "2026-10-27"
        )!!
        assertEquals(Origin.BUNDLED, p.origin)
        assertEquals(35.1, p.day.high, 0.001)
        val body = Forecast.body(p, "2026-10-29", "2026-11-02")
        assertTrue(body.contains("model run of Tue 27 Oct"))
        assertTrue(body.contains("offline"))
    }

    /** The one thing it must never do: hand back a day that is not the day asked for. */
    @Test
    fun `never stretches a run past its last day`() {
        assertNull(
            Forecast.choose("2026-11-09", emptyList(), emptyList(), null, bundled, "2026-10-27")
        )
        val body = Forecast.body(null, "2026-11-09", "2026-11-02")
        assertTrue(body.contains("No forecast"))
        assertTrue(body.contains("Mon 2 Nov"))
    }

    @Test
    fun `body never calls a saved figure live`() {
        for (origin in listOf(Origin.SAVED, Origin.BUNDLED)) {
            val p = Pick(DayHigh("2026-10-29", 30.0), origin, "2026-10-27")
            assertTrue(!Forecast.body(p, "2026-10-29", null).contains("live"))
        }
    }

    @Test
    fun `body reads as a forecast`() {
        val p = Pick(DayHigh("2026-10-29", 33.4, 26.2, 61), Origin.LIVE, null)
        assertEquals("33° / 26°, rain · live feed", Forecast.body(p, "2026-10-29", null))
        assertEquals("Mumbai, Thu 29 Oct", Forecast.title("Mumbai", "2026-10-29"))
    }

    @Test
    fun `tomorrow is the next day`() {
        assertEquals("2026-10-29", Forecast.tomorrow(at(2026, 10, 28)))
        assertEquals("2026-11-01", Forecast.tomorrow(at(2026, 10, 31, 23, 59)))  // month end
        assertEquals("2027-01-01", Forecast.tomorrow(at(2026, 12, 31)))          // year end
    }

    @Test
    fun `the daily alarm lands on the next seven o'clock`() {
        assertEquals(60 * 60 * 1000L, Forecast.millisUntil(7, at(2026, 10, 28, 6, 0)))
        assertEquals(23 * 60 * 60 * 1000L, Forecast.millisUntil(7, at(2026, 10, 28, 8, 0)))
        // exactly 7:00 means the next one, never a zero delay that fires twice
        assertEquals(24 * 60 * 60 * 1000L, Forecast.millisUntil(7, at(2026, 10, 28, 7, 0)))
    }
}
