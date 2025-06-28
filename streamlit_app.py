import streamlit as st
from yt_dlp import YoutubeDL
import os
import re
import ffmpeg

# App config
st.set_page_config(page_title="🎬 YouTube Downloader & Editor", page_icon="🎬")
st.title("🎬 Free YouTube Downloader & Editor")

# Ensure download directory
os.makedirs("downloads", exist_ok=True)

# Helpers
def trim_with_ffmpeg(input_path: str, start: str, end: str) -> str:
    base, ext = os.path.splitext(input_path)
    output_path = f"{base}_trimmed{ext}"
    ffmpeg.input(input_path, ss=start, to=end).output(output_path).run()
    return output_path

def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "_", name)

def fetch_video_titles(url: str) -> list[str]:
    with YoutubeDL({'quiet': True, 'extract_flat': True}) as ydl:
        info = ydl.extract_info(url, download=False)
        if 'entries' in info:
            return [sanitize_filename(e['title']) for e in info['entries']]
        else:
            return [sanitize_filename(info['title'])]

def download_video(url: str, target_format: str = "mp4", selected_titles: list[str] = None) -> list[str]:
    downloaded_files = []

    ydl_opts = {
        "outtmpl": "downloads/%(title)s.%(ext)s",
        "quiet": True,
        "noplaylist": False,
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4",
        "merge_output_format": "mp4",
        "postprocessors": [{
            "key": "FFmpegVideoConvertor",
            "preferedformat": "mp4"
        }],
    }

    if target_format == "mp3":
        ydl_opts["format"] = "bestaudio"
        ydl_opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        entries = info["entries"] if "entries" in info else [info]

        for entry in entries:
            title = sanitize_filename(entry.get("title", "video"))
            if selected_titles and title not in selected_titles:
                continue
            ext = "mp3" if target_format == "mp3" else "mp4"
            filepath = os.path.join("downloads", f"{title}.{ext}")
            downloaded_files.append(filepath)

    return downloaded_files


# Convert video format
def convert_format(input_path: str, target_format: str, base_name: str) -> str:
    output_path = os.path.join("downloads", f"{base_name}.{target_format}")
    ffmpeg.input(input_path).output(output_path).run()
    return output_path

# Extract audio
def extract_audio(input_path: str, base_name: str) -> str:
    output_path = os.path.join("downloads", f"{base_name}.mp3")
    ffmpeg.input(input_path).output(output_path).run()
    return output_path

# Merge multiple videos
def merge_videos(paths: list[str]) -> str:
    list_path = "merge_list.txt"
    # 🔧 Fix: Write using UTF-8 encoding to support special characters
    with open(list_path, "w", encoding="utf-8") as f:
        for p in paths:
            f.write(f"file '{p}'\n")
    output_path = "downloads/merged_output.mp4"
    ffmpeg.input(list_path, format="concat", safe=0).output(output_path, c="copy").run()
    return output_path

# Trim video
def trim_video(input_path: str, start_time: str, end_time: str, base_name: str) -> str:
    output_path = os.path.join("downloads", f"{base_name}_trimmed.mp4")
    ffmpeg.input(input_path, ss=start_time, to=end_time).output(output_path).run()
    return output_path

# --- UI Begins ---

option = st.radio("Select operation:", ["Download", "Convert Format", "Extract Audio", "Merge Videos"])

# Download section
if option == "Download":
    url = st.text_input("Enter YouTube video or playlist URL")
    target_format = st.selectbox("Choose format", ["mp4", "mp3"])

    st.markdown("**Optional: Trim Video**")
    start_time = st.text_input("Start time (HH:MM:SS)", value="00:00:00")
    end_time = st.text_input("End time (HH:MM:SS)", value="")
    apply_trim = st.checkbox("Trim video after download")

    if st.button("Download"):
        if url:
            with st.status("Starting download...", expanded=True) as status:
                try:
                    status.write("🔗 Downloading...")
                    paths = download_video(url, target_format)

                    for path in paths:
                        final_path = path
                        base_name = os.path.splitext(os.path.basename(path))[0]

                        if apply_trim and end_time:
                            status.write(f"✂️ Trimming from {start_time} to {end_time}...")
                            final_path = trim_video(path, start_time, end_time, base_name)
                            st.success(f"✅ Trimmed video: {os.path.basename(final_path)}")
                        else:
                            st.success(f"✅ Downloaded: {os.path.basename(final_path)}")

                        with open(final_path, "rb") as f:
                            st.download_button("Download", f, file_name=os.path.basename(final_path))

                    status.update(label="✅ All Done", state="complete", expanded=False)
                except Exception as e:
                    status.update(label="❌ Error", state="error")
                    st.error(f"Error: {e}")
        else:
            st.warning("Please enter a valid URL.")
