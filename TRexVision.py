import cv2
import numpy as np
import os
from tqdm import tqdm
import subprocess
from pytubefix import YouTube
import yt_dlp

def search_youtube_yt_dlp(query):
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'force_generic_extractor': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        search_results = ydl.extract_info(f"ytsearch5:{query}", download=False)
    
    if "entries" not in search_results:
        print("No results found.")
        return []

    results = []
    for idx, entry in enumerate(search_results["entries"], start=1):
        results.append((idx, entry["title"], entry["url"]))

    return results

query = input("Search for a YouTube video: ")
videos = search_youtube_yt_dlp(query)

if videos:
    for idx, title, url in videos:
        print(f"{idx}. {title} ({url})")

    choice = int(input("Enter the number of the video to download: ")) - 1
    global selected_video_url
    selected_video_url = videos[choice][2]

    print(f"You selected: {videos[choice][1]}")
    print(f"Video URL: {selected_video_url}")

def download_youtube_video():
    SAVE_PATH = "./inputFiles/"

    global filename
    filename = input("Enter the filename (without extension): ") + ".mp4".replace(" ", "_")
    video_path = os.path.join(SAVE_PATH, "video.mp4")
    audio_path = os.path.join(SAVE_PATH, "audio.mp4")
    final_output_path = os.path.join(SAVE_PATH, filename)

    try:
        yt = YouTube(selected_video_url)
        
        # Get the highest-quality video stream (video only)
        video_stream = yt.streams.filter(progressive=True, file_extension="mp4").order_by("resolution").desc().first()
        if video_stream:
            print(f"Downloading video: {video_stream.resolution}")
            video_stream.download(output_path=SAVE_PATH, filename="video.mp4")
        else:
            print("No suitable video stream found!")
            return None

        # Get the highest-quality audio stream (audio only)
        audio_stream = yt.streams.filter(only_audio=True, file_extension="mp4").first()
        if audio_stream:
            print("Downloading audio...")
            audio_stream.download(output_path=SAVE_PATH, filename="audio.mp4")
        else:
            print("No suitable audio stream found!")
            return None

        # Merge video and audio using ffmpeg
        print("Merging video and audio...")
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-strict", "experimental",
            "-map", "0:v:0",
            "-map", "1:a:0",
            final_output_path
        ]
        subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Clean up temp files
        os.remove(video_path)
        os.remove(audio_path)

        print(f"Video downloaded successfully as {final_output_path}")
        return final_output_path

    except Exception as e:
        print(f"Error: {e}")
        return None

def process_video(input_path, output_path):
    temp_video = "temp_video.avi"
    
    # Open the input video
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        print("Error: Could not open video.")
        return
    
    # Get video properties
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(temp_video, fourcc, fps, (frame_width, frame_height), isColor=False)
    
    ret, prev_frame = cap.read()
    if not ret:
        print("Error: Could not read first frame.")
        cap.release()
        return
    
    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    
    # Create a static black and white noise background
    static_noise = np.random.randint(0, 256, (frame_height, frame_width), dtype=np.uint8)
    
    # Initialize progress bar
    with tqdm(total=total_frames, desc="Processing Video", unit="frame") as pbar:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            luma_matte = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)[1]
            luma_matte_inv = cv2.bitwise_not(luma_matte)
            
            # Generate a second black and white noise layer for dynamic effect
            dynamic_noise = np.random.randint(0, 256, (frame_height, frame_width), dtype=np.uint8)
            
            # Apply luma matte over the noise layers
            masked_static_noise = cv2.bitwise_and(static_noise, static_noise, mask=luma_matte_inv)
            masked_dynamic_noise = cv2.bitwise_and(dynamic_noise, dynamic_noise, mask=luma_matte)
            
            result = cv2.add(masked_static_noise, masked_dynamic_noise)
            
            out.write(result)
            prev_gray = gray.copy()
            pbar.update(1)  # Update progress bar
    
    cap.release()
    out.release()
    
    print("Merging audio...")
    # Use ffmpeg to extract and merge audio
    ffmpeg_cmd = [
        "ffmpeg", "-y", "-i", temp_video, "-i", input_path, "-c:v", "copy", "-c:a", "aac", "-strict", "experimental", "-map", "0:v:0", "-map", "1:a:0", output_path
    ]
    subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Delete temporary video file
    os.remove(temp_video)
    print(f"Processed video with audio saved as {output_path}")

# Get the downloaded video path
video_path = download_youtube_video()

if video_path:
    # Ask the user if they want to process it
    choice = input("Do you want to generate the static black and white noise version? (yes/no): ").strip().lower()

    if choice == "yes" or "y":
        output_filename = filename.replace(".mp4", ".avi")
        outputPath = os.path.join("./outputFiles/", output_filename)
        process_video(video_path, outputPath)
    else:
        print(f"Video saved as {filename}, but static noise version was not created.")