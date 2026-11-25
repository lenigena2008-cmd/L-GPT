package com.lgpt.mobile

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.flowOn
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

/** Client Ollama. Par câble USB : adresse http://127.0.0.1:11434 grâce à « adb reverse ». */
object OllamaClient {
    const val USB_ADDRESS = "http://127.0.0.1:11434"

    private fun base(address: String): String {
        var s = address.trim().trimEnd('/')
        if (!s.startsWith("http")) s = "http://$s"
        return s
    }

    suspend fun getModels(address: String): Result<List<String>> = withContext(Dispatchers.IO) {
        runCatching {
            val c = URL("${base(address)}/api/tags").openConnection() as HttpURLConnection
            c.connectTimeout = 4000
            c.readTimeout = 8000
            try {
                if (c.responseCode != 200) error("HTTP ${c.responseCode}")
                val arr = JSONObject(c.inputStream.bufferedReader().readText()).getJSONArray("models")
                List(arr.length()) { arr.getJSONObject(it).getString("name") }
            } finally {
                c.disconnect()
            }
        }.recoverCatching {
            throw Exception("PC injoignable. Câble branché, débogage USB activé et connect_pc.bat lancé ?")
        }
    }

    fun chatStream(
        address: String,
        model: String,
        history: List<Pair<Boolean, String>>
    ): Flow<String> = flow {
        val c = URL("${base(address)}/api/chat").openConnection() as HttpURLConnection
        c.requestMethod = "POST"
        c.connectTimeout = 5000
        c.readTimeout = 300_000
        c.doOutput = true
        c.setRequestProperty("Content-Type", "application/json")
        try {
            val messages = JSONArray().put(
                JSONObject().put("role", "system").put("content", LocalLlm.SYSTEM_PROMPT)
            )
            history.forEach { (isUser, text) ->
                messages.put(
                    JSONObject().put("role", if (isUser) "user" else "assistant").put("content", text)
                )
            }
            val body = JSONObject().put("model", model).put("stream", true).put("messages", messages)
            c.outputStream.use { it.write(body.toString().toByteArray()) }

            if (c.responseCode != 200) {
                val err = c.errorStream?.bufferedReader()?.readText().orEmpty()
                throw Exception("Ollama : HTTP ${c.responseCode} $err")
            }
            val reader = c.inputStream.bufferedReader()
            while (true) {
                val line = reader.readLine() ?: break
                if (line.isBlank()) continue
                val obj = JSONObject(line)
                if (obj.has("error")) throw Exception(obj.getString("error"))
                val piece = obj.optJSONObject("message")?.optString("content").orEmpty()
                if (piece.isNotEmpty()) emit(piece)
                if (obj.optBoolean("done", false)) break
            }
        } finally {
            c.disconnect()
        }
    }.flowOn(Dispatchers.IO)
}
