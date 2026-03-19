import os
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

# ==========================================
# 🎨 UI STYLING (CSS INJECTION)
# ==========================================
st.set_page_config(page_title="Endo CMS | Smart Publisher", page_icon="✨", layout="centered")

custom_css = """
<style>
    .stApp { background-color: #F8F9FA; }
    
    .global-header { text-align: center; padding: 2rem 0 1rem 0; }
    .global-header img { width: 60px; margin-bottom: 10px; }
    .global-header h1 { color: #1A1A1A; font-weight: 800; font-size: 2.2rem; margin: 0; padding: 0; }
    .global-header p { color: #666666; font-size: 1.1rem; margin-top: 5px; }

    div[data-testid="stVerticalBlockBorderWrapper"] > div {
        background-color: #FFFFFF !important; border-radius: 16px;
        border: 1px solid #EAEAEA !important; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.04);
        padding: 24px !important;
    }
    
    div[data-testid="stVerticalBlockBorderWrapper"] h3, 
    div[data-testid="stVerticalBlockBorderWrapper"] h4, 
    div[data-testid="stVerticalBlockBorderWrapper"] label, 
    div[data-testid="stVerticalBlockBorderWrapper"] p { color: #2D3748 !important; }

    /* 🛠️ [FIX 2]: Tabs aggressiv zentrieren */
    div[data-baseweb="tab-list"] {
        display: flex !important;
        justify-content: center !important;
        gap: 15px !important;
    }
    
    /* 🛠️ [FIX 1]: Buttons (Tiefes CSS-Override) */
    /* Primary Buttons (Magenta) */
    div.stButton > button[kind="primary"] { 
        background-color: #B30047 !important; 
        border: none !important; border-radius: 10px !important; padding: 0.6rem 1.2rem !important; 
        transition: all 0.2s ease; 
    }
    /* Zwinge die innere Schrift WEISS! */
    div.stButton > button[kind="primary"] * {
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }
    div.stButton > button[kind="primary"]:hover { background-color: #8A0035 !important; transform: translateY(-2px); }
    
    /* Secondary Buttons (Grau) */
    div.stButton > button[kind="secondary"] { 
        background-color: #F0F2F5 !important; 
        border: 1px solid #CBD5E0 !important; border-radius: 10px !important; 
    }
    /* Zwinge die innere Schrift DUNKEL! */
    div.stButton > button[kind="secondary"] * {
        color: #1A1A1A !important;
        font-weight: 600 !important;
    }
    div.stButton > button[kind="secondary"]:hover { background-color: #E2E8F0 !important; }
    
    input:disabled { background-color: #F7FAFC !important; color: #A0AEC0 !important; cursor: not-allowed; }
    div[data-baseweb="input"] > div, div[data-baseweb="select"] > div, div[data-baseweb="textarea"] > div { background-color: #FFFFFF !important; border: 1px solid #E2E8F0 !important; border-radius: 8px; }
    
    .title-container { min-height: 45px; height: auto; margin-bottom: 10px; font-weight: 600; line-height: 1.3; }
    .image-btn-container { display: flex; flex-direction: column; align-items: center; margin-bottom: 10px; }
    .image-btn-container img { width: 100%; border-radius: 12px; object-fit: cover; transition: all 0.3s ease; }
    .selected-img img { border: 4px solid #4CAF50 !important; box-shadow: inset 0 0 40px rgba(76, 175, 80, 0.6), 0 0 15px rgba(76, 175, 80, 0.4) !important; filter: brightness(1.1); }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# ==========================================
# 🛠️ HELPER FUNCTIONS
# ==========================================
def get_local_image_base64(filename_without_ext: str) -> str:
    possible_names = [f"{filename_without_ext}.png", f"{filename_without_ext}.PNG", f"{filename_without_ext}.jpg"]
    for d in [".", "venv"]:
        for name in possible_names:
            path = os.path.join(d, name)
            if os.path.exists(path):
                try:
                    with open(path, "rb") as f: return base64.b64encode(f.read()).decode()
                except Exception: pass
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
            if resp.status_code == 500:
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
    if response is None: return ""
    text = getattr(response, "text", "") or ""
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
    def filter_titles(self, client: genai.Client, raw_texts: List[str], num_titles: int) -> List[str]:
        prompt = f"Filter UI garbage. Return exact {num_titles} relevant medical blog titles from these scraped texts. Output ONLY JSON array of strings: {json.dumps(raw_texts)}"
        response = client.models.generate_content(
            model=MODEL_NAME, contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.1)
        )
        resp_text = safe_extract_text(response)
        if not resp_text: raise ValueError("Sanitizer API empty.")
        data = json.loads(resp_text.replace("```json", "").replace("```", ""))
        return data[:num_titles]

class TitlewriterAgent:
    def __init__(self, client: genai.Client, model_name: str):
        self.client, self.model_name = client, model_name
    def generate_titles(self, context: str) -> List[str]:
        prompt = f"Write 4 catchy, empathetic blog titles based on this text. Return ONLY JSON: {{\"titles\":[\"T1\", \"T2\", \"T3\", \"T4\"]}} CONTEXT: {context}"
        response = self.client.models.generate_content(model=self.model_name, contents=prompt, config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.7))
        resp_text = safe_extract_text(response)
        if not resp_text: return ["Titel 1"]
        return json.loads(resp_text.replace("```json", "").replace("```", "")).get("titles",["Titel 1"])

class ArtDirectorAgent:
    def __init__(self, client: genai.Client, model_name: str, style_guide: str):
        self.client, self.model_name, self.style_guide = client, model_name, style_guide
    def create_campaign(self, title: str, content: str = "") -> Dict[str, str]:
        context_instruction = f"Base the action and emotion strictly on this article context:\n{content}" if content else "Analyze the title to determine the action and emotion."
        prompt = f"""
        You are the Lead Art Director for 'Endo Health'. TITLE: {title}
        {context_instruction}
        CRITICAL RULES:
        1. MAIN SUBJECT: A female doctor with short brown hair, wearing a white medical coat and pastel pink pants.
        2. DYNAMIC ACTION: Based on the Title, define exactly what she is doing and how she feels.
        3. Append style guide: "{self.style_guide}".
        Output ONLY JSON: {{"image_prompt": "A female doctor with short brown hair... [ACTION]... [STYLE GUIDE]"}}
        """
        response = self.client.models.generate_content(model=self.model_name, contents=prompt, config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.5))
        resp_text = safe_extract_text(response)
        if not resp_text: raise ValueError("Art Director API empty.")
        return json.loads(resp_text.replace("```json", "").replace("```", ""))

class VisionJudgeAgent:
    def __init__(self, client: genai.Client):
        self.client, self.model_name = client, "gemini-2.5-flash" 
    def evaluate_images(self, images: List[Image.Image], title: str, style: str) -> Dict[str, Any]:
        prompt = f"Evaluate these images for title: '{title}'. Style rules: {style}. Return JSON: {{'best_index': 1, 'reason': '...'}}"
        payload: List[Any] = [prompt] + images
        response = self.client.models.generate_content(model=self.model_name, contents=payload, config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.2))
        resp_text = safe_extract_text(response)
        if not resp_text: raise ValueError("Vision API empty.")
        return json.loads(resp_text.replace("```json", "").replace("```", ""))

@st.cache_resource
def get_client(): return genai.Client(api_key=GEMINI_API_KEY)
client = get_client()

# ==========================================
# 🧠 SESSION STATE MANAGEMENT (GLOBAL)
# ==========================================
# Single Creator States
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
if "num_images" not in st.session_state: st.session_state.num_images = 4

# Batch States (Scraper)
if "batch_titles" not in st.session_state: st.session_state.batch_titles =[]
if "batch_jobs" not in st.session_state: st.session_state.batch_jobs = {}
if "batch_locked" not in st.session_state: st.session_state.batch_locked = {} 
if "batch_prompts" not in st.session_state: st.session_state.batch_prompts = {} 
if "batch_stage" not in st.session_state: st.session_state.batch_stage = "scrape"
if "batch_num_articles" not in st.session_state: st.session_state.batch_num_articles = 10 

# Globale Prompts
if "prompts" not in st.session_state: st.session_state.prompts = {"Endo Default (Magenta)": FLUX_STYLE_GUIDE}
if "active_prompt_name" not in st.session_state: st.session_state.active_prompt_name = "Endo Default (Magenta)"

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
    st.markdown("Verwalte die globalen Design-Regeln.")
    selected_version = st.selectbox("Style-Profil wählen:", list(st.session_state.prompts.keys()), index=list(st.session_state.prompts.keys()).index(st.session_state.active_prompt_name))
    edited_text = st.text_area("System Instruction (Style Guide):", value=st.session_state.prompts[selected_version], height=150)
    
    st.markdown("<small style='color: #666;'>*Bild-KIs brauchen klare, kommagetrennte Strukturen.*</small>", unsafe_allow_html=True)
    if st.button("🪄 Styleguide für Bild-KIs optimieren", use_container_width=True):
        with st.spinner("Strukturiere Prompt um..."):
            try:
                opt_prompt = f"Convert this messy style guide into a highly structured, machine-readable prompt suffix (comma-separated tags, NO TEXT at the end). USER INPUT: {edited_text}. Return ONLY the optimized text."
                opt_resp = client.models.generate_content(model="gemini-2.5-flash", contents=opt_prompt)
                resp_text = getattr(opt_resp, "text", "") or ""
                st.session_state.prompts[selected_version] = resp_text.strip() if resp_text else edited_text
                st.success("Prompt wurde optimiert!")
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
        if st.button("➕ Als Neues Profil speichern", type="secondary", use_container_width=True) and new_name:
            st.session_state.prompts[new_name] = edited_text
            st.session_state.active_prompt_name = new_name
            st.rerun()

# 🛠️ [FIX 3]: Batch-Prompt Editor Pop-Up (Crasht nicht mehr, da global initialisiert)
@st.dialog("✏️ Prompt bearbeiten (Batch)", width="large")
def batch_prompt_editor_dialog(title: str):
    st.markdown(f"**Artikel:** {title}")
    new_p = st.text_area("Prompt für dieses Bild:", value=st.session_state.batch_prompts.get(title, ""), height=150)
    
    if st.button("💾 Speichern & Bild neu generieren", type="primary", use_container_width=True):
        with st.spinner("Generiere Bild neu..."):
            # Ensure prompt is always a string (coerce None -> "") to satisfy type expectations
            safe_p = str(new_p or "")
            st.session_state.batch_prompts[title] = safe_p
            try:
                imgs = render_images_pipeline(
                    prompt=safe_p, num_images=1, provider="pollinations", target_model="flux", 
                    active_key=POLLINATIONS_API_KEY, api_params={'width': 1024, 'height': 1024}
                )
                if imgs:
                    st.session_state.batch_jobs[title]["image"] = imgs[0]
                    st.session_state.batch_locked[title] = False 
                    st.success("Bild neu generiert!")
                    time.sleep(1)
                    st.rerun()
            except Exception as e:
                st.error(f"Fehler: {e}")

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
    
    # BILDER-GALERIE MIT KLICK-AUSWAHL UND FESTER GRÖSSE
    # Wir begrenzen die Spaltenanzahl dynamisch auf max 4 nebeneinander
    cols = st.columns(min(len(st.session_state.generated_images), 4))
    
    for i, img in enumerate(st.session_state.generated_images):
        with cols[i % 4]:
            # Bild zu Base64 für Custom HTML
            b64 = image_to_base64(img)
            is_selected = (i == st.session_state.best_idx)
            glow_class = "selected-img" if is_selected else ""
            
            # HTML Bild mit max-height für kompaktes Modal
            st.markdown(f'<div class="image-btn-container {glow_class}"><img src="data:image/jpeg;base64,{b64}" style="max-height: 200px; object-fit: contain;"></div>', unsafe_allow_html=True)
            
            # Der unsichtbare Button, der den Klick abfängt
            if i == st.session_state.best_idx:
                st.markdown("<div style='text-align: center; font-size: 24px; margin-top: -15px;'>🏆</div>", unsafe_allow_html=True)
                st.button("✅ Ausgewählt", key=f"sel_btn_{i}", type="primary", use_container_width=True, disabled=True)
            else:
                st.markdown("<br>", unsafe_allow_html=True) # Platzhalter für den fehlenden Pokal
                if st.button("Wählen", key=f"sel_btn_{i}", type="secondary", use_container_width=True):
                    st.session_state.best_idx = i
                    st.rerun()
    
    st.markdown("---")
    st.markdown("#### ✏️ Prompt anpassen & Neu generieren")
    new_prompt = st.text_area("Der generierte Image-Prompt:", value=st.session_state.current_prompt, height=100, label_visibility="collapsed")
    
    col_save_btn, col_gen_btn = st.columns([1, 2])
    with col_save_btn:
        if st.button("💾 Text als Style speichern", type="secondary", use_container_width=True):
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
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 Auswahl veröffentlichen", type="primary", use_container_width=True):
            st.session_state.final_image = apply_ratio_consensus_crop(st.session_state.generated_images[st.session_state.best_idx])
            st.session_state.workflow_stage = "mockup"
            st.session_state.show_selection_dialog = False
            st.rerun()
    with col2:
        if st.button("❌ Abbrechen", type="secondary", use_container_width=True):
            st.session_state.show_selection_dialog = False
            st.rerun()

# ==========================================
# 🖥️ MAIN UI LAYOUT (GLOBAL HEADER)
# ==========================================
logo_b64 = get_local_image_base64("logo")
header_img_html = f'<img src="data:image/png;base64,{logo_b64}" alt="Logo">' if logo_b64 else '<img src="https://cdn-icons-png.flaticon.com/512/3209/3209995.png" alt="Logo">'

st.markdown(f"""
<div class="global-header">
    {header_img_html}
    <h1>Endo Health CMS</h1>
    <p>Smart Content Packaging & Batch Automation</p>
