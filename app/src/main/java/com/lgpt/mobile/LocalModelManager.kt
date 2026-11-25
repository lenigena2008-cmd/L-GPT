package com.lgpt.mobile

import android.content.Context
import android.net.Uri
import android.provider.OpenableColumns
import java.io.File

object LocalModelManager {
    private val EXTENSIONS = setOf("task", "bin", "litertlm")

    /** Dossier des modèles : /sdcard/Android/data/com.lgpt.mobile/files/models (accessible aussi via adb push). */
    fun modelsDir(context: Context): File {
        val base = context.getExternalFilesDir(null) ?: context.filesDir
        return File(base, "models").apply { mkdirs() }
    }

    fun getModels(context: Context): List<File> =
        modelsDir(context).listFiles { f -> f.isFile && f.extension.lowercase() in EXTENSIONS }
            ?.sortedBy { it.name } ?: emptyList()

    fun displayName(context: Context, uri: Uri): String {
        context.contentResolver.query(uri, null, null, null, null)?.use { c ->
            val i = c.getColumnIndex(OpenableColumns.DISPLAY_NAME)
            if (i >= 0 && c.moveToFirst()) return c.getString(i)
        }
        return uri.lastPathSegment ?: "fichier"
    }

    fun importModel(context: Context, uri: Uri): File {
        val name = displayName(context, uri)
        if (name.substringAfterLast('.', "").lowercase() !in EXTENSIONS) {
            throw IllegalArgumentException("Format non supporté ($name). Utilise un fichier .task, .bin ou .litertlm")
        }
        val target = File(modelsDir(context), name)
        val temp = File(modelsDir(context), "$name.part")
        context.contentResolver.openInputStream(uri)!!.use { input ->
            temp.outputStream().use { output ->
                val buffer = ByteArray(1024 * 1024)
                while (true) {
                    val n = input.read(buffer)
                    if (n <= 0) break
                    output.write(buffer, 0, n)
                }
            }
        }
        if (target.exists()) target.delete()
        temp.renameTo(target)
        return target
    }

    fun deleteModel(file: File): Boolean = file.delete()
}
