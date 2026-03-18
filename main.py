import sys
from google import genai

# Import configurations
from config import GEMINI_API_KEY, MODEL_NAME, TARGET_URL, OUTPUT_DIR, FLUX_STYLE_GUIDE

# Import agents
from agents.extractor import ExtractionAgent
from agents.sanitizer import SanitizerAgent
from agents.art_director import ArtDirectorAgent
from agents.renderer import RenderAgent
from config import GEMINI_API_KEY, POLLINATIONS_API_KEY, MODEL_NAME, TARGET_URL, OUTPUT_DIR, FLUX_STYLE_GUIDE
# ...

def main():
    print("🚀 Initiating Endo Health Agent Swarm Framework...\n")
    
    try:
        # 1. Initialize API Client
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # 2. Instantiate Agents
        extractor = ExtractionAgent(url=TARGET_URL)
        sanitizer = SanitizerAgent(client=client, model_name=MODEL_NAME)
        art_director = ArtDirectorAgent(client=client, model_name=MODEL_NAME, style_guide=FLUX_STYLE_GUIDE)
        renderer = RenderAgent(output_dir=OUTPUT_DIR, api_key=POLLINATIONS_API_KEY)

        
        # 3. Execute Pipeline
        raw_data = extractor.fetch_raw_data()
        
        clean_titles = sanitizer.filter_titles(raw_data)
        
        campaign = art_director.create_campaign(clean_titles)
        
        renderer.render_images(campaign)
        
        print(f"\n🎉 Swarm Execution completed successfully. Outputs saved to '{OUTPUT_DIR}'.")
        
    except Exception as e:
        print(f"\n❌ CRITICAL PIPELINE FAILURE: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()