import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("CRITICAL ERROR: GEMINI_API_KEY is missing in the environment.")

# Lade alle drei Bild-Generator Keys
POLLINATIONS_API_KEY = os.getenv("POLLINATIONS_API_KEY", "")
POLLI_FLUX2_API_KEY = os.getenv("POLLI_FLUX2_API_KEY", "")
POLLI_ZIMAGE_API_KEY = os.getenv("POLLI_ZIMAGE_API_KEY", "")
FREEPIK_API_KEY = os.getenv("FREEPIK_API_KEY", "")

# Globale Settings
MODEL_NAME = "gemini-3.1-flash-lite-preview"
OUTPUT_DIR = "endo_headers"
TARGET_URL = "https://endometriose.app/aktuelles-2/"

# Strikter Styleguide für den Image Generator
FLUX_STYLE_GUIDE = (
    "Minimalist 2D flat vector illustration, digital health app aesthetic. "
    "Color palette: deep magenta, raspberry red, soft pastel pinks, and warm skin tones. "
    "Clean white background. Subjects are often centered inside a soft, pale pink circular backdrop. "
    "Simple, approachable, and empathetic medical illustration style. "
    "Solid colors with minimal shading. ABSOLUTELY NO TEXT, NO WORDS, NO LETTERS."
)