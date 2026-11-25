package com.lgpt.mobile

import android.content.SharedPreferences
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val prefs = getSharedPreferences("lgpt_settings", MODE_PRIVATE)
        setContent { LgptApp(prefs) }
    }
}

@Composable
fun LgptApp(prefs: SharedPreferences) {
    val scope = rememberCoroutineScope()
    val context = LocalContext.current

    var localModels by remember { mutableStateOf(listOf<File>()) }
    var selectedLocalModel by remember { mutableStateOf(prefs.getString("selected_local_model", "") ?: "") }
    var localModelStatus by remember { mutableStateOf("Aucun modèle détecté.") }
    var isImportingLocalModel by remember { mutableStateOf(false) }

    var currentScreen by remember { mutableStateOf(AppScreen.CHAT) }
    var selectedEngine by remember {
        // Par défaut : le téléphone fait tourner l'IA
        mutableStateOf(if (prefs.getString("engine", "PHONE") == "PC") AiEngine.PC else AiEngine.PHONE)
    }
    var serverAddress by remember {
        val saved = prefs.getString("server_address", null)
        mutableStateOf(if (saved.isNullOrBlank() || saved.contains("XXX") || saved.contains("192.168")) OllamaClient.USB_ADDRESS else saved)
    }
    var autoReconnect by remember { mutableStateOf(prefs.getBoolean("auto_reconnect", true)) }
    var connectionStatus by remember { mutableStateOf("Non connecté") }
    var isConnecting by remember { mutableStateOf(false) }
    var isGenerating by remember { mutableStateOf(false) }
    var models by remember { mutableStateOf(listOf<String>()) }
    var selectedModel by remember { mutableStateOf(prefs.getString("selected_model", "") ?: "") }
    var modelMenuExpanded by remember { mutableStateOf(false) }
    var messageInput by remember { mutableStateOf("") }
    var drawerOpen by remember { mutableStateOf(false) }
    var selectedPdf by remember { mutableStateOf<String?>(null) }
    var selectedImage by remember { mutableStateOf<String?>(null) }
    var documents by remember { mutableStateOf(listOf<String>()) }
    var documentStatus by remember { mutableStateOf("") }
    val messages = remember { mutableStateListOf<ChatMessage>() }

    val drawerState = rememberDrawerState(DrawerValue.Closed)
    LaunchedEffect(drawerOpen) { if (drawerOpen) drawerState.open() else drawerState.close() }
    LaunchedEffect(drawerState.currentValue) { drawerOpen = drawerState.currentValue == DrawerValue.Open }

    fun detectPcModels() {
        isConnecting = true
        connectionStatus = "Recherche des modèles..."
        scope.launch {
            OllamaClient.getModels(serverAddress)
                .onSuccess { detected ->
                    models = detected
                    connectionStatus = if (detected.isNotEmpty()) "Connexion réussie" else "Aucun modèle trouvé"
                    if (selectedModel !in detected) {
                        selectedModel = detected.firstOrNull() ?: ""
                        prefs.edit().putString("selected_model", selectedModel).apply()
                    }
                }
                .onFailure { connectionStatus = "Échec : ${it.message}" }
            isConnecting = false
        }
    }

    // Au démarrage : modèles du téléphone, documents, reconnexion USB automatique
    LaunchedEffect(Unit) {
        withContext(Dispatchers.IO) { DocumentStore.init(context) }
        documents = DocumentStore.names()
        localModels = withContext(Dispatchers.IO) { LocalModelManager.getModels(context) }
        if (localModels.isNotEmpty()) {
            if (selectedLocalModel !in localModels.map { it.name }) {
                selectedLocalModel = localModels.first().name
                prefs.edit().putString("selected_local_model", selectedLocalModel).apply()
            }
            localModelStatus = "${localModels.size} modèle(s) détecté(s)."
        }
        if (autoReconnect && selectedEngine == AiEngine.PC) detectPcModels()
    }

    val pdfPicker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) {
            val name = LocalModelManager.displayName(context, uri)
            documentStatus = "Lecture de $name..."
            scope.launch {
                try {
                    val n = DocumentStore.addPdf(context, uri, name)
                    selectedPdf = name
                    documents = DocumentStore.names()
                    documentStatus = "$name ajouté ($n passages)."
                } catch (e: Exception) {
                    documentStatus = "Erreur : ${e.message}"
                }
            }
        }
    }

    val imagePicker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) selectedImage = uri.lastPathSegment ?: "Image"
    }

    val localModelPicker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) {
            scope.launch {
                isImportingLocalModel = true
                localModelStatus = "Importation du modèle en cours (peut prendre quelques minutes)..."
                try {
                    val imported = withContext(Dispatchers.IO) { LocalModelManager.importModel(context, uri) }
                    localModels = withContext(Dispatchers.IO) { LocalModelManager.getModels(context) }
                    selectedLocalModel = imported.name
                    prefs.edit().putString("selected_local_model", imported.name).apply()
                    localModelStatus = "Modèle importé avec succès."
                } catch (e: Exception) {
                    localModelStatus = "Erreur : ${e.message ?: "Importation impossible"}"
                } finally {
                    isImportingLocalModel = false
                }
            }
        }
    }

    fun send() {
        val prompt = messageInput.trim()
        if (prompt.isEmpty() || isGenerating) return

        val localFile = localModels.firstOrNull { it.name == selectedLocalModel }
        if (selectedEngine == AiEngine.PHONE && localFile == null) {
            messages.add(ChatMessage(prompt, true))
            messages.add(ChatMessage("⚠ Aucun modèle sur le téléphone. Importe un fichier .task dans les paramètres.", false))
            messageInput = ""
            return
        }
        if (selectedEngine == AiEngine.PC && selectedModel.isEmpty()) {
            messages.add(ChatMessage(prompt, true))
            messages.add(ChatMessage("⚠ Aucun modèle PC sélectionné. Configure-le dans les paramètres.", false))
            messageInput = ""
            return
        }

        val docContext = DocumentStore.relevantContext(prompt)
        val modelPrompt =
            if (docContext.isBlank()) prompt else "Extraits de mes documents :\n$docContext\n\nQuestion : $prompt"
        val history = messages.filter { it.text.isNotBlank() && !it.text.startsWith("⚠") }
            .map { it.isUser to it.text } + (true to modelPrompt)

        messages.add(ChatMessage(prompt, true))
        messages.add(ChatMessage("", false))
        val idx = messages.lastIndex
        messageInput = ""
        isGenerating = true

        scope.launch {
            try {
                val stream = if (selectedEngine == AiEngine.PHONE) {
                    if (!LocalLlm.isLoaded(localFile!!)) {
                        messages[idx] = ChatMessage("Chargement du modèle...", false)
                        LocalLlm.load(context, localFile)
                        messages[idx] = ChatMessage("", false)
                    }
                    LocalLlm.generate(localFile.name, history)
                } else {
                    OllamaClient.chatStream(serverAddress, selectedModel, history)
                }
                stream.collect { piece ->
                    messages[idx] = messages[idx].copy(text = messages[idx].text + piece)
                }
            } catch (e: Exception) {
                messages[idx] = ChatMessage("⚠ Erreur : ${e.message}", false)
            } finally {
                isGenerating = false
            }
        }
    }

    MaterialTheme(
        colorScheme = darkColorScheme(
            primary = Violet, background = Background, surface = Panel,
            onPrimary = Color.White, onBackground = TextMain, onSurface = TextMain
        )
    ) {
        ModalNavigationDrawer(
            drawerState = drawerState,
            drawerContent = {
                DrawerContent(
                    onNewChat = { messages.clear(); currentScreen = AppScreen.CHAT; drawerOpen = false },
                    onChat = { currentScreen = AppScreen.CHAT; drawerOpen = false },
                    onSettings = { currentScreen = AppScreen.SETTINGS; drawerOpen = false },
                    onDocuments = { currentScreen = AppScreen.DOCUMENTS; drawerOpen = false }
                )
            },
            gesturesEnabled = true
        ) {
            Column(modifier = Modifier.fillMaxSize().background(Background).statusBarsPadding().navigationBarsPadding().imePadding()) {
                TopBar(onMenuClick = { drawerOpen = true }, currentScreen = currentScreen, selectedEngine = selectedEngine)

                when (currentScreen) {
                    AppScreen.CHAT -> ChatScreen(
                        messages = messages,
                        messageInput = messageInput,
                        onMessageChange = { messageInput = it },
                        isGenerating = isGenerating,
                        selectedPdf = selectedPdf,
                        selectedImage = selectedImage,
                        onRemovePdf = {
                            selectedPdf?.let { DocumentStore.remove(context, it) }
                            selectedPdf = null
                            documents = DocumentStore.names()
                        },
                        onRemoveImage = { selectedImage = null },
                        onAddPdf = { pdfPicker.launch(arrayOf("application/pdf")) },
                        onAddImage = { imagePicker.launch(arrayOf("image/*")) },
                        onSend = { send() }
                    )

                    AppScreen.SETTINGS -> SettingsScreen(
                        selectedEngine = selectedEngine,
                        onEngineChange = {
                            selectedEngine = it
                            prefs.edit().putString("engine", it.name).apply()
                            if (it == AiEngine.PC && autoReconnect) detectPcModels()
                        },
                        serverAddress = serverAddress,
                        onAddressChange = { serverAddress = it; prefs.edit().putString("server_address", it).apply() },
                        connectionStatus = connectionStatus,
                        autoReconnect = autoReconnect,
                        onAutoReconnectChange = { autoReconnect = it; prefs.edit().putBoolean("auto_reconnect", it).apply() },
                        isConnecting = isConnecting,
                        models = models,
                        selectedModel = selectedModel,
                        onModelSelect = { selectedModel = it; prefs.edit().putString("selected_model", it).apply() },
                        modelMenuExpanded = modelMenuExpanded,
                        onModelMenuChange = { modelMenuExpanded = it },
                        onDetectModels = { detectPcModels() },
                        localModels = localModels,
                        selectedLocalModel = selectedLocalModel,
                        localModelStatus = localModelStatus,
                        isImportingLocalModel = isImportingLocalModel,
                        onImportLocalModel = { localModelPicker.launch(arrayOf("*/*")) },
                        onDetectLocalModels = {
                            scope.launch {
                                localModels = withContext(Dispatchers.IO) { LocalModelManager.getModels(context) }
                                localModelStatus = if (localModels.isEmpty()) "Aucun modèle trouvé." else "${localModels.size} modèle(s) détecté(s)."
                                if (selectedLocalModel !in localModels.map { it.name }) {
                                    selectedLocalModel = localModels.firstOrNull()?.name ?: ""
                                    prefs.edit().putString("selected_local_model", selectedLocalModel).apply()
                                }
                            }
                        },
                        onLocalModelSelect = { selectedLocalModel = it; prefs.edit().putString("selected_local_model", it).apply() },
                        onDeleteLocalModel = { file ->
                            scope.launch {
                                if (LocalLlm.isLoaded(file)) LocalLlm.close()
                                val deleted = withContext(Dispatchers.IO) { LocalModelManager.deleteModel(file) }
                                if (deleted) {
                                    localModels = withContext(Dispatchers.IO) { LocalModelManager.getModels(context) }
                                    if (selectedLocalModel == file.name) {
                                        selectedLocalModel = ""
                                        prefs.edit().remove("selected_local_model").apply()
                                    }
                                    localModelStatus = "Modèle supprimé."
                                } else localModelStatus = "Impossible de supprimer ce modèle."
                            }
                        }
                    )

                    AppScreen.DOCUMENTS -> DocumentsScreen(
                        documents = documents,
                        status = documentStatus,
                        onImportPdf = { pdfPicker.launch(arrayOf("application/pdf")) },
                        onDelete = { name ->
                            DocumentStore.remove(context, name)
                            documents = DocumentStore.names()
                            if (selectedPdf == name) selectedPdf = null
                        }
                    )
                }
            }
        }
    }
}

