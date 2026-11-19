import streamlit as st
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def get_youtube_service():
    """Use the channel's existing refresh-token credentials, as in HBD_Songs."""
    try:
        creds = Credentials(
            token=None,
            refresh_token=st.secrets["YOUTUBE_REFRESH_TOKEN"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=st.secrets["YOUTUBE_CLIENT_ID"],
            client_secret=st.secrets["YOUTUBE_CLIENT_SECRET"],
            scopes=SCOPES,
        )
        if not creds.valid:
            creds.refresh(Request())
        return build("youtube", "v3", credentials=creds)
    except Exception as exc:
        raise RuntimeError(f"Could not authenticate with YouTube: {exc}") from exc


def upload_video(video_path: str, title: str, description: str = "") -> str:
    """Upload a puzzle video; audience setting is explicitly marked Made for Kids."""
    try:
        youtube = get_youtube_service()
        body = {
            "snippet": {
                "title": title[:100],
                "description": description,
                "tags": ["kids quiz", "puzzles for kids", "preschool learning", "fun quiz", "animals", "colours", "shapes"],
                "categoryId": "27",
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": True,
            },
        }
        media = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True, chunksize=5 * 1024 * 1024)
        request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
        response = None
        while response is None:
            _, response = request.next_chunk()
        return f"https://www.youtube.com/watch?v={response['id']}"
    except Exception as exc:
        raise RuntimeError(f"YouTube upload failed: {exc}") from exc
