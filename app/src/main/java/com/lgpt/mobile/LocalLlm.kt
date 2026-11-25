package com.lgpt.mobile

import android.content.Context
import com.google.mediapipe.tasks.genai.llminference.LlmInference
import com.google.mediapipe.tasks.genai.llminference.LlmInferenceSession
import com.google.mediapipe.tasks.genai.llminference.LlmInferenceSession.LlmInferenceSessionOptions
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import kotlinx.coroutines.flow.flowOn
import kotlinx.coroutines.withContext
import java.io.File

/** Moteur d'IA qui tourne directement sur le téléphone (MediaPipe LLM Inference). */
object LocalLlm {
    private var llm: LlmInference? = null
    private var loadedPath: String? = null

    const val SYSTEM_PROMPT =
        "Tu es L-GPT, un assistant intelligent qui tourne localement. Réponds en français, de façon claire et utile."

    fun isLoaded(file: File) = llm != null && loadedPath == file.absolutePath

    suspend fun load(context: Context, modelFile: File, maxTokens: Int = 3072) =
        withContext(Dispatchers.IO) {
            if (isLoaded(modelFile)) return@withContext
            close()
            val options = LlmInference.LlmInferenceOptions.builder()
                .setModelPath(modelFile.absolutePath)
                .setMaxTokens(maxTokens)
                .build()
            llm = LlmInference.createFromOptions(context.applicationContext, options)
            loadedPath = modelFile.absolutePath
        }

    fun close() {
        runCatching { llm?.close() }
        llm = null
        loadedPath = null
    }

    /** history : liste (estUtilisateur, texte), le dernier élément est la question en cours. */
    fun generate(modelName: String, history: List<Pair<Boolean, String>>): Flow<String> = callbackFlow {
        val engine = llm ?: throw IllegalStateException("Modèle non chargé")
        val session = LlmInferenceSession.createFromOptions(
            engine,
            LlmInferenceSessionOptions.builder()
                .setTopK(40)
                .setTopP(0.95f)
                .setTemperature(0.7f)
                .build()
        )
        session.addQueryChunk(buildPrompt(modelName, history))
        session.generateResponseAsync { partial, done ->
            trySend(partial ?: "")
            if (done) close()
        }
        awaitClose {
            runCatching { session.cancelGenerateResponseAsync() }
            runCatching { session.close() }
        }
    }.flowOn(Dispatchers.Default)

    private fun buildPrompt(modelName: String, history: List<Pair<Boolean, String>>): String {
        // On garde les derniers échanges qui tiennent dans le budget de contexte (~5500 caractères).
        val kept = ArrayDeque<Pair<Boolean, String>>()
        var budget = 5500
        for (turn in history.asReversed()) {
            if (kept.isNotEmpty() && budget - turn.second.length < 0) break
            kept.addFirst(turn)
            budget -= turn.second.length
        }
        val chatMl = modelName.lowercase().contains("qwen")
        val sb = StringBuilder()
        if (chatMl) {
            sb.append("<|im_start|>system\n$SYSTEM_PROMPT<|im_end|>\n")
            kept.forEach { (isUser, text) ->
                sb.append("<|im_start|>${if (isUser) "user" else "assistant"}\n$text<|im_end|>\n")
            }
            sb.append("<|im_start|>assistant\n")
        } else { // format Gemma
            kept.forEachIndexed { i, (isUser, text) ->
                sb.append("<start_of_turn>${if (isUser) "user" else "model"}\n")
                if (i == 0 && isUser) sb.append("$SYSTEM_PROMPT\n\n")
                sb.append("$text<end_of_turn>\n")
            }
            sb.append("<start_of_turn>model\n")
        }
        return sb.toString()
    }
}