@Composable
fun SettingsScreen(
    selectedEngine: AiEngine,
    onEngineChange: (AiEngine) -> Unit,
    serverAddress: String,
    onAddressChange: (String) -> Unit,
    connectionStatus: String,
    autoReconnect: Boolean,
    onAutoReconnectChange: (Boolean) -> Unit,
    isConnecting: Boolean,
    models: List<String>,
    selectedModel: String,
    onModelSelect: (String) -> Unit,
    modelMenuExpanded: Boolean,
    onModelMenuChange: (Boolean) -> Unit,
    onDetectModels: () -> Unit,
    localModels: List<File>,
    selectedLocalModel: String,
    localModelStatus: String,
    isImportingLocalModel: Boolean,
    onImportLocalModel: () -> Unit,
    onDetectLocalModels: () -> Unit,
    onLocalModelSelect: (String) -> Unit,
    onDeleteLocalModel: (File) -> Unit
) {
    Column(modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(18.dp)) {
        Text("Moteur d'intelligence artificielle", color = TextMain, fontSize = 21.sp, fontWeight = FontWeight.Bold)
        Spacer(modifier = Modifier.height(8.dp))
        Text("Choisis où L-GPT doit exécuter les modèles.", color = TextMuted, fontSize = 13.sp)
        Spacer(modifier = Modifier.height(25.dp))

        EngineCard(
            title = "Moteur du téléphone",
            description = "Le modèle tourne directement sur ton smartphone, même hors ligne.",
            selected = selectedEngine == AiEngine.PHONE,
            onClick = { onEngineChange(AiEngine.PHONE) }
        )
        Spacer(modifier = Modifier.height(12.dp))
        EngineCard(
            title = "Moteur du PC (câble USB)",
            description = "Utilise les modèles Ollama de ton ordinateur, relié par câble USB.",
            selected = selectedEngine == AiEngine.PC,
            onClick = { onEngineChange(AiEngine.PC) }
        )
        Spacer(modifier = Modifier.height(25.dp))

        if (selectedEngine == AiEngine.PHONE) {
            SettingsSection(title = "Modèles du téléphone") {
                Text(
                    "Importe un modèle au format .task (MediaPipe / LiteRT, ex. Gemma 3 1B ou Qwen2.5 1.5B).",
                    color = TextMuted, fontSize = 13.sp
                )
                Spacer(modifier = Modifier.height(12.dp))
                Button(
                    onClick = onImportLocalModel,
                    enabled = !isImportingLocalModel,
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(containerColor = Violet)
                ) { Text(if (isImportingLocalModel) "Importation en cours..." else "＋ Importer un modèle") }
                Spacer(modifier = Modifier.height(8.dp))
                OutlinedButton(onClick = onDetectLocalModels, modifier = Modifier.fillMaxWidth()) {
                    Text("Détecter les modèles")
                }
                Spacer(modifier = Modifier.height(10.dp))
                Text(localModelStatus, color = TextMuted, fontSize = 12.sp)
                Spacer(modifier = Modifier.height(12.dp))
                HorizontalDivider(color = PanelLight)
                Spacer(modifier = Modifier.height(10.dp))

                if (localModels.isEmpty()) {
                    Text("Aucun modèle importé.", color = TextMuted, fontSize = 13.sp)
                } else {
                    localModels.forEach { model ->
                        Row(modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp), verticalAlignment = Alignment.CenterVertically) {
                            RadioButton(
                                selected = selectedLocalModel == model.name,
                                onClick = { onLocalModelSelect(model.name) },
                                colors = RadioButtonDefaults.colors(selectedColor = Violet)
                            )
                            Column(modifier = Modifier.weight(1f)) {
                                Text(model.name, color = TextMain, fontSize = 13.sp)
                                Text(
                                    String.format("%.2f Go", model.length().toDouble() / (1024.0 * 1024.0 * 1024.0)),
                                    color = TextMuted, fontSize = 11.sp
                                )
                            }
                            Text(
                                "×", color = Color(0xFFFF7777), fontSize = 22.sp,
                                modifier = Modifier.clickable { onDeleteLocalModel(model) }.padding(8.dp)
                            )
                        }
                    }
                }
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    "Astuce : pour un gros fichier, envoie-le par câble avec scripts\\push_model.bat, puis touche « Détecter les modèles ».",
                    color = TextMuted, fontSize = 11.sp, lineHeight = 16.sp
                )
            }
        } else {
            SettingsSection(title = "Connexion au PC par câble USB") {
                Text(
                    "1. Active le débogage USB sur le téléphone et branche le câble.\n2. Lance scripts\\connect_pc.bat sur le PC.\n3. Touche « Détecter les modèles ».",
                    color = TextMuted, fontSize = 12.sp, lineHeight = 18.sp
                )
                Spacer(modifier = Modifier.height(12.dp))
                OutlinedTextField(
                    value = serverAddress,
                    onValueChange = onAddressChange,
                    label = { Text("Adresse du serveur Ollama") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true
                )
                Spacer(modifier = Modifier.height(12.dp))
                Button(
                    onClick = onDetectModels,
                    enabled = !isConnecting,
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(containerColor = Violet)
                ) { Text(if (isConnecting) "Recherche en cours..." else "Détecter les modèles") }
                Spacer(modifier = Modifier.height(10.dp))
                Text(
                    connectionStatus,
                    color = if (connectionStatus == "Connexion réussie") Color(0xFF66D9A5) else TextMuted,
                    fontSize = 12.sp
                )
                Spacer(modifier = Modifier.height(15.dp))
                Text("Modèle utilisé", color = TextMain, fontSize = 14.sp)
                Box {
                    OutlinedButton(onClick = { onModelMenuChange(true) }, modifier = Modifier.fillMaxWidth()) {
                        Text(selectedModel.ifEmpty { "Choisir un modèle" })
                    }
                    DropdownMenu(expanded = modelMenuExpanded, onDismissRequest = { onModelMenuChange(false) }) {
                        models.forEach { model ->
                            DropdownMenuItem(
                                text = { Text(model) },
                                onClick = { onModelSelect(model); onModelMenuChange(false) }
                            )
                        }
                    }
                }
                Spacer(modifier = Modifier.height(15.dp))
                HorizontalDivider(color = PanelLight)
                Spacer(modifier = Modifier.height(15.dp))
                Row(modifier = Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text("Reconnexion automatique", color = TextMain, fontSize = 14.sp, fontWeight = FontWeight.SemiBold)
                        Text("Détecter le PC dès l'ouverture de l'app.", color = TextMuted, fontSize = 12.sp)
                    }
                    Switch(
                        checked = autoReconnect,
                        onCheckedChange = onAutoReconnectChange,
                        colors = SwitchDefaults.colors(checkedThumbColor = Color.White, checkedTrackColor = Violet)
                    )
                }
            }
        }
    }
}

