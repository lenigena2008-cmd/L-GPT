package com.lgpt.mobile

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

internal val Background = Color(0xFF10111B)
internal val Panel = Color(0xFF191B29)
internal val PanelLight = Color(0xFF222438)
internal val Violet = Color(0xFF8B70FF)
internal val TextMain = Color(0xFFF3F2FA)
internal val TextMuted = Color(0xFF999BAF)

enum class AiEngine { PHONE, PC }
enum class AppScreen { CHAT, SETTINGS, DOCUMENTS }

data class ChatMessage(val text: String, val isUser: Boolean)

@Composable
fun TopBar(onMenuClick: () -> Unit, currentScreen: AppScreen, selectedEngine: AiEngine) {
    Row(
        modifier = Modifier.fillMaxWidth().background(Panel).padding(horizontal = 18.dp, vertical = 15.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text("☰", fontSize = 25.sp, color = TextMain, modifier = Modifier.clickable { onMenuClick() })
        Spacer(modifier = Modifier.width(18.dp))
        Column(modifier = Modifier.weight(1f)) {
            Text("L-GPT", fontSize = 21.sp, fontWeight = FontWeight.Bold, color = TextMain)
            Text(
                text = when (currentScreen) {
                    AppScreen.CHAT -> "Assistant intelligent"
                    AppScreen.SETTINGS -> "Paramètres"
                    AppScreen.DOCUMENTS -> "Base documentaire"
                },
                fontSize = 11.sp,
                color = TextMuted
            )
        }
        Surface(shape = RoundedCornerShape(20.dp), color = PanelLight) {
            Text(
                text = if (selectedEngine == AiEngine.PHONE) "Téléphone" else "PC (USB)",
                modifier = Modifier.padding(horizontal = 13.dp, vertical = 8.dp),
                color = Violet,
                fontSize = 12.sp,
                fontWeight = FontWeight.SemiBold
            )
        }
    }
}

@Composable
fun DrawerContent(
    onNewChat: () -> Unit,
    onChat: () -> Unit,
    onSettings: () -> Unit,
    onDocuments: () -> Unit
) {
    ModalDrawerSheet(drawerContainerColor = Panel, modifier = Modifier.width(290.dp)) {
        Column(modifier = Modifier.fillMaxSize().padding(18.dp)) {
            Spacer(modifier = Modifier.height(20.dp))
            Text("L-GPT", fontSize = 27.sp, fontWeight = FontWeight.Bold, color = Violet)
            Text("Votre assistant personnel", color = TextMuted, fontSize = 12.sp)
            Spacer(modifier = Modifier.height(30.dp))
            Button(
                onClick = onNewChat,
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(14.dp),
                colors = ButtonDefaults.buttonColors(containerColor = Violet)
            ) { Text("+  Nouvelle discussion") }
            Spacer(modifier = Modifier.height(25.dp))
            DrawerButton("⌂", "Discussion", onChat)
            DrawerButton("▤", "Base documentaire", onDocuments)
            DrawerButton("⚙", "Paramètres", onSettings)
            Spacer(modifier = Modifier.weight(1f))
            HorizontalDivider(color = PanelLight)
            Spacer(modifier = Modifier.height(15.dp))
            Text("L-GPT Mobile", color = TextMuted, fontSize = 12.sp)
            Text("Version 1.0", color = TextMuted, fontSize = 10.sp)
        }
    }
}

@Composable
fun DrawerButton(icon: String, title: String, onClick: () -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth().clickable { onClick() }.padding(vertical = 15.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(icon, color = Violet, fontSize = 20.sp)
        Spacer(modifier = Modifier.width(16.dp))
        Text(title, color = TextMain, fontSize = 15.sp)
    }
}

@Composable
fun ChatScreen(
    messages: List<ChatMessage>,
    messageInput: String,
    onMessageChange: (String) -> Unit,
    isGenerating: Boolean,
    selectedPdf: String?,
    selectedImage: String?,
    onRemovePdf: () -> Unit,
    onRemoveImage: () -> Unit,
    onAddPdf: () -> Unit,
    onAddImage: () -> Unit,
    onSend: () -> Unit
) {
    Column(modifier = Modifier.fillMaxSize()) {
        if (messages.isEmpty()) {
            Column(
                modifier = Modifier.weight(1f).fillMaxWidth().padding(25.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center
            ) {
                Surface(shape = CircleShape, color = PanelLight, modifier = Modifier.size(85.dp)) {
                    Box(contentAlignment = Alignment.Center) { Text("✦", fontSize = 42.sp, color = Violet) }
                }
                Spacer(modifier = Modifier.height(25.dp))
                Text("Comment puis-je t'aider ?", fontSize = 24.sp, fontWeight = FontWeight.Bold, color = TextMain)
                Spacer(modifier = Modifier.height(10.dp))
                Text(
                    "Pose une question, importe un document\nou envoie une image.",
                    color = TextMuted, fontSize = 14.sp, lineHeight = 21.sp
                )
                Spacer(modifier = Modifier.height(35.dp))
                SuggestionCard("Analyser un document", "Importer un PDF et poser des questions")
                SuggestionCard("Comprendre une image", "Demander à l'IA d'analyser une image")
            }
        } else {
            val listState = androidx.compose.foundation.lazy.rememberLazyListState()
            androidx.compose.runtime.LaunchedEffect(messages.size, messages.lastOrNull()?.text?.length) {
                listState.animateScrollToItem(messages.size - 1)
            }
            LazyColumn(
                state = listState,
                modifier = Modifier.weight(1f).fillMaxWidth(),
                contentPadding = PaddingValues(16.dp),
                verticalArrangement = Arrangement.spacedBy(15.dp)
            ) {
                items(messages) { message -> if (message.text.isNotEmpty()) MessageBubble(message) }
                if (isGenerating) {
                    item { Text("L-GPT réfléchit...", color = Violet, fontSize = 13.sp) }
                }
            }
        }

        Column(
            modifier = Modifier.fillMaxWidth().background(Background).padding(horizontal = 12.dp, vertical = 10.dp)
        ) {
            if (selectedPdf != null || selectedImage != null) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    if (selectedPdf != null) AttachmentChip("PDF : $selectedPdf", onRemovePdf)
                    if (selectedImage != null) AttachmentChip("Image : $selectedImage", onRemoveImage)
                }
                Spacer(modifier = Modifier.height(8.dp))
            }
            Surface(shape = RoundedCornerShape(23.dp), color = Panel, modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(10.dp)) {
                    OutlinedTextField(
                        value = messageInput,
                        onValueChange = onMessageChange,
                        modifier = Modifier.fillMaxWidth(),
                        placeholder = { Text("Écris ton message...", color = TextMuted) },
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedBorderColor = Color.Transparent,
                            unfocusedBorderColor = Color.Transparent,
                            focusedTextColor = TextMain,
                            unfocusedTextColor = TextMain,
                            cursorColor = Violet
                        ),
                        minLines = 1,
                        maxLines = 5
                    )
                    Row(modifier = Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                        Text("＋", fontSize = 27.sp, color = Violet, modifier = Modifier.clickable { onAddPdf() })
                        Spacer(modifier = Modifier.width(15.dp))
                        Text("▧", fontSize = 23.sp, color = Violet, modifier = Modifier.clickable { onAddImage() })
                        Spacer(modifier = Modifier.weight(1f))
                        Button(
                            onClick = onSend,
                            enabled = !isGenerating,
                            shape = RoundedCornerShape(13.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = Violet),
                            contentPadding = PaddingValues(horizontal = 17.dp, vertical = 9.dp)
                        ) { Text("➤", fontSize = 18.sp) }
                    }
                }
            }
        }
    }
}

