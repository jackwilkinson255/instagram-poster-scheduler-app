from dataclasses import dataclass
from pathlib import Path
from pydantic import BaseModel


class InstaUpload(BaseModel):
    images: list[str]
    bucket: str
    project: str


@dataclass
class ImageDirectories:
    unprocessed: Path
    down_sampled: Path
    processed: Path
