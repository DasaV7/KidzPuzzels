import os
import random
from datetime import datetime

import streamlit as st

from services.notification_service import send_email_notification
from services.puzzle_video_service import create_puzzle_video, safe_video_filename
from services.sheets_service import get_questions
from services.youtube_service import upload_video

os.makedirs("generated", exist_ok=True)

st.set_page_config(page_title="Kids Puzzle Video Generator", page_icon="🧩", layout="centered")
st.markdown("""
<style>
.main-title {font-size:2.2rem;font-weight:800;text-align:center;margin-bottom:.2rem;color:#6A1B9A;}
.sub-title {text-align:center;color:#666;margin-bottom:1.4rem;}
.stButton>button {border-radius:10px;font-weight:700;}
</style>
""", unsafe_allow_html=True)
st.markdown('<div class="main-title">🧩 Kids Puzzle Video Generator</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">A cheerful 10-question quiz for little learners</div>', unsafe_allow_html=True)
st.info("Each episode uses 10 questions from your Google Sheet. Children see three choices, get 10 seconds to think, then the correct answer is revealed.")

with st.sidebar:
    st.header("Episode settings")
    upload_enabled = st.checkbox("Upload finished video to YouTube", value=True)
    notify_email = st.text_input("Notify user email (optional)", placeholder="parent@example.com")
    video_title = st.text_input("YouTube title", value="Fun Kids Quiz! 10 Easy Puzzles for Little Learners")

if "questions" not in st.session_state:
    st.session_state.questions = []
if "puzzle_result" not in st.session_state:
    st.session_state.puzzle_result = None

col_a, col_b = st.columns(2)
with col_a:
    if st.button("📥 Load questions from Google Sheets", use_container_width=True):
        try:
            with st.spinner("Connecting to Google Sheets and checking question rows..."):
                st.session_state.questions = get_questions()
            categories = sorted({row["Category"] for row in st.session_state.questions})
            st.success(f"Loaded {len(st.session_state.questions)} valid questions across {len(categories)} categories.")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))
with col_b:
    if st.button("🧹 Clear loaded questions", use_container_width=True):
        st.session_state.questions = []
        st.session_state.puzzle_result = None
        st.rerun()

questions = st.session_state.questions
if questions:
    categories = sorted({row["Category"] for row in questions})
    category_filter = st.selectbox("Question category", ["All categories"] + categories, key="category_choice")
    eligible = questions if category_filter == "All categories" else [q for q in questions if q["Category"] == category_filter]
    st.caption(f"{len(eligible)} questions available for this selection. The video always contains exactly 10.")
    if len(eligible) < 10:
        st.warning("Choose another category or add more rows: at least 10 questions are needed in the selected set.")
    st.dataframe(eligible[:25], use_container_width=True, hide_index=True)

    if st.button("🎬 Create 10-question video" + (" and upload" if upload_enabled else ""),
                 type="primary", use_container_width=True, disabled=len(eligible) < 10):
        chosen = random.sample(eligible, 10)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        video_path = f"generated/{safe_video_filename(video_title)}_{timestamp}.mp4"
        try:
            with st.status("Creating your puzzle episode...", expanded=True) as status:
                st.write("Drawing colorful question and answer slides...")
                video_path, _ = create_puzzle_video(chosen, output_path=video_path)
                status.update(label="Video rendered", state="complete")
            youtube_url = None
            if upload_enabled:
                with st.status("Uploading to YouTube...", expanded=True) as status:
                    youtube_url = upload_video(
                        video_path,
                        video_title,
                        "A fun, family-friendly quiz for preschool learners. Ten simple questions with three choices and time to think.\n\n#KidsQuiz #PreschoolLearning #KidsPuzzles",
                    )
                    status.update(label="Video uploaded", state="complete")
                try:
                    send_email_notification(notify_email, youtube_url, video_title)
                    st.success("Email notification sent to the configured admin and user address (if provided).")
                except Exception as exc:
                    st.warning(f"Video uploaded, but email notification could not be sent: {exc}")
            st.session_state.puzzle_result = {"video_path": video_path, "youtube_url": youtube_url, "title": video_title}
            st.success("Puzzle video is ready!")
        except Exception as exc:
            st.error(f"Video workflow failed: {exc}")

result = st.session_state.puzzle_result
if result:
    st.markdown("---")
    st.subheader("Latest video")
    if os.path.exists(result["video_path"]):
        st.video(result["video_path"])
        with open(result["video_path"], "rb") as video_file:
            st.download_button("⬇️ Download MP4", video_file, file_name=os.path.basename(result["video_path"]), mime="video/mp4")
    if result.get("youtube_url"):
        st.markdown(f"[▶ Watch on YouTube]({result['youtube_url']})")
