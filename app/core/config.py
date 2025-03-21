import os
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

class Settings:
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "JAN Code Estimation API"
    
    # OpenAI API設定
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # JANCODE LOOKUP API設定
    JANCODE_API_URL: str = "https://api.jancodelookup.com/"
    JANCODE_API_APP_ID: str = os.getenv("JANCODE_API_APP_ID", "")
    
    # JANコード推定設定
    MAX_CANDIDATES: int = 5  # 最大候補数

settings = Settings()