from pydantic import BaseModel
from typing import Optional

class ProfileStats(BaseModel):
    username: str
    display_name: str
    followers: str
    following: str
    posts: str
    profile_pic_url: str
    raw_desc: Optional[str] = None
