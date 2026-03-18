# 👩‍⚕️ Endo Health CMS & AI Image Pipeline
**Ein modulares Agenten-Framework für automatisierten Digital Health Content.**

*Entwickelt für die Endo Health "AI-Solutions Engineer" Challenge.*

## 🚀 The TL;DR
Für diese Challenge habe ich mich entschieden, nicht einfach ein Python-Skript zu schreiben, das blind 10 Bilder generiert. Ich habe ein modulares **Agentic Framework** und ein vollwertiges **SaaS-Frontend (Streamlit)** gebaut. Der Fokus liegt wegen mangelder Zeit auf Architektur und nicht Design. 

Das Tool simuliert einen Redaktions-Workflow: Von der LLM-gestützten Titelfindung über multimodale Qualitätskontrolle bis hin zur Batch-Generierung der gesamten Website-Header.

👉 **[Live Demo: Endo CMS Smart Publisher](https://endoblogaid-jhs95ky7ep7ccdnzsjghj5.streamlit.app/)**

!!! ACHTUNG !!! 
Bitte bei Streamlit in den Lite Modus gehen. 
DANKE ;)
---

## 🏗️ System-Architektur (The Agent Swarm)

Das System folgt streng dem Prinzip der *Separation of Concerns*. Die Logik ist vollständig vom User-Interface getrennt und in isolierte KI-Agenten unterteilt, die asynchron miteinander kommunizieren.

### 1. The LLM-Assisted Scraper (`ExtractionAgent` & `SanitizerAgent`)
**Das Konzept:** Klassisches Web-Scraping bricht sofort, wenn sich das Cascading Style Sheets (CSS) oder Design der Website ändert. Ich habe eine KI-gestützte Filterung implementiert. Der `ExtractionAgent` zieht alle rohen Textbausteine des DOM-Trees. Der `SanitizerAgent` (Gemini 3 Flash) sortiert semantisch UI-Elemente (z.B. "Newsletter", "Impressum") aus und isoliert ausschließlich echte medizinische Blog-Titel. Das macht die Datenpipeline wartungsfrei.

### 2. The Context-Aware Designer (`ArtDirectorAgent` & `TitlewriterAgent`)
**Das Konzept:** Bild-KIs tendieren zu Halluzinationen. Um das zu verhindern und die Brand-Consistency zu wahren, übersetzt der `ArtDirectorAgent` das medizinische Thema in streng strukturierte 2D-Vektor Prompts. Ein hartcodierter Style-Guide (Endo-Health Magenta, Female Health Aesthetic) wird automatisch injiziert. 
**2.1 BONUS:** Das System verfügt zudem über ein interaktives **Prompt Engineering Feature**, das natürliche Sprache in Bildgenerator-angepasste Prompts umstrukturiert.

### 3. The Asynchronous Engine (`RenderAgent`)
**Das Konzept:** Das System unterstützt sowohl synchrone als auch asynchrone (Long-Polling) APIs. Die Bildgenerierung läuft über eine Pipeline mit "Exponential Backoff", um bei HTTP-Fehlern (Rate Limits oder 500er Server Crashes) elegant in einen stabilen Fallback-Modus zu wechseln, anstatt abzustürzen.

### 4. Multimodal Quality Assurance (`VisionJudgeAgent`)
**Das Konzept:** Bevor der Redakteur die generierten Bilder sichtet, feuert ein automatisierter VQA-Loop (Visual Question Answering). Vier Bildvarianten werden im RAM gehalten und an die Vision-KI übergeben. Das LLM gleicht die Pixel mit euren Brand-Guidelines ab und liefert eine JSON-basierte Empfehlung für das beste Bild.
**4.1 BONUS (Future Roadmap):** Durch RLHF (Reinforcement Learning from Human Feedback) lässt sich dieser Agent iterativ trainieren. Wenn das Team die System-Empfehlung überstimmt, speichern wir das Delta. Die Vision-KI lernt dadurch automatisch die spezifischen, visuellen Nuancen und Präferenzen eurer Redaktion kennen, bis die manuelle Bildauswahl komplett überflüssig wird.

---

## 🛠️ The "Zero-Budget Hacker" Approach vs. Enterprise Scaling

Für diesen Prototypen habe ich mich bewusst für einen agilen **Zero-Budget-Ansatz** entschieden. Das Backend läuft komplett auf kostenlosen Cloud-APIs (Gemini Free Tier, Pollinations,FreePik, Streamlit Cloud). Das beweist, dass man hochkomplexe MVPs ohne Infrastrukturkosten in Rekordzeit validieren kann.

**So skaliere ich das System in eurer Produktionsumgebung:**
1. **Datenschutz (DSGVO/HIPAA):** Um unveröffentlichte Patiententhemen nicht an externe Server zu senden, ersetze ich die Text-LLMs durch lokale Small Language Models (z. B. Llama 3 8B).
2. **Visuelle Präzision:** Für 100%ige Farbtreue und Charakter-Konsistenz wird der Public-Bildgenerator durch einen lokalen ComfyUI-Server mit einem dedizierten **LoRA-Modell** (trainiert auf das Endo Health Brand-Kit) ersetzt.
3. **Automatisierung:** Sobald der Workflow visuell finalisiert ist, würde ich die Agenten-Knotenpunkte in ein Low-Code System (Rivet oder n8n) übertragen und via Webhook direkt an euer Headless-CMS anbinden. *(Siehe Tab 3 in der Web-App).*

Alternativ kann man auch die Vorteile von FreePik nutzen und dort über ein simples Orchestrator Script die Pipeline starten. Auf der dritten Seite habe ich ein Beispiel für die Kommunikationswege der einzelnen Komponenten hochgeladen.

---

## 🚀 Lokale Ausführung

1. Repository klonen.
2. Virtuelle Umgebung erstellen: `python -m venv venv`
3. Umgebung aktivieren und Dependencies installieren: `pip install -r requirements.txt`
4. Eigene API-Keys in eine `.env` Datei eintragen (siehe `.env.example`).
5. App starten: `streamlit run app.py`

*Let's build workflows that actually take the stress away.*