@Composable
fun MessageBubble(message: ChatMessage) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = if (message.isUser) Arrangement.End else Arrangement.Start
    ) {
        Surface(
            color = if (message.isUser) Color(0xFF51418F) else Panel,
            shape = RoundedCornerShape(18.dp),
            modifier = Modifier.widthIn(max = 310.dp)
        ) {
            Text(message.text, color = TextMain, fontSize = 14.sp, lineHeight = 21.sp, modifier = Modifier.padding(14.dp))
        }
    }
}

@Composable
fun SuggestionCard(title: String, description: String) {
    Surface(color = Panel, shape = RoundedCornerShape(15.dp), modifier = Modifier.fillMaxWidth().padding(vertical = 5.dp)) {
        Column(modifier = Modifier.padding(15.dp)) {
            Text(title, color = TextMain, fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
            Spacer(modifier = Modifier.height(5.dp))
            Text(description, color = TextMuted, fontSize = 12.sp)
        }
    }
}

@Composable
fun AttachmentChip(text: String, onRemove: () -> Unit) {
    Surface(color = PanelLight, shape = RoundedCornerShape(10.dp), modifier = Modifier.padding(end = 6.dp)) {
        Row(modifier = Modifier.padding(horizontal = 9.dp, vertical = 6.dp), verticalAlignment = Alignment.CenterVertically) {
            Text(text.take(22), color = TextMain, fontSize = 11.sp)
            Spacer(modifier = Modifier.width(5.dp))
            Text("×", color = Violet, modifier = Modifier.clickable { onRemove() })
        }
    }
}

@Composable
fun EngineCard(title: String, description: String, selected: Boolean, onClick: () -> Unit) {
    Surface(
        color = if (selected) Color(0xFF292443) else Panel,
        shape = RoundedCornerShape(16.dp),
        modifier = Modifier.fillMaxWidth().clickable { onClick() },
        border = if (selected) BorderStroke(1.dp, Violet) else null
    ) {
        Row(modifier = Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
            RadioButton(selected = selected, onClick = onClick, colors = RadioButtonDefaults.colors(selectedColor = Violet))
            Spacer(modifier = Modifier.width(10.dp))
            Column {
                Text(title, color = TextMain, fontWeight = FontWeight.SemiBold, fontSize = 15.sp)
                Spacer(modifier = Modifier.height(5.dp))
                Text(description, color = TextMuted, fontSize = 12.sp, lineHeight = 18.sp)
            }
        }
    }
}

@Composable
fun SettingsSection(title: String, content: @Composable ColumnScope.() -> Unit) {
    Column(modifier = Modifier.fillMaxWidth().background(Panel, RoundedCornerShape(16.dp)).padding(16.dp)) {
        Text(title, color = Violet, fontSize = 15.sp, fontWeight = FontWeight.Bold)
        Spacer(modifier = Modifier.height(15.dp))
        content()
    }
}
