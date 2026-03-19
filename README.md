# 👩‍⚕️ Endo Health CMS & AI Image Pipeline
**Ein modulares Agenten-Framework für automatisierten Digital Health Content.**

*Entwickelt für die Endo Health "AI-Solutions Engineer" Challenge.*

## 🚀 The TL;DR
Für diese Challenge habe ich mich entschieden, nicht einfach ein monolithisches Python-Skript zu schreiben, das blind 10 Bilder generiert. Stattdessen habe ich ein modulares **Agentic Framework** und ein vollwertiges **SaaS-Frontend (Streamlit)** gebaut. Der Fokus des MVPs liegt ganz klar auf agiler System-Architektur, API-Orchestrierung und Workflow-Logik.

Das Tool simuliert euren realen Redaktions-Alltag: Von der LLM-gestützten Titelfindung über multimodale Qualitätskontrolle bis hin zur vollautomatischen Batch-Generierung von Website-Headern.

👉 **[Live Demo: Endo CMS Smart Publisher](https://endoblogaid-jhs95ky7ep7ccdnzsjghj5.streamlit.app/)**

> **!!! ACHTUNG !!!** 
> *Bitte bei Streamlit oben rechts über die Einstellungen (⚙️) in den **Light Mode** wechseln, damit das UI/CSS optimal dargestellt wird. Danke ;)*

---

## 🗺️ Walkthrough: Die Architektur im Einsatz

Das System folgt streng dem Prinzip der *Separation of Concerns*. Die Logik ist vollständig vom User-Interface getrennt und in isolierte KI-Agenten unterteilt, die asynchron miteinander kommunizieren.

### 📍 Seite 1: Auto-Batch Scraper (Die Challenge)
Auf dem ersten Tab der App löse ich die eigentliche Challenge: Automatisiert 10 Titel ziehen und konsistent bebildern. 

*   **Der LLM-Assisted Scraper (`ExtractionAgent` & `SanitizerAgent`):** Klassisches Web-Scraping bricht sofort, wenn sich CSS oder das Design der Website ändert. Ich habe eine KI-gestützte Filterung implementiert. Der Extraktor zieht alle rohen Textbausteine des DOM-Trees. Der `SanitizerAgent` (Gemini 3.1 Flash) sortiert semantisch den UI-Müll (z.B. "Newsletter", "Impressum") aus und isoliert ausschließlich echte medizinische Blog-Titel. Das macht die Datenpipeline extrem robust und wartungsfrei.
*   **The Asynchronous Engine (`RenderAgent`):** Die Bildgenerierung (z. B. 10 Bilder auf einmal) läuft über eine Pipeline mit "Exponential Backoff". Bei HTTP-Fehlern (Rate Limits oder 500er Server Crashes der Bild-APIs) stürzt das System nicht ab, sondern wartet oder wechselt elegant in einen stabilen Fallback-Modus.

### 📍 Seite 2: Single-Content Creator (Der Redaktions-Assistent)
Hier demonstriere ich, wie KI-Tools Teams im Alltag spürbar entlasten können. 

*   **The Context-Aware Designer (`ArtDirectorAgent` & `TitlewriterAgent`):** Bild-KIs tendieren zu Halluzinationen. Um das zu verhindern und die Brand-Consistency zu wahren, übersetzt der `ArtDirectorAgent` das medizinische Thema (oder den eingefügten Artikeltext) in streng strukturierte 2D-Vektor Prompts. Ein hartcodierter Style-Guide (Endo-Health Magenta, Female Health Aesthetic) wird automatisch injiziert.
*   **Prompt Engineering Studio (BONUS):** Das UI verfügt über ein interaktives Studio (⚙️ Prompt-Regeln bearbeiten). Es wandelt die natürlich-sprachigen Wünsche von Redakteuren auf Knopfdruck in Bildgenerator-angepasste, kommagetrennte Prompts um.
*   **Multimodal Quality Assurance (`VisionJudgeAgent`):** Bevor der Redakteur die generierten Bilder sichtet, feuert ein automatisierter VQA-Loop (Visual Question Answering). Vier Bildvarianten werden im RAM gehalten und an die Vision-KI übergeben. Das LLM gleicht die Pixel mit euren Brand-Guidelines ab und liefert eine JSON-basierte Empfehlung (🏆) für das beste Bild.
*   **Future Roadmap (RLHF):** Durch Reinforcement Learning from Human Feedback lässt sich dieser Agent in der Zukunft iterativ trainieren. Wenn das Team die System-Empfehlung überstimmt, speichern wir das Delta. Die Vision-KI lernt dadurch automatisch die visuellen Nuancen und Präferenzen eurer Redaktion, bis die manuelle Auswahl komplett überflüssig wird.

### 📍 Seite 3: Low-Code Alternative (Der Headless-Ansatz)
Auf der dritten Seite diskutiere ich die Vor- und Nachteile von Code vs. No-Code. Ein Python/Streamlit MVP ist perfekt für anpassbare UIs und komplexe State-Management-Workflows (Human-in-the-Loop). 
Sobald der visuelle Stil der Bilder aber zu 100 % finalisiert ist, würde ich die Architektur auf ein Low-Code System (wie Rivet, n8n oder Make) umstellen. Das erleichtert dem Content-Team die Wartung und ermöglicht (z. B. in Kombination mit der Freepik Mystic API) eine nahtlose Webhook-Anbindung an euer CMS. 

---

## 🛠️ The "Zero-Budget Hacker" Approach vs. Enterprise Scaling

Für diesen Prototypen habe ich mich bewusst für einen agilen **Zero-Budget-Ansatz** entschieden. Das Backend läuft komplett auf kostenlosen Cloud-APIs (Gemini Free Tier, Pollinations, FreePik, Streamlit Cloud). Das beweist, dass man hochkomplexe MVPs ohne Infrastrukturkosten in Rekordzeit validieren kann.

**So skaliere ich das System in eurer Produktionsumgebung:**
1. **Datenschutz (DSGVO/HIPAA):** Um unveröffentlichte Patiententhemen nicht an externe Server zu senden, ersetze ich die Text-LLMs durch lokale Small Language Models (z. B. Llama 3 8B).
2. **Visuelle Präzision:** Für 100%ige Farbtreue und Charakter-Konsistenz wird der Public-Bildgenerator durch einen lokalen ComfyUI-Server mit einem dedizierten **LoRA-Modell** (trainiert auf das Endo Health Brand-Kit) ersetzt.
3. **Automatisierung:** Die gesamte Pipeline lässt sich über ein simples Orchestrator-Script starten. Auf der dritten Seite (Low-Code) habe ich ein Diagramm hochgeladen, das die Kommunikationswege der einzelnen Komponenten skizziert.

---

## 💻 Lokale Ausführung

1. Repository klonen.
2. Virtuelle Umgebung erstellen: `python -m venv venv`
3. Umgebung aktivieren und Dependencies installieren: `pip install -r requirements.txt`
4. Eigene API-Keys in eine `.env` Datei eintragen (siehe `.env.example`).
5. App starten: `streamlit run app.py`

*Let's build workflows that actually take the stress away.*
