import os
from pathlib import Path
import yaml
from fastapi import FastAPI, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import storage
from src.image_utils import PostManager
from src.models import PostInfo
import uvicorn

app = FastAPI()
origins = ["http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BUCKET_NAME = "{{ PROJECT_ID }}-images"
UNPROCESSED_DIR = "test/unprocessed"
# app.upload_status = {"data": "idle"}  # idle, uploading, complete

@app.get("/api/")
async def root():
    return {"message": "Welcome to Instagram Poster!"}

@app.get("/api/uploadstatus/")
async def get_upload_status() -> dict:
    pm = PostManager(BUCKET_NAME)
    file_names = pm.get_file_names(UNPROCESSED_DIR)
    ids = pm.get_image_file_ids(file_names)
    max_id = pm.get_max_id(ids)
    return {"data": max_id}


@app.post("/api/uploadimages/")
async def create_files(files: list[UploadFile], caption: str = Form(...), location: str = Form(...), hashtags: str = Form(...), image_order: list[str] = Form(...)):
    files, id = get_new_file_names(files, image_order)

    post_details = PostInfo(
        caption=caption,
        location=location,
        hashtags=hashtags.split(),
    )
    upload_post_details(post_details, path=f"{UNPROCESSED_DIR}/{id}.yaml")
    upload_images(files)
    return {"data": "Upload Complete!"}


def get_new_file_names(files: list[UploadFile], image_order: list[str]) -> list[str]:
    pm = PostManager(BUCKET_NAME)
    file_names = pm.get_file_names(UNPROCESSED_DIR)
    ids = pm.get_image_file_ids(file_names)
    id = pm.get_max_id(ids) + 1

    sorted_files = [" "] * len(files)
    for file in files:
        i = image_order.index(file.filename)
        sorted_files[i] = file

    for i, file in enumerate(sorted_files):
        file.filename = f"{id}_{i}_{file.filename}"

    return sorted_files, id


def upload_post_details(post_info: PostInfo, path: str):
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    file_path = Path(path)

    blob = bucket.blob(str(file_path))
    ext = file_path.suffix.lstrip(".")
    content = yaml.dump(dict(post_info), indent=4)

    blob.upload_from_string(data=content, content_type=f"application/{ext}")

    return True


def upload_images(files: list[UploadFile]):
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    for file in files:
        blob = bucket.blob(f"{UNPROCESSED_DIR}/{file.filename}")
        blob.upload_from_file(file.file, content_type=f'image/{Path(file.filename).suffix}')
    return True

if __name__ == "__main__":
    uvicorn.run("main:app", port=8000, reload=True)
