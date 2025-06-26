# 🎬 YouTube Downloader & Editor (Streamlit App)

This is a simple, powerful, and free Streamlit-based application to **download**, **convert**, **extract audio**, and **merge** YouTube videos. It supports **single videos**, **entire playlists**, and **batch downloads**, along with format conversion and audio extraction.

## 🔧 Features

✅ Download single video or full playlist  
✅ Convert between formats: `.mp4`, `.avi`, `.mkv`  
✅ Extract audio from video (MP3)  
✅ Merge multiple MP4 videos into one  
✅ Supports drag-and-drop uploads  
✅ Built with ❤️ using [yt-dlp](https://github.com/yt-dlp/yt-dlp), [ffmpeg](https://ffmpeg.org/), and [Streamlit](https://streamlit.io)

---

## 🚀 Deployment

### Run Locally

```bash
# 1. Clone the repo
git clone https://github.com/Janardhan-Git/Youtube-downloader-app.git
cd Youtube-downloader-app

# 2. Create virtual environment and activate
python -m venv venv
venv\Scripts\activate  # on Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the Streamlit app
streamlit run streamlit_app.py
