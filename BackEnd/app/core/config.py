import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "IG Modular Monolith Scraper"
    IG_USERNAME: str = os.getenv("IG_USERNAME", "")
    IG_PASSWORD: str = os.getenv("IG_PASSWORD", "")
    IG_COOKIE_STRING: str = os.getenv("IG_COOKIE_STRING", "")
    MONGODB_URI: str = os.getenv("MONGODB_URI", "")
    SESSION_FILE: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "session_state.json")
    
    def __init__(self):
        # Buscar ScraperIG/.env en la raíz del proyecto
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        old_env_path = os.path.join(base_dir, "ScraperIG", ".env")
        if os.path.exists(old_env_path):
            from dotenv import load_dotenv
            load_dotenv(old_env_path, override=False)
            self.IG_COOKIE_STRING = os.getenv("IG_COOKIE_STRING", "")
    
settings = Settings()