elif option == "Convert Format":
    uploaded = st.file_uploader("Upload video", type=["mp4", "avi", "mkv", "webm"])
    target_format = st.selectbox("Convert to", ["mp4", "avi", "mkv"])

    if st.button("Convert"):
        if uploaded:
            with st.status("Converting...", expanded=True) as status:
                try:
                    filename = sanitize_filename(uploaded.name)
                    base_name = os.path.splitext(filename)[0]
                    tmp_path = os.path.join("downloads", filename)

                    with open(tmp_path, "wb") as f:
                        f.write(uploaded.read())

                    output_path = convert_format(tmp_path, target_format, base_name)
                    st.success(f"✅ Converted: {os.path.basename(output_path)}")
                    with open(output_path, "rb") as f:
                        st.download_button("Download", f, file_name=os.path.basename(output_path))

                    status.update(label="✅ Done", state="complete", expanded=False)
                except Exception as e:
                    status.update(label="❌ Error", state="error")
                    st.error(f"Error: {e}")
        else:
            st.warning("Please upload a file")

# Extract Audio section
elif option == "Extract Audio":
    url = st.text_input("YouTube URL (optional)")
    uploaded = st.file_uploader("Or upload video file", type=["mp4", "avi", "webm", "mkv"])

    if st.button("Extract Audio"):
        with st.status("Extracting...", expanded=True) as status:
            try:
                if url:
                    status.write("🔗 Downloading from YouTube...")
                    paths = download_video(url, "mp4")
                    filepath = paths[0]
                    base_name = os.path.splitext(os.path.basename(filepath))[0]
                elif uploaded:
                    filename = sanitize_filename(uploaded.name)
                    base_name = os.path.splitext(filename)[0]
                    filepath = os.path.join("downloads", filename)
                    with open(filepath, "wb") as f:
                        f.write(uploaded.read())
                else:
                    st.warning("Please provide a URL or upload a file.")
                    st.stop()

                status.write("🎧 Extracting audio...")
                audio_path = extract_audio(filepath, base_name)
                st.success(f"✅ Audio ready: {os.path.basename(audio_path)}")
                with open(audio_path, "rb") as f:
                    st.download_button("Download Audio", f, file_name=os.path.basename(audio_path))

                status.update(label="✅ Done", state="complete", expanded=False)
            except Exception as e:
                status.update(label="❌ Error", state="error")
                st.error(f"Error: {e}")

# Merge Videos section
elif option == "Merge Videos":
    files = st.file_uploader("Upload multiple MP4 files", type=["mp4"], accept_multiple_files=True)

    if st.button("Merge"):
        if files:
            with st.status("Merging...", expanded=True) as status:
                try:
                    paths = []
                    for f in files:
                        filename = sanitize_filename(f.name)
                        temp_path = os.path.join("downloads", filename)
                        with open(temp_path, "wb") as tmp:
                            tmp.write(f.read())
                        paths.append(temp_path)

                    output_path = merge_videos(paths)
                    st.success("✅ Videos merged")
                    with open(output_path, "rb") as f:
                        st.download_button("Download Merged Video", f, file_name="merged_output.mp4")

                    status.update(label="✅ Done", state="complete", expanded=False)
                except Exception as e:
                    status.update(label="❌ Merge failed", state="error")
                    st.error(f"Error: {e}")
        else:
            st.warning("Please upload at least 2 files")

# Footer
st.markdown("---")
st.caption("Built with ❤️ by Jana")