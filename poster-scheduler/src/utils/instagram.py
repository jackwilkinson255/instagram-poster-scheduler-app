import time
import os
from datetime import datetime
from enum import auto, Enum
from functools import cache
from pathlib import Path
from tenacity import retry, stop_after_attempt, wait_random
from src.utils.cloud_storage import CloudStorageAdapter
from instagrapi import Client
from instagrapi.types import (
    Location,
    StoryHashtag,
    StoryLocation,
    Media,
    Story,
    Highlight,
)
from src.utils.misc import get_credentials_secret, get_current_service_account
import logging
import random
from src.utils.hash_tags import (
    STREET_PHOTOGRAPHY_HASH_TAGS,
    GENERIC_HASH_TAGS,
    PHOTOGRAPHY_HASH_TAGS,
    FUJIFILM_HASH_TAGS,
)

logger = logging.getLogger("insta_poster_logger")

POST_DELAY_MIN = 4
POST_DELAY_MAX = 7
TEST_ACCOUNTS = []
TEST_ACCOUNT = TEST_ACCOUNTS[1]


class InstagramType(Enum):
    POST = auto()
    ALBUM = auto()
    STORY = auto()
    HIGHLIGHT = auto()


class InstagramAdapter:
    def __init__(
        self,
        bucket: str,
        account: str = "test",
        upload_type: str = "post",
        project: str = None,
        highlight: str = None,
        login: bool = True,
    ):
        self.media = None
        self.username = None
        self.bucket = bucket
        self.account = account
        self.upload_type = upload_type
        self.gcs = CloudStorageAdapter(bucket)
        get_current_service_account()
        self.session_path = Path(f"{account}/session.json")
        if login:
            self.project = project
            self.cl = Client(delay_range=[2, 5])
            self.setup_connection()
            self.user_id = self.cl.user_id_from_username(self.username)
        self.highlight = highlight
        self.highlight_pk_path = Path(f"{account}/highlights.json")
        self.story = None
        self.date_fmt = "%y-%m-%d %H:%M:%S"

    def setup_connection(self):
        test_acct = True if self.account == "test" else False
        self.username, password = get_credentials_secret(test_acct, self.project)
        if test_acct:
            self.username = TEST_ACCOUNT

        if self.gcs.blob_exists(self.session_path):
            logger.info("Previous session found, using to log in...")
            self.relogin(password)
        else:
            self.fresh_login(password)

        self.check_login(password)

    def fresh_login(self, password: str):
        self.session_path.parent.mkdir(exist_ok=True, parents=True)
        settings = self.cl.get_settings()
        settings["country"] = "GB"
        settings["country_code"] = 44
        settings["locale"] = "en_GB"
        settings["timezone_offset"] = 0
        settings["device_settings"]["app_version"] = "302.1.0.36.111"
        settings["device_settings"]["model"] = "GM1913"
        settings["device_settings"]["dpi"] = ("560dpi",)
        settings["device_settings"]["resolution"] = "3120x1440"
        settings["device_settings"]["android_version"] = 12
        settings["device_settings"]["android_release"] = "9.0.0"
        settings[
            "user_agent"
        ] = f'Instagram {settings["device_settings"]["app_version"]} \
        Android ({settings["device_settings"]["android_version"]}/{settings["device_settings"]["android_release"]}; \
        {settings["device_settings"]["dpi"]}; {settings["device_settings"]["resolution"]}; OnePlus;\
         {settings["device_settings"]["model"]}; devitron; qcom; {settings["locale"]}; 314665256)'

        self.gcs.upload_json(self.session_path, settings)
        self.login(self.username, password, relogin=False)

    def relogin(self, password: str):
        settings = self.gcs.download_json_blob(self.session_path)
        self.cl.set_settings(settings)
        self.login(self.username, password, relogin=True)

    def login(self, username: str, password: str, relogin: bool = False):
        try:
            self.cl.login(username, password, relogin=relogin)
        except:
            raise ValueError("Could not log in!")

    @retry(stop=stop_after_attempt(1), wait=wait_random(min=3, max=6))
    def check_login(self, password: str):
        logger.info("Attempting relogin...")
        self.relogin(password)

    @staticmethod
    def next_proxy() -> str:
        """Does not need instagram to be logged in"""
        logger.info("Changing proxy...")
        return random.choice(
            [
                "http://123.com",
                "http://123.com",
                "http://123.com",
            ]
        )

    def parse_json_contents(self, contents: str) -> tuple[str]:
        """Does not need instagram to be logged in"""
        loc_obj = self.get_location_obj(contents["location"])
        hash_tags = self.get_hash_tags(contents["hashtags"])
        return contents["caption"], loc_obj, hash_tags

    def get_hash_tags(self, req_hash_tags: list[str]) -> str:
        """Does not need instagram to be logged in"""
        hash_tags_str = ""
        max_hash_tags = 30
        hash_tags = req_hash_tags

        while len(hash_tags) < max_hash_tags:
            hash_tags = list(set(hash_tags))
            for default_hash_tags in [
                STREET_PHOTOGRAPHY_HASH_TAGS,
                GENERIC_HASH_TAGS,
                PHOTOGRAPHY_HASH_TAGS,
                FUJIFILM_HASH_TAGS,
            ]:
                hash_tags.append(random.choice(default_hash_tags))

        if self.upload_type == "post":
            for hash_tag in hash_tags:
                hash_tags_str = hash_tags_str + f"#{hash_tag} "
            return hash_tags_str
        else:
            return hash_tags

    def upload_pictures_to_story(
        self,
        _path: Path,
        file_names: list[str],
        caption: str = "",
        loc_obj: Location = None,
        hashtags: str = None,
        highlight: str = None,
    ):
        for idx, file_name in enumerate(file_names):
            self.upload_picture_to_story(
                _path, file_name, idx, caption, loc_obj, hashtags, highlight
            )

    def upload_picture_to_story(
        self,
        path_: Path,
        file_name: str,
        idx: int,
        caption: str = None,
        loc_obj: Location = None,
        hashtags: str = None,
        highlight: str = None,
    ):
        file_path = path_.joinpath(file_name)
        first_image = idx == 0
        # time.sleep(random.randint(POST_DELAY_MIN, POST_DELAY_MAX))  # Small delay between story uploads
        # First image differs as we need to add hashtag and location stickers to it
        if first_image:
            self.create_new_story(hashtags, file_name, file_path, loc_obj)
            if highlight:
                if highlight == "new":
                    self.create_new_highlight(loc_obj, caption, file_name)

                else:
                    self.add_to_existing_highlight(highlight, file_name)
        else:
            logger.info(f"Uploading '{file_name}' to story...")
            self.story = self.cl.photo_upload_to_story(file_path)

            if highlight:
                if highlight == "new":
                    logger.info(
                        f"Adding '{file_name}' story to highlight with pk '{self.highlight.pk}'..."
                    )
                    self.cl.highlight_add_stories(self.highlight.pk, [self.story.id])
                else:
                    self.add_to_existing_highlight(highlight, file_name)

    def create_new_story(
        self, hashtags: str, file_name: str, file_path: str, loc_obj: Location
    ):
        hashtag_objs = self.get_story_hashtag_list(hashtags)
        logger.info(f"Adding '{file_name}' to story...")
        # Only add location to first story
        loc_story_obj = (
            [StoryLocation(location=loc_obj, x=0.5, y=0.5, width=20, height=20)]
            if loc_obj
            else None
        )
        self.story = self.cl.photo_upload_to_story(
            path=file_path, hashtags=hashtag_objs, locations=loc_story_obj
        )

    def create_new_highlight(self, loc_obj: Location, caption: str, file_name: str):
        # We also need to add the new highlight PK to our database
        logger.info(f"Adding '{file_name}' story to highlight...")
        # hc_args = {
        #     "title": "" if not loc_obj else loc_obj.name,
        #     "story_ids": [self.story.id],
        # }
        print(self.story.id)
        self.highlight = self.cl.highlight_create(
            title="" if not loc_obj else loc_obj.name, story_ids=[self.story.id]
        )
        self.save_highlight_pk(self.highlight.pk, self.story.id, caption)
        logger.info(f"Highlight pk is: '{self.highlight.pk}'.")

    def add_to_existing_highlight(self, highlight: str, file_name: str):
        if highlight == "latest":
            latest_highlight = self.get_latest_highlight_pk()
            logger.info(
                f"Adding '{file_name}' story to latest highlight {latest_highlight}..."
            )
            self.cl.highlight_add_stories(latest_highlight, [self.story.id])

        elif highlight.isnumeric():
            self.validate_highlight_pk(highlight)
            logger.info(
                f"Adding '{file_name}' story to highlight existing {highlight}..."
            )
            self.cl.highlight_add_stories(highlight, [self.story.id])

    def save_highlight_pk(self, highlight_pk: str, story_id: str, caption: str):
        highlight_pks = {}
        if self.highlight_pk_path in self.gcs.list_blobs(self.highlight_pk_path):
            highlight_pks = self.gcs.download_json_blob(self.highlight_pk_path)

        highlight_pks[highlight_pk] = {
            "story_id": story_id,
            "caption": caption,
            "created_at": datetime.now().strftime(self.date_fmt),
        }
        self.gcs.upload_json(self.highlight_pk_path, highlight_pks)

    def validate_highlight_pk(self, highlight_pk) -> bool:
        if self.highlight_pk_path not in self.gcs.list_blobs(self.highlight_pk_path):
            raise FileExistsError(f"File {self.highlight_pk_path} not found!")
        else:
            highlight_pks = self.gcs.download_json_blob(self.highlight_pk_path)

        if highlight_pk not in highlight_pks:
            raise ValueError(f"Highlight PK {highlight_pk} not found!")

        return True

    @cache
    def get_latest_highlight_pk(self) -> str:
        highlight_pks = self.gcs.download_json_blob(self.highlight_pk_path)
        max_highlight_pk = None
        max_created_at = None
        for highlight_pk, content in highlight_pks.items():
            created_at = datetime.strptime(content["created_at"], self.date_fmt)
            if max_created_at is None:
                max_created_at = created_at
                max_highlight_pk = highlight_pk
            if created_at > max_created_at:
                max_created_at = created_at
                max_highlight_pk = highlight_pk

        return max_highlight_pk

    def get_story_hashtag_list(self, hashtags: list[str]) -> list[StoryHashtag]:
        logger.info("Creating StoryHashtag list...")
        num_tags = 3
        story_hashtags = []

        for tag in hashtags[:num_tags]:
            story_hashtags.append(
                StoryHashtag(
                    hashtag=self.cl.hashtag_info(tag),
                    x=random.randint(10, 200),
                    y=random.randint(10, 200),
                    width=10,
                    height=10,
                )
            )
            time.sleep(random.randint(POST_DELAY_MIN, POST_DELAY_MAX))

        return story_hashtags

    def upload_picture(self, _path, file_name, caption=None, loc_obj=None):
        file_path = _path.joinpath(file_name)
        self.media = self.cl.photo_upload(
            path=str(file_path), caption=caption, location=loc_obj
        )

        if not self.successful_upload(pk=self.media.pk):
            raise AssertionError("Instagram picture upload failed!")

    def upload_album(self, path_, file_names, caption=None, loc_obj=None):
        paths = []
        for file in file_names:
            paths.append(os.path.join(path_, file))
        self.media = self.cl.album_upload(
            paths=paths, caption=caption, location=loc_obj
        )
        if not self.successful_upload(pk=self.media.pk):
            raise AssertionError("Instagram album upload failed!")

    def get_location_obj(self, location: str) -> Location:
        loc_info = {}
        keys_required = ["pk", "name", "lng", "lat"]
        search_info = dict(self.cl.fbsearch_places(location)[0])
        for key in keys_required:
            loc_info[key] = search_info[key]
        return Location(
            pk=loc_info["pk"],
            name=loc_info["name"],
            lat=loc_info["lat"],
            lng=loc_info["lng"],
        )

    def add_comment(self, comment: str):
        id = self.media.id
        self.cl.media_comment(id, comment)

    def successful_upload(self, pk: str) -> bool:
        user_id = self.cl.user_id_from_username(self.username)
        user_medias = self.cl.user_medias(user_id=user_id)
        for media in user_medias:
            if pk == media.pk:
                return True
        return False

    def list_users_media(self, media_type: InstagramType, user_id: str = ""):
        if not user_id:
            user_id = self.user_id
        match media_type:
            case InstagramType.POST:
                for media in self.cl.user_medias(user_id):
                    yield media
            case InstagramType.ALBUM:
                for media in self.cl.user_medias(user_id):
                    yield media
            case InstagramType.STORY:
                for media in self.cl.user_stories(user_id):
                    yield media
            case InstagramType.HIGHLIGHT:
                for media in self.cl.user_highlights(user_id):
                    yield media

    def delete_users_media(self, media):
        if self.account != "test":
            return
        result = False
        id = ""
        result_type = ""
        if isinstance(media, Media):
            id = media.id
            result_type = "media"
            result = self.cl.media_delete(media_id=id)
        elif isinstance(media, Story):
            id = media.pk
            result_type = "story"
            result = self.cl.story_delete(story_pk=id)
        elif isinstance(media, Highlight):
            id = media.pk
            result_type = "highlight"
            result = self.cl.highlight_delete(highlight_pk=id)

        if result:
            logger.info(f"Deleted {result_type} with id: {id}")
        else:
            logger.warning(f"Failed to delete {result_type} with id: {id}")
