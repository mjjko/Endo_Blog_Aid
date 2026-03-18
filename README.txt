# 👩‍⚕️ Endo Health CMS & AI Image Pipeline
**An Agentic Framework for Automated Digital Health Content**

*Built for the Endo Health AI-Solutions Engineer Challenge.*

## 🚀 The TL;DR
Ich habe euch ein modulares **Agentic Framework** und ein vollwertiges **SaaS-Frontend (Streamlit)** gebaut. Es simuliert einen realen Redaktions-Workflow: Von der automatisierten Themenfindung über die multimodale Qualitätskontrolle bis zum fertigen kontextbezogenen Bildgenerator.

👉 **[Live Demo: Endo CMS Smart Publisher](HIER_DEINEN_STREAMLIT_LINK_EINTRAGEN)**

---

## 🏗️ System Architecture (The Agent Swarm)

Das System folgt streng dem Prinzip der *Separation of Concerns*. Die Geschäftslogik ist vollständig vom UI getrennt und in isolierte KI-Agenten unterteilt, die asynchron miteinander kommunizieren.

### 1. Der LLM-gestützte Scraper (`ExtractionAgent` & `SanitizerAgent`)
**Technisch:** Herkömmliches Web-Scraping stützt sich auf instabile CSS-Selektoren, die bei Aktualisierungen der Benutzeroberfläche versagen. Ich habe eine LLM-gestützte Bereinigungspipeline implementiert: Der `ExtractionAgent` extrahiert rohe DOM-Textknoten, und der `SanitizerAgent` (gemini-3.1-flash-lite-preview) filtert UI-Artefakte (z. B. „Newsletter“, „Impressum“) semantisch heraus, um reine Titel medizinischer Blogs zu isolieren.
**In meinem Sprech:** Klassische Webscraper gehen kaputt, sobald ihr das Design der Website ändert. Mein System zieht einfach den ganzen Textmüll der Seite und lässt die KI entscheiden, was ein echter Blog-Titel ist und was nicht. Das System ist dadurch extrem robust und wartungsfrei.

### 2. The Context-Aware Designer (`ArtDirectorAgent` & `TitlewriterAgent`)
**Technical:** To prevent generative hallucinations and ensure brand consistency, the `ArtDirectorAgent` strictly translates medical topics into literal 2D flat-vector prompt structures, forcefully appending a hardcoded hex-color style guide (`FLUX_STYLE_GUIDE`). 
**In meinem Sprech:** Bild-KIs übertreiben gerne. Wenn man ihnen keinen strengen Rahmen gibt, halluzinieren sie seltsame Dinge. Der Art Director sorgt dafür, dass aus einem komplexen medizinischen Thema ein maschinenlesbarer Befehl wird, der garantiert, dass das Endo-Health-Magenta und der flache App-Stil zu 100 % getroffen werden. Keine Bänder, keine Gesichter, nur saubere Vektoren.

### 3. The Asynchronous Engine (`RenderAgent`)
**Technical:** Implemented dynamic provider routing supporting both synchronous (Pollinations) and asynchronous long-polling APIs (Freepik Mystic with Style Reference injection). The pipeline features Exponential Backoff for robust 429/500 HTTP error handling and a Fallback-Degradation-Loop.
**In meinem Sprech:** Wenn ein Server bei einem API-Anbieter crasht, stürzt mein Programm nicht ab. Es wartet kurz, versucht es noch mal oder schaltet nahtlos auf ein stabileres Modell um. Außerdem könnt ihr im UI zwischen Modellen (wie Flux oder Freepik) wechseln und sogar ein Referenzbild hochladen.

### 4. Multimodal Quality Assurance (`VisionJudgeAgent`)
**Technical:** Integrated an automated VQA (Visual Question Answering) loop. The system generates 4 variations in memory (RAM) and feeds them to Gemini Vision alongside the brand guidelines. The LLM acts as an automated judge, returning a JSON-formatted verdict on the highest-fidelity image.
**In meinem Sprech:** Bevor der Redakteur die Bilder überhaupt sieht, hat eine zweite KI sie sich schon angeschaut, mit euren Brand-Guidelines abgeglichen und das beste Bild mit einem Sternchen markiert. Das spart Entscheidungszeit.
**Der nächste Schritt wäre dem VisionJudgeAgent durch Delta-Protokollierung und RF-Learning seine Wahl der Bilder an die Kreterien des Users anzupassen. Das erzeugt vertrauen auf lange Sicht und der User muss nicht mehr die Bildauswahl manuell machen.
---

## 🛠️ The "Zero-Budget Hacker" Approach vs. Enterprise Scaling

Für diesen Prototypen habe ich mich bewusst für einen agilen **Zero-Budget-Ansatz** entschieden. Das Backend läuft komplett auf kostenlosen/günstigen Cloud-APIs (Gemini, Pollinations, Streamlit Cloud). Das beweist, dass man hochkomplexe MVPs in kürzester Zeit ohne Infrastrukturkosten validieren kann.

**Wie ich das System in eurer echten Produktionsumgebung skalieren würde:**
1. **Datenschutz (HIPAA/DSGVO):** Um sensible Patiententhemen oder interne Artikel-Entwürfe nicht an externe APIs zu senden, würde ich die Text-Agenten auf lokale **SLMs** (Small Language Models wie Llama 3 8B) umstellen.
2. **100% visuelle Konsistenz:** Statt auf öffentliche Flux-APIs zu vertrauen, würde ich einen lokalen ComfyUI-Server orchestrieren. Dort würde ich ein dediziertes **LoRA-Modell** trainieren, das exakt auf euer Corporate Design und eure App-Charaktere gefinetuned ist.
3. **Low-Code Integration:** Um das System für Nicht-Programmierer wartbar zu machen, lassen sich die Agenten-Knotenpunkte problemlos in Tools wie **Rivet** oder **n8n** überführen.

---

## 🚀 How to run locally

1. Clone the repository.
2. Create a virtual environment: `python -m venv venv`
3. Activate it and install dependencies: `pip install -r requirements.txt`
4. Add your API keys to a `.env` file (see `.env.example`).
5. Run the UI: `streamlit run app.py`

*Let's build workflows that actually take the stress away.*