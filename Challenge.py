#!/usr/bin/env python3

import os
import time
import logging
from google import genai
from google.genai.types import HttpOptions
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel

# Try to import Google Cloud Logging; fallback if unavailable
try:
    import google.cloud.logging as gcp_logging
    CLOUD_LOGGING_AVAILABLE = True
except ImportError:
    gcp_logging = None
    CLOUD_LOGGING_AVAILABLE = False
    logging.warning(
        "google-cloud-logging package not found; logs will only go to stdout"
    )

# ——— Configuration ———
PROJECT_ID = "YOUR_PROJECT_ID"
LOCATION   = "us-central1"

# Initialize Cloud Logging if available
if CLOUD_LOGGING_AVAILABLE:
    gcp_logging_client = gcp_logging.Client()
    gcp_logging_client.setup_logging()

# Initialize the Gemini (GenAI) client for text generation
text_client = genai.Client(
    vertexai=True,
    project=PROJECT_ID,
    location=LOCATION,
    http_options=HttpOptions(api_version="v1"),
)

def generate_bouquet_image(prompt: str, output_file: str = "bouquet.jpeg") -> str:
    """
    Task 1: Generate an image via Imagen and save it locally.

    Args:
      prompt: Text prompt (e.g. "Create an image containing a bouquet of 2 sunflowers and 3 roses.")
      output_file: Local path for the generated image.
    Returns:
      The path to the saved image.
    """
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-002")

    images = model.generate_images(
        prompt=prompt,
        number_of_images=1,
        seed=1,
        add_watermark=False,
    )
    images[0].save(output_file)
    return output_file


def analyze_bouquet_image(image_path: str) -> str:
    """
    Task 2: Stream birthday wishes based on the bouquet image.

    Args:
      image_path: Path to the locally saved JPEG.
    Returns:
      The complete birthday wishes text.
    """
    with open(image_path, "rb") as f:
        img_bytes = f.read()

    contents = [
        "Generate heartfelt birthday wishes inspired by this bouquet image:",
        {"inline_data": {"mime_type": "image/jpeg", "data": img_bytes}},
    ]

    stream = text_client.models.generate_content_stream(
        model="gemini-2.0-flash-001",
        contents=contents,
    )

    full_response = ""
    for chunk in stream:
        print(chunk.text, end="")
        full_response += chunk.text
    print()
    return full_response


def read_image_content_and_log(image_path: str) -> str:
    """
    Reads the generated image, asks the model to describe it,
    logs the description to Cloud Logging (if available), and waits for the log entry.

    Returns:
      The textual description of the image.
    """
    with open(image_path, "rb") as f:
        img_bytes = f.read()

    contents = [
        "What is shown in this image?",
        {"inline_data": {"mime_type": "image/jpeg", "data": img_bytes}},
    ]

    response = text_client.models.generate_content(
        model="gemini-2.0-flash-001",
        contents=contents,
    )
    description = response.text.strip()

    # Log it
    logging.info(f"Image content: {description}")
    if CLOUD_LOGGING_AVAILABLE:
        # Poll Cloud Logging until the entry appears (up to 30s)
        filter_str = f'textPayload:"Image content: {description}"'
        for _ in range(30):
            entries = list(gcp_logging_client.list_entries(filter_=filter_str, page_size=1))
            if entries:
                print("Log entry created in Cloud Logging")
                break
            time.sleep(1)
        else:
            print("Timed out waiting for Cloud Log entry")
    else:
        print("Cloud Logging not available; check local logs instead.")

    return description


if __name__ == "__main__":
    # 1) Generate the bouquet image
    prompt = "Create an image containing a bouquet of 2 sunflowers and 3 roses."
    img_path = generate_bouquet_image(prompt)
    print(f"Image saved to {img_path}")

    # 2) Analyze the image to get birthday wishes
    print("\nStreaming birthday wishes:\n")
    wishes = analyze_bouquet_image(img_path)

    # 3) Save the wishes
    with open("wishes.txt", "w") as out:
        out.write(wishes)
    print("Wishes saved to wishes.txt")

    # 4) Read the image content and wait for log
    print("\nReading image content and waiting for log:\n")
    description = read_image_content_and_log(img_path)
    print(f"Detected image content: {description}")
