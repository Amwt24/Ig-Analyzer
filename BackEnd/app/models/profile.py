from pydantic import BaseModel
from typing import Optional, List

class Comment(BaseModel):
    username: str
    text: str
    sentiment: Optional[str] = None  # "positive" | "negative" | "neutral"

class SentimentAnalysis(BaseModel):
    acceptance_score: float = 0.0  # 0-100%
    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0
    total_comments: int = 0
    summary: str = ""  # Texto descriptivo generado por el LLM

class Post(BaseModel):
    url: str
    image_url: Optional[str] = None
    caption: Optional[str] = None
    comments: Optional[List[Comment]] = []

class ProfileStats(BaseModel):
    username: str
    display_name: str
    followers: str
    following: str
    posts: str
    profile_pic_url: str
    raw_desc: Optional[str] = None
    biography: Optional[str] = None
    category: Optional[str] = None
    external_url: Optional[str] = None
    recent_posts: Optional[List[Post]] = []
