# Kids Puzzle Video Generator

A standalone Streamlit app that reads quiz rows from Google Sheets, builds a colorful 720p MP4, optionally uploads it to YouTube, and emails the admin/requester. It does not modify the working HBD_Songs repository.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

FFmpeg must be installed and available on `PATH` for MoviePy to render MP4.

## Google Sheet

Create a worksheet named `Questions` (or configure `questions_worksheet` in secrets) with these exact headers in row 1:

`Question | OptionA | OptionB | OptionC | Correct | Category`

Share the spreadsheet with the service-account email as a Viewer. At least 10 valid questions are required. The `Correct` cell must match one of the three option values (case-insensitive). The app samples ten questions from the selected category; a category must itself contain ten or more questions if filtered.

## Streamlit secrets

Reuse corresponding credentials from HBD_Songs, entered privately in this app's Streamlit secrets:

```toml
[sheets]
spreadsheet_id = "YOUR_GOOGLE_SPREADSHEET_ID"
questions_worksheet = "Questions"
service_account = '''{"type":"service_account", ...}'''

YOUTUBE_CLIENT_ID = "..."
YOUTUBE_CLIENT_SECRET = "..."
YOUTUBE_REFRESH_TOKEN = "..."
EMAIL_ADDRESS = "sender@gmail.com"
EMAIL_PASSWORD = "gmail_app_password"
ADMIN_EMAIL = "admin@example.com"
```

YouTube uploads are explicitly marked `selfDeclaredMadeForKids = true`; confirm the channel's audience and other upload settings before publishing.

## Video format

The episode begins and ends with a friendly title slide. Each question displays three large choices and a 10-second animated progress bar, followed by a highlighted correct answer. Rendered video is H.264 MP4, 1280x720, 24 fps. Optional background images can be placed in `assets/backgrounds/`; pastel fallback backgrounds are generated when no images are present. Optional fonts are read from `assets/fonts/`.

## Deployment notes

Configure the Google Sheets service account, YouTube OAuth refresh token, and SMTP app password as Streamlit secrets; do not commit credentials. Test with YouTube upload disabled first. Google/YouTube account upload limits still apply.
