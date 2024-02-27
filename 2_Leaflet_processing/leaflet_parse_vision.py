import base64
import requests
from PIL import Image
import os
import io
from tqdm import tqdm  

# OpenAI API Key
api_key = "YOUR-API-KEY-HERE"

# Function to encode the image directly from a PIL image object
def encode_image_pil(image):
    img_byte_arr = io.BytesIO()  # Create a bytes buffer
    image.save(img_byte_arr, format='JPEG')  # Save the image to the bytes buffer in JPEG format
    img_byte_arr = img_byte_arr.getvalue()  # Get the byte value of the image
    return base64.b64encode(img_byte_arr).decode('utf-8')  # Encode to base64 and return

# Function to append images horizontally
def append_images_horizontally(images_paths):
    images = [Image.open(img_path) for img_path in images_paths]
    
    # Calculate the total width and the max height of the final image
    total_width = sum(img.width for img in images)
    max_height = max(img.height for img in images)
    
    # Create a new image with the calculated dimensions
    new_image = Image.new('RGB', (total_width, max_height))
    
    # Append each image horizontally
    x_offset = 0
    for img in images:
        y_offset = (max_height - img.height) // 2
        new_image.paste(img, (x_offset, y_offset))
        x_offset += img.width
    
    return new_image

# Function to list all images in a directory
def list_images_in_directory(directory_path):
    valid_extensions = ['.jpg', '.jpeg', '.png']
    return [os.path.join(directory_path, f) for f in os.listdir(directory_path)
            if os.path.isfile(os.path.join(directory_path, f)) and os.path.splitext(f)[1].lower() in valid_extensions]

# Adjust the process_directory function to handle the modifications for message_content and file saving:
# def process_directory(directory_path):
#     images_paths = list_images_in_directory(directory_path)
def process_directory(directory_path):
    # Check if the output file already exists to enable resuming
    subdirectory_name = os.path.basename(os.path.normpath(directory_path))
    output_file_path_json = os.path.join("leaflet_jsons", f"{subdirectory_name}.json")
    output_file_path_txt = os.path.join("leaflet_jsons", f"{subdirectory_name}.txt")
    
    # Skip processing if either a JSON or TXT file already exists
    if os.path.exists(output_file_path_json) or os.path.exists(output_file_path_txt):
        # print(f"Skipping {directory_path} as output file already exists.")
        return

    # Existing code for processing directories
    images_paths = list_images_in_directory(directory_path)
    if images_paths:
        appended_image = append_images_horizontally(images_paths)
        base64_image = encode_image_pil(appended_image)

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        payload = {
            "model": "gpt-4-vision-preview",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt_text
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 3000
        }

        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)

        if response.status_code == 200:
            try:
                message_content = response.json()['choices'][0]['message']['content']
                
                # Modify message_content based on specific conditions
                lines = message_content.splitlines()
                if lines[0] == "```" and lines[-1] == "```":
                    message_content = "\n".join(lines[1:-1])  # Remove the first and last lines
                
                # Determine file extension
                file_extension = "txt"
                if len(lines) > 3 and lines[1].startswith("{") and lines[-2].startswith("}"):
                    file_extension = "json"
                
                # Save the message content as a file
                subdirectory_name = os.path.basename(os.path.normpath(directory_path))
                output_file_path = os.path.join("leaflet_jsons", f"{subdirectory_name}.{file_extension}")
                with open(output_file_path, 'w', encoding='utf-8') as file:
                    file.write(message_content)
            except KeyError as e:
                print(f"KeyError encountered while processing directory {directory_path}: {e}")
        else:
            print(f"Failed to process directory {directory_path}. HTTP Status Code: {response.status_code}")

# Master directory containing subdirectories
master_directory_path = "./leaflet_data/leaflet_images"

# Load prompt text from a file
prompt_text_file = 'prompt_text.txt'
with open(prompt_text_file, 'r', encoding='utf-8') as file:
    prompt_text = file.read()

# Iterate over each subdirectory in the master directory
for subdir in tqdm(os.listdir(master_directory_path), desc="Processing Directories"):
    subdir_path = os.path.join(master_directory_path, subdir)
    if os.path.isdir(subdir_path):
        process_directory(subdir_path)