</div>
""", unsafe_allow_html=True)

# Tabs
tab_batch, tab_single, tab_nocode = st.tabs(["🚀 Auto-Batch Scraper (Website)", "✍️ Single-Content Creator", "🧩 Low-Code / No-Code Alternative"])

# ------------------------------------------
# TAB 1: AUTO-BATCH SCRAPER
# ------------------------------------------
with tab_batch:
    _, col_center, _ = st.columns([1, 10, 1])
    
    with col_center:
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.session_state.batch_stage == "scrape":
            with st.container(border=True):
                st.markdown("<h3 style='text-align:center;'>🕸️ Website Scraper</h3>", unsafe_allow_html=True)
                st.markdown("<p style='text-align:center; color:#666;'>Ziehe automatisch Artikel-Titel von endometriose.app und generiere Header in einem Rutsch.</p>", unsafe_allow_html=True)
                
                st.session_state.batch_num_articles = st.slider("Wie viele Artikel sollen geladen werden?", min_value=1, max_value=20, value=10)
                
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🔍 Website Scrapen & Titel extrahieren", type="primary", use_container_width=True):
                    with st.spinner(f"Scrape und filtere {st.session_state.batch_num_articles} Titel..."):
                        try:
                            ext = ExtractionAgent()
                            raw = ext.fetch_raw_data("https://endometriose.app/aktuelles-2/")
                            san = SanitizerAgent()
                            titles = san.filter_titles(client, raw, st.session_state.batch_num_articles)
                            
                            st.session_state.batch_titles = titles
                            st.session_state.batch_jobs = {t: {"status": "pending", "image": None, "prompt": "", "retries": 0} for t in titles}
                            st.session_state.batch_locked = {t: False for t in titles}
                            st.session_state.batch_prompts = {t: "" for t in titles}
                            st.session_state.batch_stage = "generate"
                            st.rerun()
                        except Exception as e:
                            st.error(f"Fehler: {e}")

        elif st.session_state.batch_stage == "generate":
            with st.container(border=True):
                st.markdown("<h3 style='text-align:center;'>🎨 Generiere Bilder...</h3>", unsafe_allow_html=True)

                ad = ArtDirectorAgent(client=client, model_name=MODEL_NAME, style_guide=st.session_state.prompts[st.session_state.active_prompt_name])
                jobs = st.session_state.batch_jobs
                total = len(jobs)
                done = sum(1 for j in jobs.values() if j["status"] == "done")

                progress = st.progress(done / total if total else 0)

                for title, job in jobs.items():
                    if job["status"] == "done": continue
                    try:
                        job["status"] = "running"
                        if not st.session_state.batch_prompts.get(title):
                            camp = ad.create_campaign(title)
                            st.session_state.batch_prompts[title] = camp.get("image_prompt", "")

                        imgs = render_images_pipeline(
                            prompt=st.session_state.batch_prompts[title], num_images=1, provider="pollinations", target_model="flux", 
                            active_key=POLLINATIONS_API_KEY, api_params={'width': 1024, 'height': 1024}
                        )
                        if imgs:
                            job["image"] = imgs[0]
                            job["status"] = "done"
                        else:
                            job["status"] = "failed"
                    except Exception as e:
                        job["retries"] += 1
                        job["status"] = "pending"
                    break  

                done = sum(1 for j in jobs.values() if j["status"] == "done")
                progress.progress(done / total if total else 0)

                if done == total:
                    st.session_state.batch_stage = "review"
                    st.rerun()
                else:
                    time.sleep(1.3)
                    st.rerun()

        elif st.session_state.batch_stage == "review":
            with st.container(border=True):
                all_locked = all(st.session_state.batch_locked.values())
                
                if all_locked:
                    st.success("✅ **Alle Bilder sind markiert!** Du kannst die Auswahl jetzt in den Blog übertragen.")
                    if st.button("🚀 Auswahl bestätigen & Zum Blog Mockup", type="primary", use_container_width=True):
                        st.session_state.batch_stage = "mockup"
                        st.rerun()
                else:
                    st.info("💡 **Aktion erforderlich:** Bitte markiere die Bilder die du behalten willst. Klicke danach unten auf 'Unmarkierte neu generieren'.")
                    if st.button("🔄 Unmarkierte neu generieren", type="secondary", use_container_width=True):
                        for title, job in st.session_state.batch_jobs.items():
                            if not st.session_state.batch_locked[title]:
                                job["status"] = "pending"
                                job["image"] = None
                        st.session_state.batch_stage = "generate"
                        st.rerun()
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            cols = st.columns(2) 
            for idx, (title, job) in enumerate(st.session_state.batch_jobs.items()):
                with cols[idx % 2]:
                    with st.container(border=True):
                        st.markdown(f"<div class='title-container'>{title}</div>", unsafe_allow_html=True)
                        
                        img = job.get("image")
                        if img:
                            thumb = apply_ratio_consensus_crop(img, target_ratio=1.0)
                            b64 = image_to_base64(thumb)
                            is_locked = st.session_state.batch_locked[title]
                            
                            glow_class = "selected-img" if is_locked else ""
                            st.markdown(f'<div class="image-btn-container {glow_class}"><img src="data:image/jpeg;base64,{b64}"></div>', unsafe_allow_html=True)
                            
                            btn_label = "[ ✓ ] Behalten (Klick zum Entfernen)" if is_locked else "[   ] Nicht markiert (Klick zum Behalten)"
                            if st.button(btn_label, key=f"btn_lock_{idx}", type="secondary", use_container_width=True):
                                st.session_state.batch_locked[title] = not is_locked
                                st.rerun()
                                
                            if st.button("✏️ Prompt bearbeiten", key=f"btn_edit_{idx}", type="secondary", use_container_width=True):
                                batch_prompt_editor_dialog(title)

# -----------------------------
# STAGE 4: BLOG BATCH MOCKUP
# -----------------------------
        elif st.session_state.batch_stage == "mockup":
            st.markdown("<h3 style='text-align: center; margin-top:-10px; margin-bottom: 20px;'>🎉 Endo Health - Aktuelles</h3>", unsafe_allow_html=True)
            st.write("So sieht die finale Übersichtsseite aus.")
            
            if st.button("⬅️ Zurück zum Editor", type="secondary"):
                st.session_state.batch_stage = "review"
                st.rerun()
                
            st.markdown("---")
            
            # 🛠️ [FIX]: Native 3er-Grid-Ansicht (Verhindert jegliche HTML/CSS Verzerrung)
            mockup_cols = st.columns(3) 
            
            for idx, (title, job) in enumerate(st.session_state.batch_jobs.items()):
                img = job.get("image")
                if img is not None:
                    # 1. Das Bild in Python auf exakt 16:9 (1.77) croppen
                    cropped_img = apply_ratio_consensus_crop(img, target_ratio=1.77)
                    
                    with mockup_cols[idx % 3]:
                        # 2. Den "Karten"-Look mit nativem Streamlit nachbauen (Schatten via CSS-Hack auf Container-Ebene)
                        with st.container(border=True):
                            # Das Bild passt sich dynamisch der Spaltenbreite an (niemals verzerrt!)
                            st.image(cropped_img, width="stretch")
                            
                            # Der Text-Bereich direkt darunter
                            st.markdown(f"""
                            <div style="padding: 10px 5px 5px 5px; font-family: sans-serif;">
                                <span style="color: #B30047; font-weight: 700; font-size: 11px; text-transform: uppercase; margin-bottom: 8px; display: block;">Wissen & Therapie</span>
                                <h4 style="margin: 0 0 10px 0; color: #1a1a1a; font-size: 16px; line-height: 1.3;">{title}</h4>
                                <a href="#" style="color: #666; font-size: 13px; text-decoration: none; font-weight: 600;">Weiterlesen →</a>
                            </div>
                            """, unsafe_allow_html=True)

# ------------------------------------------
# TAB 2: SINGLE-CONTENT CREATOR
# ------------------------------------------

with tab_single:
    if st.session_state.workflow_stage == "input":
        _, col_main, col_settings, _ = st.columns([1, 4, 3, 1])
        
        with col_main:
            with st.container(border=True):
                st.markdown("<h3 style='text-align: center; margin-top:-10px; margin-bottom: 20px;'>Content Packaging Assistant</h3>", unsafe_allow_html=True)
                
                st.session_state.manual_title_input = st.text_input("Blog-Titel eingeben:", value=st.session_state.manual_title_input, disabled=st.session_state.use_ai_title, placeholder="z.B. Endometriose ist geheilt!")
                
                if st.button("➕ Artikel einfügen (Optional)", type="secondary", use_container_width=True):
                    st.session_state.show_article_input = not st.session_state.show_article_input
                    
                if st.session_state.show_article_input:
                    with st.container():
                        content = st.text_area("Artikel-Text hier einfügen:", height=150, label_visibility="collapsed")
                        if content != st.session_state.blog_content: st.session_state.blog_content = content
                        if st.button("💡 Titel generieren", type="secondary", disabled=not bool(st.session_state.blog_content), use_container_width=True):
                            with st.spinner("KI formuliert Titel..."):
                                tw = TitlewriterAgent(client=client, model_name=MODEL_NAME)
                                st.session_state.generated_titles = tw.generate_titles(st.session_state.blog_content)
                                st.session_state.use_ai_title = True
                                
                if st.session_state.use_ai_title and st.session_state.generated_titles:
                    st.success("Wähle einen der generierten Titel:")
                    st.session_state.blog_title = st.radio("Vorschläge:", st.session_state.generated_titles, label_visibility="collapsed")
                    if st.button("🔄 Manuelle Eingabe wieder aktivieren", type="secondary"):
                        st.session_state.use_ai_title = False
                        st.session_state.generated_titles = []
                        st.rerun()
                else:
                    st.session_state.blog_title = st.session_state.manual_title_input

                st.markdown("<br>", unsafe_allow_html=True)
                generate_btn = st.button("✨ Pipeline Starten", type="primary", use_container_width=True)

        with col_settings:
            with st.container(border=True):
                st.markdown("<h4 style='color: #444; margin-bottom: 15px; margin-top:-5px;'>🛠️ Pipeline Settings</h4>", unsafe_allow_html=True)
                
                # Entstaucht: Jedes Element bekommt wieder seine eigene Zeile
                selected_model = st.selectbox("KI-Modell", ["Flux Schnell", "Flux 2 Dev", "ZImage", "Freepik Mystic"])
                
                api_params = {}
                if selected_model in ["Flux Schnell", "Flux 2 Dev", "ZImage"]:
                    aspect_ratio = st.selectbox("Format", ["Quadratisch (1:1)", "Breitbild (16:9)"])
                    api_params['width'] = 512
                    api_params['height'] = 512 if aspect_ratio == "Quadratisch (1:1)" else 288
                elif selected_model == "Freepik Mystic":
                    style_ref = st.file_uploader("Referenzbild", type=["jpg", "png"])
                    api_params['style_ref'] = image_to_base64(Image.open(style_ref)) if style_ref else None
                
                st.session_state.num_images = st.slider("Anzahl Bilder (Variationen)", 1, 8, 4)
                
                # Separator (---) entfernt für saubereren Flow
                st.markdown("<br>", unsafe_allow_html=True) # Sanfter Abstand
                
                # Dropdown und Button wieder untereinander, aber kompakt
                st.markdown("<small style='font-weight:600; color:#666;'>Aktueller Style-Prompt:</small>", unsafe_allow_html=True)
                new_active_prompt = st.selectbox(
                    "Style wählen", 
                    options=list(st.session_state.prompts.keys()), 
                    index=list(st.session_state.prompts.keys()).index(st.session_state.active_prompt_name),
                    label_visibility="collapsed"
                )
                if new_active_prompt != st.session_state.active_prompt_name:
                    st.session_state.active_prompt_name = new_active_prompt
                    st.rerun()
                
                if st.button("🖋️ Prompt bearbeiten", type="secondary", use_container_width=True):
                    style_editor_dialog()
                
                # Unsichtbarer Spacer, falls Block 1 (durch Text-Eingaben) länger wird.
                # So schließen beide Boxen unten optisch harmonischer ab.
                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

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
            if st.button("⬅️ Neues Cover erstellen", type="secondary"): reset_workflow(); st.rerun()


# ------------------------------------------
# TAB 3: LOW-CODE / NO-CODE ALTERNATIVE
# ------------------------------------------
with tab_nocode:
    _, col_nocode, _ = st.columns([1, 8, 1])
    with col_nocode:
        with st.container(border=True):
            st.markdown("<h3 style='text-align: center;'>🧩 Die Low-Code Architektur</h3>", unsafe_allow_html=True)
            st.markdown("""
            **Vorteile von Rivet/n8n für Endo Health:**
            1. **Wartbarkeit:** Das Content-Team kann den "Art Director Prompt" oder die API-Endpunkte visuell anpassen, ohne einen Developer zu brauchen.
            2. **Integration:** Wir können den Output-Node direkt an das echte CMS (z.B. Webflow, WordPress, Contentful) von Endo Health anbinden.
            3. **Skalierbarkeit:** Webhooks triggern den Agent-Swarm vollautomatisch, sobald ein Redakteur auf "Artikel speichern" klickt.
            """)
            st.markdown("---")
            st.markdown("#### Beispiel-Architektur (FreePik Workflow)")
            try:
                nocode_img_b64 = get_local_image_base64("no-code_WORKFLOW")
                if nocode_img_b64:
                    st.markdown(f'<img src="data:image/png;base64,{nocode_img_b64}" style="width: 100%; border-radius: 8px; border: 1px solid #EAEAEA;">', unsafe_allow_html=True)
            except Exception:
                st.info("Bitte lade ein Bild mit dem Namen `no-code_WORKFLOW.png` hoch.")

with tab_nocode:
    _, col_nocode, _ = st.columns([1, 8, 1])
    with col_nocode:
        with st.container(border=True):                
            st.markdown("---")
            st.markdown("""
                        1. Der grüne Block zeigt die Streamline für den Avatar. 
                        2. Im Gelben Block wird der Titel definiert und/oder mit dem frisch verfassten Artikel und dem AVATAR in Kontext gesetzt damit der Prompt Agent die Instruktionen für den Bildgenerator Agenten formulieren kann. 
                        3. Der blaue Block zeigt die Bildgenerierung via FreePik API. Sobald das Bild generiert ist, wird es automatisch in das CMS gepusht und im Artikel angezeigt.""")