@Composable
fun DocumentsScreen(
    documents: List<String>,
    status: String,
    onImportPdf: () -> Unit,
    onDelete: (String) -> Unit
) {
    Column(modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp)) {
        Text("Base documentaire", color = TextMain, fontSize = 23.sp, fontWeight = FontWeight.Bold)
        Spacer(modifier = Modifier.height(8.dp))
        Text(
            "Les PDF importés sont lus sur le téléphone. L-GPT utilise automatiquement les passages utiles pour répondre.",
            color = TextMuted, fontSize = 13.sp, lineHeight = 20.sp
        )
        Spacer(modifier = Modifier.height(25.dp))
        Surface(color = Panel, shape = RoundedCornerShape(18.dp), modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(20.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                Text("▤", color = Violet, fontSize = 40.sp)
                Spacer(modifier = Modifier.height(12.dp))
                Text("Importer un document PDF", color = TextMain, fontWeight = FontWeight.SemiBold)
                Spacer(modifier = Modifier.height(8.dp))
                Text("Ajoute un document à la base de L-GPT.", color = TextMuted, fontSize = 12.sp)
                Spacer(modifier = Modifier.height(18.dp))
                Button(onClick = onImportPdf, colors = ButtonDefaults.buttonColors(containerColor = Violet)) {
                    Text("+ Importer un PDF")
                }
            }
        }
        if (status.isNotEmpty()) {
            Spacer(modifier = Modifier.height(12.dp))
            Text(status, color = TextMuted, fontSize = 12.sp)
        }
        if (documents.isNotEmpty()) {
            Spacer(modifier = Modifier.height(20.dp))
            Text("Documents :", color = TextMuted, fontSize = 12.sp)
            documents.forEach { name ->
                Row(modifier = Modifier.fillMaxWidth().padding(vertical = 6.dp), verticalAlignment = Alignment.CenterVertically) {
                    Text(name, color = TextMain, fontSize = 14.sp, modifier = Modifier.weight(1f))
                    Text(
                        "×", color = Color(0xFFFF7777), fontSize = 22.sp,
                        modifier = Modifier.clickable { onDelete(name) }.padding(8.dp)
                    )
                }
            }
        }
    }
}
