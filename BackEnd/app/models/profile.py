from pydantic import BaseModel
from typing import Optional, List

class Comment(BaseModel):
    username: str
    text: str

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

