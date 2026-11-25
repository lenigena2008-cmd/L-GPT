package com.lgpt.mobile

import android.content.Context
import android.net.Uri
import com.tom_roush.pdfbox.android.PDFBoxResourceLoader
import com.tom_roush.pdfbox.pdmodel.PDDocument
import com.tom_roush.pdfbox.text.PDFTextStripper
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.util.concurrent.CopyOnWriteArrayList

/** Base documentaire locale : extrait le texte des PDF et retrouve les passages utiles à une question. */
object DocumentStore {
    private data class Chunk(val doc: String, val text: String)

    private val chunks = CopyOnWriteArrayList<Chunk>()
    private var ready = false

    private fun dir(context: Context) = File(context.filesDir, "docs").apply { mkdirs() }
    private fun safe(name: String) = name.removeSuffix(".pdf").replace(Regex("[\\\\/:*?\"<>|]"), "_")
    private fun split(doc: String, text: String) =
        text.replace(Regex("\\s+"), " ").trim().chunked(900).map { Chunk(doc, it) }

    fun init(context: Context) {
        if (ready) return
        PDFBoxResourceLoader.init(context.applicationContext)
        dir(context).listFiles()?.filter { it.extension == "txt" }?.forEach {
            chunks.addAll(split(it.nameWithoutExtension, it.readText()))
        }
        ready = true
    }

    fun names(): List<String> = chunks.map { it.doc }.distinct()

    suspend fun addPdf(context: Context, uri: Uri, displayName: String): Int = withContext(Dispatchers.IO) {
        init(context)
        val text = context.contentResolver.openInputStream(uri)!!.use { stream ->
            PDDocument.load(stream).use { PDFTextStripper().getText(it) }
        }
        require(text.isNotBlank()) { "Aucun texte trouvé dans ce PDF (document scanné ?)" }
        val name = safe(displayName)
        File(dir(context), "$name.txt").writeText(text)
        chunks.removeAll { it.doc == name }
        val parts = split(name, text)
        chunks.addAll(parts)
        parts.size
    }

    fun remove(context: Context, name: String) {
        val base = safe(name)
        chunks.removeAll { it.doc == base }
        File(dir(context), "$base.txt").delete()
    }

    fun relevantContext(query: String, maxChars: Int = 2400): String {
        if (chunks.isEmpty()) return ""
        val words = Regex("[\\p{L}\\p{N}]{4,}").findAll(query.lowercase()).map { it.value }.toSet()
        if (words.isEmpty()) return ""
        return chunks
            .map { c -> c to words.count { c.text.lowercase().contains(it) } }
            .filter { it.second > 0 }
            .sortedByDescending { it.second }
            .take(3)
            .joinToString("\n---\n") { "[${it.first.doc}] ${it.first.text}" }
            .take(maxChars)
    }
}
