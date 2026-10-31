package com.example.myapplication

import android.content.res.AssetManager
import java.io.Closeable
import java.io.IOException
import java.net.InetAddress
import java.net.ServerSocket
import java.net.Socket
import java.util.concurrent.Executors

/**
 * Serves the bundled site over http on the loopback interface.
 * The page is served from a loopback origin so fetch() and the chat bot's streaming
 * response behave as they would on the web; a file:// page gets neither. Only the
 * read-only assets that ship inside the APK are served.
 */
class AssetServer(private val assets: AssetManager, private val root: String) : Closeable {

    private val socket = ServerSocket(0, 8, InetAddress.getByName("127.0.0.1"))
    private val pool = Executors.newCachedThreadPool()

    val port: Int get() = socket.localPort

    fun start() = apply {
        pool.execute {
            while (!socket.isClosed) {
                val client = try { socket.accept() } catch (e: IOException) { return@execute }
                pool.execute { serve(client) }
            }
        }
    }

    private fun serve(client: Socket) = client.use {
        val request = it.getInputStream().bufferedReader().readLine() ?: return
        // "GET /assets/forecast.json HTTP/1.1"
        val path = request.split(' ').getOrNull(1)
            ?.substringBefore('?')?.substringBefore('#')?.trimStart('/')
            ?.ifEmpty { "index.html" } ?: return
        val out = it.getOutputStream()
        val body = try {
            if (path.contains("..")) null else assets.open("$root/$path").readBytes().let {
                // The OpenRouter key is not in the page source; it is put in as the page is served.
                if (path.endsWith(".html"))
                    it.toString(Charsets.UTF_8)
                        .replace("__OPENROUTER_KEY__", BuildConfig.OPENROUTER_KEY)
                        .toByteArray()
                else it
            }
        } catch (e: IOException) {
            null
        }
        if (body == null) {
            out.write("HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\nConnection: close\r\n\r\n".toByteArray())
            return
        }
        out.write(
            ("HTTP/1.1 200 OK\r\nContent-Type: ${mime(path)}\r\nContent-Length: ${body.size}\r\n" +
                "Cache-Control: no-store\r\nConnection: close\r\n\r\n").toByteArray()
        )
        out.write(body)
        out.flush()
    }

    private fun mime(path: String) = when {
        path.endsWith(".html") -> "text/html; charset=utf-8"
        path.endsWith(".json") -> "application/json; charset=utf-8"
        path.endsWith(".css") -> "text/css; charset=utf-8"
        path.endsWith(".js") -> "text/javascript; charset=utf-8"
        else -> "application/octet-stream"
    }

    override fun close() {
        socket.close()
        pool.shutdownNow()
    }
}
