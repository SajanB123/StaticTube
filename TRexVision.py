import cv2
import numpy as np
import os
from tqdm import tqdm
import subprocess
from pytubefix import YouTube

def download_youtube_video():
    # Where to save the video
    SAVE_PATH = "./inputFiles/"

    # Ask for the YouTube link
    link = input("Enter YouTube URL: ")

    # Ask for the filename
    global filename
    filename = input("Enter the filename (without extension): ") + ".mp4"
    full_path = os.path.join(SAVE_PATH, filename)

    try:
        yt = YouTube(link)
        d_video = yt.streams.filter(progressive=True, file_extension="mp4").order_by("resolution").desc().first()
        
        if d_video:
            d_video.download(output_path=SAVE_PATH, filename=filename)
            print(f"Video downloaded successfully as {filename}!")
            return full_path  # Return the full path to be used in processing
        else:
            print("No valid video stream found!")
            return None
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

    if choice == "yes":
        output_filename = filename.replace(".mp4", ".avi")
        outputPath = os.path.join("./outputFiles/", output_filename)
        process_video(video_path, outputPath)
    else:
        print(f"Video saved as {filename}, but static noise version was not created.")