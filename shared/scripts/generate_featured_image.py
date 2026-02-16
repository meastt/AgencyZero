#!/usr/bin/env python3
"""
Gemini Featured Image Generator
Generates 16:9 featured images for blog posts using Google's Gemini 2.5 Flash model.
Usage: python3 generate_featured_image.py "Post Title" "Site Niche"
"""

import os
import sys
import mimetypes
import argparse
from datetime import datetime
from dotenv import load_dotenv

# Load root .env
load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))

# Try to import google-genai, warn if missing
try:
    from google import genai
    from google.genai import types
except ImportError:
    print("❌ Critical Dependency Missing: google-genai")
    print("👉 Please run: pip install google-genai")
    sys.exit(1)

def save_binary_file(file_name, data):
    try:
        with open(file_name, "wb") as f:
            f.write(data)
        print(f"✅ Image saved to: {file_name}")
        return True
    except Exception as e:
        print(f"❌ Failed to save image: {e}")
        return False

def generate_image(title, niche):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or "PLACEHOLDER" in api_key:
        print("❌ GEMINI_API_KEY is missing or invalid in .env")
        return

    client = genai.Client(api_key=api_key)
    
    # Construct a high-quality prompt for SEO featured images
    prompt_text = (
        f"Create a photorealistic, high-quality featured image for a blog post about '{niche}'. "
        f"The specific topic is: '{title}'. "
        "The image should be professional, engaging, and suitable for a modern website header. "
        "Use cinematic lighting, sharp details, and a 16:9 composition. "
        "No text overlay on the image."
    )
    
    print(f"🎨 Generating image for: '{title}' ({niche})...")
    
    model = "gemini-2.5-flash-image"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=prompt_text),
            ],
        ),
    ]
    
    generate_content_config = types.GenerateContentConfig(
        image_config=types.ImageConfig(
            aspect_ratio="16:9",
            # image_size="1920x1080", # Verify if supported, usually strict enum or string
            person_generation="allow_adult", # Or stricter filtering if needed
        ),
        response_modalities=[
            "IMAGE",
        ],
    )

    # Ensure output directory exists
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets/generated_images")
    os.makedirs(output_dir, exist_ok=True)
    
    # Create filename-safe title
    safe_title = "".join([c if c.isalnum() else "_" for c in title])[:50]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_filename = os.path.join(output_dir, f"{safe_title}_{timestamp}")

    try:
        # Use simple generate_content instead of stream if possible for single image, 
        # but user code used stream, so we stick to it for compatibility
        file_index = 0
        generated = False
        
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            if not chunk.parts:
                continue
                
            for part in chunk.parts:
                if part.inline_data and part.inline_data.data:
                    inline_data = part.inline_data
                    data_buffer = inline_data.data
                    # mimetype might be 'image/jpeg' or 'image/png'
                    ext = mimetypes.guess_extension(inline_data.mime_type) or ".jpg"
                    
                    final_path = f"{base_filename}{ext}"
                    if save_binary_file(final_path, data_buffer):
                        print(f"🖼️  Preview: {final_path}")
                        generated = True
                elif part.text:
                    print(f"📝 Model Info: {part.text}")
        
        if not generated:
            print("⚠️  No image data received from API.")

    except Exception as e:
        print(f"❌ Generation Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate 16:9 Featured Image via Gemini")
    parser.add_argument("title", help="Blog Post Title")
    parser.add_argument("niche", help="Site Niche (e.g., 'Astrophotography', 'Predatory Cats')")
    
    if len(sys.argv) < 3:
        parser.print_help()
        sys.exit(1)
        
    args = parser.parse_args()
    generate_image(args.title, args.niche)
