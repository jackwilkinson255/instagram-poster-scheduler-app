from pydantic import BaseModel


class PostInfo(BaseModel):
    caption: str
    location: str
    hashtags: list[str]