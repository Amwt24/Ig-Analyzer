import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "IG Modular Monolith Scraper"
    IG_USERNAME: str = os.getenv("IG_USERNAME", "")
    IG_PASSWORD: str = os.getenv("IG_PASSWORD", "")
    IG_COOKIE_STRING: str = os.getenv("IG_COOKIE_STRING", "")
    MONGODB_URI: str = os.getenv("MONGODB_URI", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    SESSION_FILE: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "session_state.json")
    
settings = Settings()
