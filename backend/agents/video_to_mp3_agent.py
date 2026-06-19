import os
import subprocess
import imageio_ffmpeg
from backend.agents.base import BaseAgent
from backend.config import get_user_documents_dir
from backend.logger import get_logger

logger = get_logger("agents.video_to_mp3")

class VideoToMp3Agent(BaseAgent):
    name = 'video_to_mp3'
    description = 'Converts uploaded video files to mp3 format using the internal ffmpeg build.'

    def run(self, query: str) -> str:
        docs_dir = get_user_documents_dir()
        logger.info(f"Running VideoToMp3Agent with query: '{query}' in docs directory: '{docs_dir}'")

        # 1. Try to find the target video file in the documents directory
        video_extensions = {".mp4", ".mkv", ".avi", ".mov", ".webm"}
        all_files = [f for f in os.listdir(docs_dir) if os.path.isfile(os.path.join(docs_dir, f))]
        
        target_file = None
        
        # Check if the query refers to a specific file in the directory
        for f in all_files:
            ext = os.path.splitext(f)[1].lower()
            if ext in video_extensions:
                # If exact filename matches or is contained in the query
                if f.lower() in query.lower() or os.path.splitext(f)[0].lower() in query.lower():
                    target_file = f
                    break
        
        # Fallback: if no match, find the most recently modified video file in the directory
        if not target_file:
            video_files = [
                f for f in all_files 
                if os.path.splitext(f)[1].lower() in video_extensions
            ]
            if video_files:
                # Sort by modification time desc
                video_files.sort(
                    key=lambda x: os.path.getmtime(os.path.join(docs_dir, x)), 
                    reverse=True
                )
                target_file = video_files[0]
                logger.info(f"No specific video file match found in query. Defaulting to most recent video: {target_file}")
        
        if not target_file:
            return "Error: No video file was found in your workspace to convert. Please upload a video file first."

        input_path = os.path.join(docs_dir, target_file)
        base_name = os.path.splitext(target_file)[0]
        output_filename = f"{base_name}.mp3"
        output_path = os.path.join(docs_dir, output_filename)

        # 2. Convert using imageio-ffmpeg
        try:
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            cmd = [
                ffmpeg_exe,
                "-y",
                "-i", input_path,
                "-vn",
                output_path
            ]
            logger.info(f"Running conversion: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"ffmpeg conversion failed: {result.stderr}")
                return f"Error converting video to MP3: {result.stderr}"
            
            # Rebuild index on the analyse agent so the new MP3 text is indexed (if needed)
            try:
                from backend.core.registry import AgentRegistry
                registry = AgentRegistry()
                # If imported in server, we can get registry, but simpler is to try to trigger it via import
                # Or just let the user query it directly. Rebuilding index:
                from backend.agents.analyse_agent import AnalyseAgent
                analyse = AnalyseAgent()
                analyse.rebuild_index()
            except Exception as index_err:
                logger.warning(f"Could not automatically rebuild FAISS index: {index_err}")

            import urllib.parse
            encoded_filename = urllib.parse.quote(output_filename)
            download_url = f"/api/download/{encoded_filename}"
            return f"Successfully converted video '{target_file}' to audio format. Saved as '{output_filename}' in your documents folder. You can listen to it or download it here:\n\n[Audio: {output_filename}]({download_url})"
        except Exception as e:
            logger.exception("Conversion failed due to an exception:")
            return f"Error during conversion: {str(e)}"