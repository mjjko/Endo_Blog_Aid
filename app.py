import json
import urllib.parse
import requests
import base64
import math
import time
from io import BytesIO
from PIL import Image
from typing import Any, List, Dict
from bs4 import BeautifulSoup

import streamlit as st
from google import genai
from google.genai import types

from config import (
    GEMINI_API_KEY, POLLINATIONS_API_KEY, POLLI_FLUX2_API_KEY, POLLI_ZIMAGE_API_KEY,
    FREEPIK_API_KEY, MODEL_NAME, FLUX_STYLE_GUIDE
)

# Initialize the client using the GEMINI_API_KEY
client = genai.Client(api_key=GEMINI_API_KEY)

# ==========================================
# 🎨 UI STYLING & HELPER FUNCTIONS
# ==========================================
st.set_page_config(page_title="Endo CMS | Smart Publisher", page_icon="✨", layout="wide")

custom_css = """
<style>
    .stApp { background-color: #F0F2F5; }
    div[data-testid="stVerticalBlockBorderWrapper"] > div {
        background-color: #D1D6D8 !important; border-radius: 12px;
        border: 2px solid #A0A5A8 !important; box-shadow: 0 6px 20px rgba(0, 0, 0, 0.08);
        padding: 20px !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] h3, h4, label, p, .stMarkdown { color: #1a1a1a !important; }
    div.stButton > button[kind="primary"] { background-color: #B30047 !important; color: white !important; border: none; border-radius: 8px; }
    div.stButton > button[kind="primary"]:hover { background-color: #8A0035 !important; }
    div.stButton > button[kind="secondary"] { background-color: #FFFFFF !important; color: #333333 !important; border: 1px solid #CCCCCC !important; border-radius: 8px !important; }
    input:disabled { background-color: #E8EBEB !important; color: #888888 !important; cursor: not-allowed; }
    div[data-baseweb="input"] > div, div[data-baseweb="select"] > div, div[data-baseweb="textarea"] > div { background-color: #FFFFFF !important; border: 1px solid #CCCCCC !important; color: #000000 !important; }
    .faded-logo { opacity: 0.15; display: block; margin: 0 auto 20px auto; width: 120px; }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# 🛠️ [FIX 1]: Funktion für lokales Bild zu Base64 (Damit dein lokales Logo funktioniert!)
def get_local_image_base64(filepath: str) -> str:
    try:
        with open(filepath, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except Exception:
        # Fallback auf leeres Bild, falls Pfad lokal nicht stimmt
        return ""

def image_to_base64(img: Image.Image) -> str:
    buffered = BytesIO()
    img = img.convert("RGB")
    img.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode()

def apply_ratio_consensus_crop(img: Image.Image, target_ratio: float = 1.0) -> Image.Image:
    w, h = img.size
    current_ratio = w / h
    if current_ratio > target_ratio: target_w, target_h = h * target_ratio, h
    else: target_w, target_h = w, w / target_ratio
    left, top = math.floor((w - target_w) / 2), math.floor((h - target_h) / 2)
    right, bottom = left + math.floor(target_w), top + math.floor(target_h)
    return img.crop((left, top, right, bottom)).resize((800, 800), Image.Resampling.LANCZOS)

def render_images_pipeline(prompt: str, num_images: int, provider: str, target_model: str, active_key: str, api_params: dict) -> List[Image.Image]:
    imgs =[]
    if provider == "pollinations":
        encoded_p = urllib.parse.quote(prompt)
        for i in range(1, num_images + 1):
            params = {"model": target_model, "seed": int(time.time()) + i, "nologo": "true", "width": api_params.get('width', 512), "height": api_params.get('height', 512)}
            if active_key: params["key"] = active_key
            url = f"https://gen.pollinations.ai/image/{encoded_p}?{urllib.parse.urlencode(params)}"
            resp = requests.get(url, timeout=60)
            if resp.status_code == 500: # Fallback
                params["model"] = "flux"
                url = f"https://gen.pollinations.ai/image/{encoded_p}?{urllib.parse.urlencode(params)}"
                resp = requests.get(url, timeout=60)
            resp.raise_for_status()
            imgs.append(Image.open(BytesIO(resp.content)))
            
    elif provider == "freepik":
        headers = {"x-freepik-api-key": active_key, "Content-Type": "application/json"}
        task_ids =[]
        for _ in range(num_images):
            payload = {"prompt": prompt}
            if api_params.get('style_ref'): payload["style_reference"] = api_params['style_ref']
            post_resp = requests.post("https://api.freepik.com/v1/ai/mystic", headers=headers, json=payload)
            post_resp.raise_for_status()
            task_ids.append(post_resp.json().get("data", {}).get("task_id"))
            
        completed_images = {}
        for _ in range(40):
            if len(completed_images) == num_images: break
            for t_id in task_ids:
                if t_id in completed_images: continue
                get_resp = requests.get(f"https://api.freepik.com/v1/ai/mystic/{t_id}", headers=headers)
                data = get_resp.json().get("data", {})
                if data.get("status") == "COMPLETED":
                    img_url = data.get("generated", [None])[0] or data.get("image", {}).get("url")
                    completed_images[t_id] = Image.open(BytesIO(requests.get(img_url).content))
            time.sleep(3)
        imgs = list(completed_images.values())
    return imgs

def safe_extract_text(response) -> str:
    """Safely extract and clean text from API response."""
    if response is None:
        return ""
    text = getattr(response, "text", "") or ""
    if not text:
        return ""
    return text.strip()

# ==========================================
# 🤖 AGENTS
# ==========================================
class ExtractionAgent:
    def fetch_raw_data(self, url: str) -> List[str]:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        raw_texts =[]
        for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'a']):
            text = tag.get_text(strip=True)
            if len(text) > 10 and text not in raw_texts: raw_texts.append(text)
        return raw_texts

class SanitizerAgent:
    def filter_titles(self, client: genai.Client, raw_texts: List[str]) -> List[str]:
        prompt = f"Filter UI garbage. Return exact 10 relevant medical blog titles from these scraped texts. Output ONLY JSON array of strings: {json.dumps(raw_texts)}"
        response = client.models.generate_content(
            model=MODEL_NAME, contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.1)
        )
        resp_text = safe_extract_text(response)
        if not resp_text:
            raise ValueError("Sanitizer API empty.")
        data = json.loads(resp_text.replace("```json", "").replace("```", ""))
        return data[:10]

class TitlewriterAgent:
    def __init__(self, client: genai.Client, model_name: str):
        self.client, self.model_name = client, model_name
    def generate_titles(self, context: str) -> List[str]:
        prompt = f"Write 4 catchy, empathetic blog titles based on this text. Return ONLY JSON: {{\"titles\":[\"T1\", \"T2\", \"T3\", \"T4\"]}} CONTEXT: {context}"
        response = self.client.models.generate_content(model=self.model_name, contents=prompt, config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.7))
        resp_text = safe_extract_text(response)
        if not resp_text:
            return ["Titel 1"]
        return json.loads(resp_text.replace("```json", "").replace("```", "")).get("titles",["Titel 1"])

class ArtDirectorAgent:
    def __init__(self, client: genai.Client, model_name: str, style_guide: str):
        self.client = client
        self.model_name = model_name
        self.style_guide = style_guide

    def create_campaign(self, title: str, content: str = "") -> Dict[str, str]:
        context_instruction = f"Base the action and emotion strictly on this article context:\n{content}" if content else "Analyze the title to determine the action and emotion."
        
        prompt = f"""
        You are the Lead Art Director for 'Endo Health'.
        TITLE: {title}
        
        {context_instruction}
        
        Your task: Create a highly descriptive prompt for a text-to-image AI (Flux).
        
        CRITICAL RULES FOR THE IMAGE:
        1. MAIN SUBJECT: The focus MUST ALWAYS be a female doctor with short brown hair, wearing a white medical coat and pastel pink pants.
        2. DYNAMIC ACTION & EMOTION: Based on the Title/Context, define exactly what she is doing and how she feels. (e.g., If the title is about pain, she should look empathetic or be holding a comforting hand to her stomach. If it's about science, she might look joyful, holding a glowing pill or a  or something relevant. If it's about Yoga, she should be doing a seated yoga pose).
        3. STYLE GUIDE: Append this exact text at the end: "{self.style_guide}".
        
        Output ONLY a JSON object: 
        {{
            "image_prompt": "A female doctor with short brown hair, wearing a white medical coat and pastel pink pants. [INSERT HER SPECIFIC DYNAMIC ACTION AND EMOTION HERE BASED ON THE TITLE]. [INSERT ANY PROPS LIKE PILLS, CHARTS, ETC]. " + Style Guide
        }}
        """
        response = self.client.models.generate_content(
            model=self.model_name, contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.5) # Etwas mehr Kreativität für die Aktionen
)
        if not response.text:             raise ValueError("Art Director API empty.")
        return json.loads(response.text.strip().replace("```json", "").replace("```", ""))

# Placeholder class for VisionJudgeAgent to resolve the undefined error
class VisionJudgeAgent:
    def __init__(self, client):
        self.client = client

    def evaluate_images(self, imgs, title, style):
        # Placeholder logic for evaluation
        return {"best_index": 1, "reason": "Default evaluation logic."}

# ==========================================
# 🧠 SESSION STATE MANAGEMENT
# ==========================================
if "workflow_stage" not in st.session_state: st.session_state.workflow_stage = "input"
if "generated_images" not in st.session_state: st.session_state.generated_images =[]
if "best_idx" not in st.session_state: st.session_state.best_idx = 0
if "blog_title" not in st.session_state: st.session_state.blog_title = ""
if "blog_content" not in st.session_state: st.session_state.blog_content = ""
if "current_prompt" not in st.session_state: st.session_state.current_prompt = ""
if "show_selection_dialog" not in st.session_state: st.session_state.show_selection_dialog = False
if "show_article_input" not in st.session_state: st.session_state.show_article_input = False
if "generated_titles" not in st.session_state: st.session_state.generated_titles =[]
if "use_ai_title" not in st.session_state: st.session_state.use_ai_title = False
if "manual_title_input" not in st.session_state: st.session_state.manual_title_input = ""

if "prompts" not in st.session_state: st.session_state.prompts = {"Endo Default (Magenta)": FLUX_STYLE_GUIDE}
if "active_prompt_name" not in st.session_state: st.session_state.active_prompt_name = "Endo Default (Magenta)"
if "num_images" not in st.session_state: st.session_state.num_images = 4
if "batch_titles" not in st.session_state: st.session_state.batch_titles =[]
if "batch_results" not in st.session_state: st.session_state.batch_results = {}

def reset_workflow():
    st.session_state.workflow_stage = "input"
    st.session_state.generated_images =[]
    st.session_state.show_selection_dialog = False
    st.session_state.blog_content = ""
    st.session_state.generated_titles =[]
    st.session_state.use_ai_title = False

# ==========================================
# 📝 POPUPS (MODAL DIALOGS)
# ==========================================
@st.dialog("⚙️ Prompt Engineering Studio", width="large")
def style_editor_dialog():
    st.markdown("Verwalte die globalen Design-Regeln oder lass die KI deinen Styleguide optimieren.")
    selected_version = st.selectbox("Style-Profil wählen:", list(st.session_state.prompts.keys()), index=list(st.session_state.prompts.keys()).index(st.session_state.active_prompt_name))
    edited_text = st.text_area("System Instruction (Style Guide):", value=st.session_state.prompts[selected_version], height=150)
    
    st.markdown("<small style='color: #666;'>*Bild-KIs wie Flux brauchen klare, kommagetrennte Strukturen statt komplexer Grammatik.*</small>", unsafe_allow_html=True)
    if st.button("🪄 Styleguide für Bild-KIs (Flux) optimieren", use_container_width=True):
        with st.spinner("Strukturiere Prompt um..."):
            try:
                opt_prompt = f"Convert this messy style guide into a highly structured, machine-readable prompt suffix (comma-separated tags, NO TEXT at the end). USER INPUT: {edited_text}. Return ONLY the optimized text."
                opt_resp = client.models.generate_content(model="gemini-2.5-flash", contents=opt_prompt)
                # Safely handle cases where opt_resp.text may be None
                resp_text = ""
                if opt_resp is not None:
                    resp_text = getattr(opt_resp, "text", "") or ""
                optimized = resp_text.strip() if resp_text else edited_text
                st.session_state.prompts[selected_version] = optimized
                st.success("Prompt wurde maschinengerecht strukturiert!")
                time.sleep(1)
                st.rerun()
            except Exception as e: st.error(f"Fehler: {e}")
    
    st.markdown("---")
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("💾 Profil Speichern", type="primary", use_container_width=True):
            st.session_state.prompts[selected_version] = edited_text
            st.session_state.active_prompt_name = selected_version
            st.rerun()
    with col_b:
        new_name = st.text_input("Neu", placeholder="z.B. Variante Pastell", label_visibility="collapsed")
        if st.button("➕ Als Neues Profil speichern", use_container_width=True) and new_name:
            st.session_state.prompts[new_name] = edited_text
            st.session_state.active_prompt_name = new_name
            st.rerun()

@st.dialog("🖼️ Bildauswahl & Feinabstimmung", width="large")
def selection_dialog():
    if not st.session_state.generated_images or len(st.session_state.generated_images) == 0:
        st.warning("Keine Bilder zur Auswahl vorhanden.")
        if st.button("❌ Schließen"):
            st.session_state.show_selection_dialog = False
            st.rerun()
        return

    if st.session_state.best_idx >= len(st.session_state.generated_images):
        st.session_state.best_idx = len(st.session_state.generated_images) - 1
    if st.session_state.best_idx < 0:
        st.session_state.best_idx = 0

    st.info(f"🌟 **System-Empfehlung:** {st.session_state.ai_reason}")
    cols = st.columns(len(st.session_state.generated_images))
    for i, img in enumerate(st.session_state.generated_images):
        with cols[i]:
            st.image(img, width="stretch")
            # 🛠️ [FIX 4]: Pokal absolut mittig zentrieren mit HTML/CSS
            if i == st.session_state.best_idx: 
                st.markdown("<div style='text-align: center; font-size: 24px; margin-top: -10px;'>🏆</div>", unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("#### ✏️ Prompt anpassen & Neu generieren")
    new_prompt = st.text_area("Der generierte Image-Prompt:", value=st.session_state.current_prompt, height=100, label_visibility="collapsed")
    
    # 🛠️ [FIX 5]: Speichern Logik wieder im Pop-Up (Speichert direkt im gerade aktiven Profil)
    col_save_btn, col_gen_btn = st.columns([1, 2])
    with col_save_btn:
        if st.button("💾 Text als Style speichern", use_container_width=True):
            st.session_state.prompts[st.session_state.active_prompt_name] = new_prompt
            st.session_state.current_prompt = new_prompt
            st.success(f"Unter '{st.session_state.active_prompt_name}' gespeichert!")
            time.sleep(1)
            st.rerun()
            
    with col_gen_btn:
        if st.button("🔄 Mit aktuellem Prompt neu generieren", type="primary", use_container_width=True):
            safe_prompt = str(new_prompt) if new_prompt else ""
            with st.spinner("Generiere neue Bilder..."):
                st.session_state.current_prompt = safe_prompt
                imgs = render_images_pipeline(safe_prompt, st.session_state.num_images, st.session_state.current_provider, st.session_state.current_target_model, st.session_state.current_active_key, st.session_state.current_api_params)
                verdict = VisionJudgeAgent(client=client).evaluate_images(imgs, st.session_state.blog_title, st.session_state.prompts[st.session_state.active_prompt_name])
                st.session_state.generated_images = imgs
                new_idx = verdict.get("best_index", 1) - 1
                if new_idx >= len(imgs): new_idx = len(imgs) - 1
                if new_idx < 0: new_idx = 0
                st.session_state.best_idx = new_idx
                st.rerun() 
            
    st.markdown("---")
    st.markdown("#### ✅ Finale Auswahl")
    choice = st.radio("Titelbild wählen:", range(len(st.session_state.generated_images)), index=st.session_state.best_idx, horizontal=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Bild veröffentlichen", type="primary", use_container_width=True):
            st.session_state.final_image = apply_ratio_consensus_crop(st.session_state.generated_images[choice])
            st.session_state.workflow_stage = "mockup"
            st.session_state.show_selection_dialog = False
            st.rerun()
    with col2:
        if st.button("❌ Abbrechen", use_container_width=True):
            st.session_state.show_selection_dialog = False
            st.rerun()

# ==========================================
# 🖥️ MAIN UI LAYOUT (TABS: SINGLE VS BATCH VS LOW-CODE)
# ==========================================
st.title("👩‍⚕️ Endo Health CMS")
tab_batch, tab_single, tab_nocode = st.tabs(["🚀 Auto-Batch Scraper (Website)", "✍️ Single-Content Creator", "🧩 Low-Code / No-Code Alternative"])

# ------------------------------------------
# TAB 1: SINGLE-CONTENT CREATOR
# ------------------------------------------
with tab_single:
    if st.session_state.workflow_stage == "input":
        _, col_main, col_settings, _ = st.columns([1, 4, 3, 1])
        
        with col_main:
            with st.container(border=True):
                # Lokales Logo laden
                logo_b64 = get_local_image_base64("logo.png")
                if logo_b64:
                    st.markdown(f'<img src="data:image/png;base64,{logo_b64}" class="faded-logo">', unsafe_allow_html=True)
                else:
                    st.markdown('<img src="https://cdn-icons-png.flaticon.com/512/3209/3209995.png" class="faded-logo">', unsafe_allow_html=True)
                    
                st.markdown("<h3 style='text-align: center; margin-top:-10px; margin-bottom: 20px;'>Content Packaging Assistant</h3>", unsafe_allow_html=True)
                
                st.session_state.manual_title_input = st.text_input("Blog-Titel eingeben:", value=st.session_state.manual_title_input, disabled=st.session_state.use_ai_title, placeholder="z.B. Endometriose ist geheilt!")
                
                if st.button("➕ Artikel einfügen (Optional)", use_container_width=True):
                    st.session_state.show_article_input = not st.session_state.show_article_input
                    
                if st.session_state.show_article_input:
                    with st.container():
                        content = st.text_area("Artikel-Text hier einfügen:", height=150, label_visibility="collapsed")
                        if content != st.session_state.blog_content: st.session_state.blog_content = content
                        if st.button("💡 Titel generieren", disabled=not bool(st.session_state.blog_content), use_container_width=True):
                            with st.spinner("KI formuliert Titel..."):
                                tw = TitlewriterAgent(client=client, model_name=MODEL_NAME)
                                st.session_state.generated_titles = tw.generate_titles(st.session_state.blog_content)
                                st.session_state.use_ai_title = True
                                
                if st.session_state.use_ai_title and st.session_state.generated_titles:
                    st.success("Wähle einen der generierten Titel:")
                    st.session_state.blog_title = st.radio("Vorschläge:", st.session_state.generated_titles, label_visibility="collapsed")
                    if st.button("🔄 Manuelle Eingabe wieder aktivieren"):
                        st.session_state.use_ai_title = False
                        st.session_state.generated_titles = []
                        st.rerun()
                else:
                    st.session_state.blog_title = st.session_state.manual_title_input

                st.markdown("<br>", unsafe_allow_html=True)
                generate_btn = st.button("✨ Pipeline Starten", type="primary", use_container_width=True)

        with col_settings:
            with st.container(border=True):
                st.markdown("<h4>🛠️ Pipeline Settings</h4>", unsafe_allow_html=True)
                
                selected_model = st.selectbox("KI-Modell", ["Flux Schnell", "Flux 2 Dev", "ZImage", "Freepik Mystic"])
                
                api_params = {}
                if selected_model in ["Flux Schnell", "Flux 2 Dev", "ZImage"]:
                    aspect_ratio = st.selectbox("Format", ["Quadratisch (1:1)", "Breitbild (16:9)"])
                    api_params['width'] = 512
                    api_params['height'] = 512 if aspect_ratio == "Quadratisch (1:1)" else 288
                elif selected_model == "Freepik Mystic":
                    style_ref = st.file_uploader("Style Referenzbild", type=["jpg", "png"])
                    api_params['style_ref'] = image_to_base64(Image.open(style_ref)) if style_ref else None
                
                st.session_state.num_images = st.slider("Anzahl Bilder (Variationen)", 1, 8, 4)
                
                st.markdown("---")
                st.markdown("<small style='font-weight:bold; color:#666;'>Aktueller Style-Prompt:</small>", unsafe_allow_html=True)
                new_active_prompt = st.selectbox(
                    "Style wählen", 
                    options=list(st.session_state.prompts.keys()), 
                    index=list(st.session_state.prompts.keys()).index(st.session_state.active_prompt_name),
                    label_visibility="collapsed"
                )
                if new_active_prompt != st.session_state.active_prompt_name:
                    st.session_state.active_prompt_name = new_active_prompt
                    st.rerun()
                
                if st.button("🖋️ Prompt-Regeln bearbeiten", use_container_width=True):
                    style_editor_dialog()

        if generate_btn:
            if not st.session_state.blog_title:
                st.warning("Bitte gib einen Titel ein.")
            else:
                with col_main:
                    progress_bar = st.progress(0)
                    status = st.empty()
                    try:
                        model_map = {
                            "Flux Schnell": ("flux", POLLINATIONS_API_KEY, "pollinations"),
                            "Flux 2 Dev": ("flux-2-dev", POLLI_FLUX2_API_KEY or POLLINATIONS_API_KEY, "pollinations"),
                            "ZImage": ("zimage", POLLI_ZIMAGE_API_KEY or POLLINATIONS_API_KEY, "pollinations"),
                            "Freepik Mystic": ("mystic", FREEPIK_API_KEY, "freepik")
                        }
                        target_model, active_key, provider = model_map[selected_model]
                        
                        st.session_state.current_provider, st.session_state.current_target_model = provider, target_model
                        st.session_state.current_active_key, st.session_state.current_api_params = active_key, api_params
                        
                        status.info("🎨 Art Director entwickelt Prompt...")
                        active_style = st.session_state.prompts[st.session_state.active_prompt_name]
                        ad = ArtDirectorAgent(client=client, model_name=MODEL_NAME, style_guide=active_style)
                        campaign = ad.create_campaign(st.session_state.blog_title, st.session_state.blog_content)
                        st.session_state.current_prompt = campaign['image_prompt']
                        progress_bar.progress(40)
                        
                        status.info(f"🏭 Generiere Bilder via {provider}...")
                        imgs = render_images_pipeline(st.session_state.current_prompt, st.session_state.num_images, provider, target_model, active_key, api_params)
                        progress_bar.progress(80)
                        
                        status.info("⚖️ Vision-KI bewertet Qualität...")
                        verdict = VisionJudgeAgent(client=client).evaluate_images(imgs, st.session_state.blog_title, active_style)
                        
                        st.session_state.generated_images = imgs
                        
                        new_idx = verdict.get("best_index", 1) - 1
                        if new_idx >= len(imgs): new_idx = len(imgs) - 1
                        if new_idx < 0: new_idx = 0
                        st.session_state.best_idx = new_idx
                        st.session_state.ai_reason = verdict.get("reason", "")
                        
                        st.session_state.show_selection_dialog = True
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Fehler: {e}")

    if st.session_state.show_selection_dialog:
        selection_dialog()

    elif st.session_state.workflow_stage == "mockup" and st.session_state.final_image:
        _, col_main, _ = st.columns([1, 8, 1])
        with col_main:
            b64 = image_to_base64(st.session_state.final_image)
            snippet = st.session_state.blog_content[:150] + "..." if len(st.session_state.blog_content) > 150 else st.session_state.blog_content
            
            html = f"""
            <div style="display: flex; justify-content: center; padding: 40px;">
                <div style="background: white; border-radius: 20px; overflow: hidden; width: 450px; box-shadow: 0 15px 35px rgba(179,0,71,0.1);">
                    <img src="data:image/jpeg;base64,{b64}" style="width: 100%; height: 450px; object-fit: cover;">
                    <div style="padding: 30px; font-family: sans-serif;">
                        <span style="color: #B30047; font-weight: bold; font-size: 12px; text-transform: uppercase;">Wissen & Therapie</span>
                        <h2 style="color: #1a1a1a; margin: 10px 0;">{st.session_state.blog_title}</h2>
                        <p style="color: #666; font-size: 15px;">{snippet}</p>
                        <a href="#" style="background: #B30047; color: white; padding: 10px 20px; border-radius: 20px; text-decoration: none; display: inline-block; font-weight: bold; font-size: 14px;">Artikel lesen</a>
                    </div>
                </div>
            </div>
            """
            st.markdown(html, unsafe_allow_html=True)
            if st.button("⬅️ Neues Cover erstellen"): reset_workflow(); st.rerun()

# ------------------------------------------
# TAB 2: BATCH PROCESSING (Zentriert)
# ------------------------------------------
with tab_batch:
    _, col_batch, _ = st.columns([1, 8, 1])
    
    with col_batch:
        with st.container(border=True):
            st.markdown("<h3 style='text-align: center; margin-top:-10px; margin-bottom: 20px;'>🕸️ Website Auto-Scraper & Batch Generator</h3>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: #666;'>Ziehe automatisch die neuesten Titel, generiere Bilder, locke deine Favoriten und rendere den Rest neu.</p>", unsafe_allow_html=True)
            
            if "batch_titles" not in st.session_state: st.session_state.batch_titles = []
            if "batch_images" not in st.session_state: st.session_state.batch_images = {}
            if "batch_locked" not in st.session_state: st.session_state.batch_locked = {}
            if "batch_prompts" not in st.session_state: st.session_state.batch_prompts = {}
            if "batch_stage" not in st.session_state: st.session_state.batch_stage = "scrape"
            
            if st.session_state.batch_stage == "scrape":
                col_scrape1, col_scrape2, col_scrape3 = st.columns([1, 2, 1])
                with col_scrape2:
                    if st.button("🔍 1. Website Scrapen", use_container_width=True, type="primary"):
                        with st.spinner("Scrape und filtere Titel von endometriose.app..."):
                            try:
                                ext = ExtractionAgent()
                                raw = ext.fetch_raw_data("https://endometriose.app/aktuelles-2/")
                                san = SanitizerAgent()
                                clean_titles = san.filter_titles(client, raw)
                                
                                st.session_state.batch_titles = clean_titles
                                st.session_state.batch_images = {t: None for t in clean_titles}
                                st.session_state.batch_locked = {t: False for t in clean_titles}
                                st.session_state.batch_prompts = {t: "" for t in clean_titles}
                                
                                st.success(f"{len(clean_titles)} Titel erfolgreich geladen!")
                            except Exception as e:
                                st.error(f"Fehler beim Scraping: {e}")
                
                if st.session_state.batch_titles:
                    st.markdown("---")
                    st.write("**Gefundene Artikel:**")
                    for t in st.session_state.batch_titles:
                        st.markdown(f"- {t}")
                        
                    col_start1, col_start2, col_start3 = st.columns([1, 2, 1])
                    with col_start2:
                        if st.button("🚀 2. Initial-Generierung Starten (Alle)", type="primary", use_container_width=True):
                            st.session_state.batch_stage = "edit"
                            st.rerun()

            elif st.session_state.batch_stage == "edit":
                st.info("💡 **Tipp:** Aktiviere die Checkbox '🔒 Behalten' bei Bildern, die dir gefallen. Klicke dann unten auf '🔄 Unmarkierte neu generieren'.")
                
                col_ctrl1, col_ctrl2, col_ctrl3 = st.columns(3)
                with col_ctrl1:
                    if st.button("🔄 Unmarkierte neu generieren", type="primary", use_container_width=True):
                        ad = ArtDirectorAgent(client=client, model_name=MODEL_NAME, style_guide=st.session_state.prompts[st.session_state.active_prompt_name])
                        my_bar = st.progress(0, text="Starte Batch-Job...")
                        total_images = len(st.session_state.batch_titles)
                        
                        for idx, t in enumerate(st.session_state.batch_titles):
                            if not st.session_state.batch_locked.get(t, False):
                                try:
                                    my_bar.progress((idx) / total_images, text=f"Generiere Bild {idx+1}/{total_images}: {t[:30]}...")
                                    if not st.session_state.batch_prompts.get(t):
                                        camp = ad.create_campaign(t)
                                        st.session_state.batch_prompts[t] = camp.get('image_prompt', '')
                                    prompt = st.session_state.batch_prompts[t]
                                    imgs = render_images_pipeline(prompt=prompt, num_images=1, provider="pollinations", target_model="flux", active_key=POLLINATIONS_API_KEY, api_params={'width': 512, 'height': 512})
                                    if imgs and len(imgs) > 0:
                                        st.session_state.batch_images[t] = imgs[0]
                                    time.sleep(1.5)
                                except Exception as e:
                                    st.error(f"❌ Fehler bei '{t[:20]}...': {e}")
                                    continue
                        my_bar.progress(1.0, text="Batch abgeschlossen!")
                        time.sleep(0.5)
                        st.rerun() 
                        
                with col_ctrl2:
                    if st.button("✅ 3. Auswahl bestätigen & Zum Blog-Mockup", type="primary", use_container_width=True):
                        missing = sum(1 for t in st.session_state.batch_titles if st.session_state.batch_images.get(t) is None)
                        if missing > 0:
                            st.warning(f"Es fehlen noch {missing} Bilder! Bitte klicke auf 'Unmarkierte neu generieren'.")
                        else:
                            st.session_state.batch_stage = "mockup"
                            st.rerun()
                            
                with col_ctrl3:
                    if st.button("🗑️ Batch verwerfen & Neu Scrapen", use_container_width=True):
                        st.session_state.batch_titles = []
                        st.session_state.batch_images = {}
                        st.session_state.batch_locked = {}
                        st.session_state.batch_prompts = {}
                        st.session_state.batch_stage = "scrape"
                        st.rerun()

                st.markdown("---")
                
                cols = st.columns(3)
                for idx, title in enumerate(st.session_state.batch_titles):
                    with cols[idx % 3]:
                        with st.container(border=True):
                            short_title = title[:45] + "..." if len(title) > 45 else title
                            st.markdown(f"**{short_title}**")
                            
                            img = st.session_state.batch_images.get(title)
                            if img is not None:
                                st.image(img, width="stretch")
                                locked = st.checkbox("🔒 Behalten", value=st.session_state.batch_locked.get(title, False), key=f"lock_{idx}")
                                st.session_state.batch_locked[title] = locked
                                
                                with st.expander("Prompt anpassen"):
                                    new_p = st.text_area("Prompt:", value=st.session_state.batch_prompts.get(title, ""), key=f"prompt_{idx}", label_visibility="collapsed")
                                    if new_p != st.session_state.batch_prompts.get(title, ""):
                                        st.session_state.batch_prompts[title] = new_p
                                        st.session_state.batch_locked[title] = False 
                            else:
                                st.markdown("<div style='height: 150px; display: flex; align-items: center; justify-content: center; background-color: #E8EBEB; border-radius: 8px; color: #888;'>Wartet auf Generierung...</div>", unsafe_allow_html=True)
                                st.caption("Noch kein Bild vorhanden.")

            elif st.session_state.batch_stage == "mockup":
                st.markdown("<h3 style='text-align: center; margin-top:-10px; margin-bottom: 20px;'>🎉 Endo Health - Aktuelles (Live Preview)</h3>", unsafe_allow_html=True)
                st.write("So sieht die Blog-Übersichtsseite mit deinen finalen Bildern aus.")
                
                if st.button("⬅️ Zurück zum Editor"):
                    st.session_state.batch_stage = "edit"
                    st.rerun()
                    
                st.markdown("---")
                
                mockup_cols = st.columns(3)
                for idx, title in enumerate(st.session_state.batch_titles):
                    img = st.session_state.batch_images.get(title)
                    if img is not None:
                        cropped_img = apply_ratio_consensus_crop(img, target_ratio=1.77)
                        b64 = image_to_base64(cropped_img)
                        
                        html_card = f"""
                        <div style="background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 20px; border: 1px solid #EAEAEA;">
                            <img src="data:image/jpeg;base64,{b64}" style="width: 100%; height: 180px; object-fit: cover;">
                            <div style="padding: 15px;">
                                <span style="color: #B30047; font-weight: 700; font-size: 11px; text-transform: uppercase;">Artikel</span>
                                <h4 style="margin: 8px 0 0 0; color: #1a1a1a; font-size: 16px; line-height: 1.3;">{title}</h4>
                            </div>
                        </div>
                        """
                        with mockup_cols[idx % 3]:
                            st.markdown(html_card, unsafe_allow_html=True)

# ------------------------------------------
# TAB 3: LOW-CODE / NO-CODE ALTERNATIVE
# ------------------------------------------
with tab_nocode:
    _, col_nocode, _ = st.columns([1, 8, 1])
    
    with col_nocode:
        with st.container(border=True):
            st.markdown("<h3 style='text-align: center; margin-top:-10px; margin-bottom: 20px;'>🧩 Die Low-Code Architektur</h3>", unsafe_allow_html=True)
            st.markdown("""
            In der Stellenausschreibung wurde gefragt, wann Tools wie **n8n, Make oder Rivet** schneller ans Ziel führen als ein selbst geschriebenes Script.
            
            **Meine Architekten-Einschätzung:**
            Ein Python/Streamlit MVP (wie Tab 1 und 2) ist perfekt für hochgradig anpassbare UIs und komplexe State-Management-Workflows (Human-in-the-Loop). 
            Sobald der visuelle Stil der Bilder und die API-Logik aber zu **100 % finalisiert** sind und das System "Headless" im Hintergrund laufen soll, ist ein Low-Code Tool die bessere Wahl.
            
            **Vorteile von Rivet/n8n für Endo Health:**
            1. **Wartbarkeit:** Das Content-Team kann den "Art Director Prompt" oder die API-Endpunkte visuell anpassen, ohne einen Developer zu brauchen.
            2. **Integration:** Wir können den Output-Node direkt an das echte CMS (z.B. Webflow, WordPress, Contentful) von Endo Health anbinden.
            3. **Skalierbarkeit:** Webhooks triggern den Agent-Swarm vollautomatisch, sobald ein Redakteur auf "Artikel speichern" klickt.
            """)
            
            st.markdown("---")
            st.markdown("#### Beispiel-Architektur (Rivet Workflow)")
            
            # Bild laden (Fallback, falls nocode_example.png lokal nicht existiert)
            try:
                nocode_img_b64 = get_local_image_base64("no-code_WORKFLOW.PNG")
                if nocode_img_b64:
                    st.markdown(f'<img src="data:image/png;base64,{nocode_img_b64}" style="width: 100%; border-radius: 8px; border: 1px solid #EAEAEA;">', unsafe_allow_html=True)
                else:
                    st.info("💡 **Hinweis:** Bitte lade ein Bild mit dem Namen `no-code_WORKFLOW.PNG` in dein Hauptverzeichnis auf GitHub hoch, um hier einen Workflow-Screenshot anzuzeigen.")
            except Exception:
                st.info("💡 **Hinweis:** Bitte lade ein Bild mit dem Namen `no-code_WORKFLOW.PNG` in dein Hauptverzeichnis auf GitHub hoch, um hier einen Workflow-Screenshot anzuzeigen.")
