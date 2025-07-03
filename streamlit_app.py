import streamlit as st
from yt_dlp import YoutubeDL
import os
import re
import ffmpeg
import unicodedata
import zipfile

def create_zip(file_paths: list[str], zip_name="downloads/all_videos.zip") -> str:
    with zipfile.ZipFile(zip_name, 'w') as zipf:
        for file_path in file_paths:
            arcname = os.path.basename(file_path)
            zipf.write(file_path, arcname=arcname)
    return zip_name


# ✅ Sanitize filename safely (no duplicates)
def sanitize_filename(name: str) -> str:
    # Normalize Unicode characters (e.g., remove accents)
    name = unicodedata.normalize("NFKD", name)
    # Replace illegal filename characters
    name = re.sub(r'[\\/*?:"<>|]', "_", name)
    # Limit filename length to avoid OS limits
    return name[:100]

# App config
st.set_page_config(
    page_title="Free, Ad Free YouTube Video Downloader & Editor",
    page_icon="🎬"
)
st.title("🎬 Free, Ad Free YouTube Video Downloader & Editor")

# Ensure download directory exists
os.makedirs("downloads", exist_ok=True)

# Helpers
def trim_with_ffmpeg(input_path: str, start: str, end: str) -> str:
    base, ext = os.path.splitext(input_path)
    output_path = f"{base}_trimmed{ext}"
    ffmpeg.input(input_path, ss=start, to=end).output(output_path).run()
    return output_path

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
    "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best",
    "http_headers": {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
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

            # ✅ Use yt-dlp's actual output path
            try:
                real_path = ydl.prepare_filename(entry)
                if target_format == "mp3":
                    real_path = os.path.splitext(real_path)[0] + ".mp3"  # postprocessed
                if not os.path.exists(real_path):
                    # fallback: scan folder for matching prefix
                    matches = [f for f in os.listdir("downloads") if f.startswith(title)]
                    if matches:
                        real_path = os.path.join("downloads", matches[0])
                    else:
                        raise FileNotFoundError(f"Downloaded file for {title} not found.")
                downloaded_files.append(real_path)
            except Exception as e:
                raise FileNotFoundError(f"Downloaded file for {title} not found.")

    return downloaded_files

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

option = st.radio("Select operation:", ["Download", "Extract Audio", "Merge Videos"])

# Download section
if option == "Download":
    url = st.text_input("Enter YouTube video or playlist URL")
    target_format = st.selectbox("Choose format", ["mp4", "mp3"])

    st.markdown("**Optional: Trim Video**")
    start_time = st.text_input("Start time (HH:MM:SS)", value="00:00:00")
    end_time = st.text_input("End time (HH:MM:SS)", value="")
    apply_trim = st.checkbox("Trim video after download")

    selected_titles = None
    if url:
        if "playlist" in url or "list=" in url:
            titles = fetch_video_titles(url)
            selected_titles = st.multiselect("Select videos to download from playlist:", titles, default=titles)


if st.button("Download"):
    if not url.strip():
        st.warning("Please enter a valid URL.")
    else:
        processed_paths = []  # ✅ Initialize before the try block

        with st.status("Starting download...", expanded=True) as status:
            try:
                status.write("🔗 Downloading...")
                paths = download_video(url, target_format, selected_titles)

                for path in paths:
                    final_path = path
                    base_name = os.path.splitext(os.path.basename(path))[0]

                    if apply_trim and end_time:
                        status.write(f"✂️ Trimming {base_name} from {start_time} to {end_time}...")
                        final_path = trim_video(path, start_time, end_time, base_name)
                        st.success(f"✅ Trimmed: {os.path.basename(final_path)}")
                    else:
                        st.success(f"✅ Downloaded: {os.path.basename(final_path)}")

                    with open(final_path, "rb") as f:
                        st.download_button("Download", f, file_name=os.path.basename(final_path), key=final_path)

                    processed_paths.append(final_path)

                status.update(label="✅ All Done", state="complete", expanded=False)

            except Exception as e:
                status.update(label="❌ Error", state="error")
                st.error(f"Error: {e}")

        if processed_paths:
            zip_path = create_zip(processed_paths)
            with open(zip_path, "rb") as f:
                st.download_button("📦 Download All as ZIP", f, file_name="all_videos.zip")

                                                 
# Extract Audio section

elif option == "Extract Audio":
    url = st.text_input("YouTube URL")
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