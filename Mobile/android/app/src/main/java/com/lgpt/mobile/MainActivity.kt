package com.lgpt.mobile

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    LgptHomeScreen()
                }
            }
        }
    }
}

@Composable
private fun LgptHomeScreen() {
    var selectedMode by remember { mutableStateOf("Intelligent") }
    var selectedEngine by remember { mutableStateOf("Local (téléphone)") }

    Column(
        modifier = Modifier.fillMaxSize().padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        Text("L-GPT", style = MaterialTheme.typography.headlineLarge)
        Text("Assistant IA — version mobile 4.0", style = MaterialTheme.typography.bodyLarge)

        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text("Mode de réponse", style = MaterialTheme.typography.titleMedium)
                Spacer(Modifier.height(8.dp))
                Row {
                    listOf("Document", "Connaissances", "Intelligent").forEach { mode ->
                        if (selectedMode == mode) {
                            Button(onClick = { selectedMode = mode }) { Text(mode) }
                        } else {
                            OutlinedButton(onClick = { selectedMode = mode }) { Text(mode) }
                        }
                        Spacer(Modifier.width(4.dp))
                    }
                }
                Spacer(Modifier.height(6.dp))
                Text(
                    when (selectedMode) {
                        "Document" -> "Les réponses utiliseront uniquement les documents importés."
                        "Connaissances" -> "Les réponses utiliseront les connaissances du modèle."
                        else -> "L-GPT choisira entre les documents et les connaissances du modèle."
                    },
                    style = MaterialTheme.typography.bodyMedium
                )
            }
        }

        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text("Moteur IA", style = MaterialTheme.typography.titleMedium)
                Spacer(Modifier.height(8.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    if (selectedEngine == "Local (téléphone)") {
                        Button(onClick = { selectedEngine = "Local (téléphone)" }) { Text("Téléphone") }
                    } else {
                        OutlinedButton(onClick = { selectedEngine = "Local (téléphone)" }) { Text("Téléphone") }
                    }
                    if (selectedEngine == "PC (Ollama)") {
                        Button(onClick = { selectedEngine = "PC (Ollama)" }) { Text("PC / Ollama") }
                    } else {
                        OutlinedButton(onClick = { selectedEngine = "PC (Ollama)" }) { Text("PC / Ollama") }
                    }
                }
                Text("Sélection actuelle : $selectedEngine", style = MaterialTheme.typography.bodyMedium)
                Text("Connexion moteur : à configurer à l'étape suivante.", style = MaterialTheme.typography.bodySmall)
            }
        }

        Button(onClick = { /* PDF picker will be added in a later step. */ }, modifier = Modifier.fillMaxWidth()) {
            Text("Importer un PDF — bientôt disponible")
        }

        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text("Nouvelle conversation", style = MaterialTheme.typography.titleMedium)
                Spacer(Modifier.height(6.dp))
                Text("L'interface de discussion et la mémoire des conversations seront ajoutées dans les prochaines étapes.")
            }
        }
        Spacer(Modifier.weight(1f))
        Text("L-GPT Mobile 4.0 — prototype d'interface", style = MaterialTheme.typography.labelSmall)
    }
}
