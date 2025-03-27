#!/usr/bin/env python3
"""
Blog Post Generator for Pro Truck Logistics

This script:
1. Fetches current logistics/transportation news using GPT.
2. Uses GPT to generate blog posts.
3. Generates unique images for posts using DALL-E.
4. Downloads and saves images locally.
5. Creates HTML files from the content.
6. Uploads the files (HTML, JSON, Images) to hosting via SFTP.
"""

import os
import json
import time
import random
# import ftplib # Removed FTP library
import paramiko # Added SFTP library
import requests
import html2text
import re
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from openai import OpenAI
import io # Added for image handling

# --- Configuration ---
# Get sensitive info from environment variables or a secure config file
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY") # Replace fallback
# --- Use SFTP details ---
FTP_HOST = os.environ.get("FTP_HOST", "yourdomain.com") # Replace fallback (often just the domain)
FTP_USER = os.environ.get("FTP_USER", "YOUR_SFTP_USERNAME") # Replace fallback
FTP_PASS = os.environ.get("FTP_PASS", "YOUR_SFTP_PASSWORD") # Replace fallback
FTP_PORT = int(os.environ.get("FTP_PORT", "22")) # Default SFTP port is 22
FTP_BLOG_DIR = "/public_html/blog-posts/" # IMPORTANT: Adjust to the correct path from your SFTP root to the blog-posts dir (e.g., /home/user/public_html/blog-posts/ or /var/www/html/blog-posts/)

# --- Local Storage Paths ---
LOCAL_BLOG_DIR = Path("blog-posts") # Base directory for local files
LOCAL_BLOG_DIR.mkdir(exist_ok=True)
LOCAL_IMAGE_DIR = LOCAL_BLOG_DIR / "images" # Local image subfolder
LOCAL_IMAGE_DIR.mkdir(exist_ok=True)        # Create it if it doesn't exist

# --- Generation Settings ---
POSTS_TO_GENERATE = 1 # Number of posts per run

# --- Model Selection ---
GPT_MODEL = "gpt-3.5-turbo"
BROWSING_MODEL = "gpt-4-1106-preview" # Or a newer capable model
IMAGE_MODEL = "dall-e-3" # Or "dall-e-2"

# --- Blog Content Definitions ---
# [ Keep your BLOG_CATEGORIES and AUTHORS lists here - omitted for brevity ]
BLOG_CATEGORIES = [
    "Industry Trends", "Market Analysis", "Supply Chain Management", "Driver Tips",
    "Driver Recruitment", "Driver Retention", "Sustainability", "Technology Trends",
    "Safety", "Regulations", "Fleet Management", "Fuel Management", "LTL Shipping",
    "FTL Transport", "Logistics Insights"
    # Add more as needed
]

AUTHORS = [
    {
        "name": "John Smith", "position": "Logistics Specialist",
        "bio": "John has over 15 years of experience...",
        "image": "https://via.placeholder.com/100?text=JS" # Use placeholder or real URLs
    },
    {
        "name": "Sarah Johnson", "position": "Transportation Analyst",
        "bio": "Sarah is an expert in transportation economics...",
        "image": "https://via.placeholder.com/100?text=SJ"
    },
    # Add more authors
]


# --- Initialize OpenAI Client ---
try:
    client = OpenAI(api_key=OPENAI_API_KEY)
    # Test connection (optional)
    client.models.list()
    print("OpenAI client initialized successfully.")
except Exception as e:
    print(f"FATAL ERROR: Failed to initialize OpenAI client: {e}")
    exit(1) # Exit if OpenAI connection fails

# --- Function to Get Topics ---
def get_current_logistics_topics():
    """
    Fetches or generates relevant topics for semi-truck logistics blog posts.
    (Using the refined logic from previous steps)
    """
    # [ Keep your refined get_current_logistics_topics function here - omitted for brevity ]
    # This should return a list of topic dictionaries: [{'title': '...', 'summary': '...', 'relevance': '...', 'category': '...' (optional)}]
    # Make sure it has robust fallbacks.
    print("Simulating topic fetching: Using hardcoded semi-truck topics.")
    fallback_topics = [
        {
            "title": "Next-Gen Semi-Truck Cabs: How Driver Comfort is Revolutionizing Fleet Retention",
            "summary": "Modern semi-truck cab designs are incorporating unprecedented comfort features, transforming the driver experience.",
            "relevance": "Investing in driver comfort is a critical strategy for retaining experienced operators.",
            "category": "Driver Retention"
        },
        {
            "title": "Commercial Fleet Electrification: Real-World ROI Data from Early Semi-Truck Adopters",
            "summary": "New data reveals the actual cost savings and operational impacts from logistics companies using electric semi-trucks.",
            "relevance": "Fleet managers need concrete data from similar operations to make informed transition decisions.",
            "category": "Sustainability"
        }
    ]
    return fallback_topics


# --- Function to Get Image ---
def get_relevant_image(topic, post_id):
    """
    Generates a custom image using DALL-E based on the blog post topic.
    Downloads the image, saves it locally, and returns the FINAL server path.
    Returns a fallback URL if generation/download/save fails.
    """
    print(f"Attempting to generate DALL-E image for topic: {topic.get('title', 'Untitled')}")

    # More specific fallback image related to trucking
    fallback_image = "https://images.unsplash.com/photo-1588411393236-d2827123e3e6?ixlib=rb-1.2.1&auto=format&fit=crop&w=1024&q=80" # Image of trucks

    try:
        # 1. Create a custom prompt for DALL-E using GPT
        topic_title = topic.get('title', '')
        topic_summary = topic.get('summary', '')
        prompt_creation_prompt = f"""
        Create a detailed, visually interesting DALL-E prompt (around 100 words) for a photorealistic image illustrating a blog post titled "{topic_title}".
        The post is about: {topic_summary}.
        Focus on commercial trucking, semi-trucks, or logistics operations. Avoid generic stock photos. Include specific elements, mood (e.g., optimistic, industrious), and lighting (e.g., dawn, highway lights).
        Output only the prompt itself.
        """
        prompt_response = client.chat.completions.create(
            model=GPT_MODEL, # Cheaper model for prompt generation
            messages=[{"role": "user", "content": prompt_creation_prompt}]
        )
        custom_image_prompt = prompt_response.choices[0].message.content.strip()
        print(f"Generated DALL-E prompt: {custom_image_prompt[:100]}...")

        # 2. Generate image using DALL-E
        print(f"Requesting image from DALL-E model: {IMAGE_MODEL}")
        image_response = client.images.generate(
            model=IMAGE_MODEL,
            prompt=custom_image_prompt,
            size="1024x1024", # DALL-E 3 supports 1024x1024, 1792x1024, 1024x1792
            quality="standard", # Or "hd"
            n=1,
            response_format="url" # Get temporary URL first
        )
        temp_image_url = image_response.data[0].url
        print(f"DALL-E temporary URL received.")

        # 3. Download the image
        print(f"Downloading image from temporary URL...")
        image_download_response = requests.get(temp_image_url, stream=True, timeout=60) # Increased timeout
        image_download_response.raise_for_status() # Check for download errors
        image_data = image_download_response.content
        print(f"Downloaded {len(image_data)} bytes.")

        # 4. Define paths and save locally
        content_type = image_download_response.headers.get('content-type')
        extension = 'png' # Default
        if content_type:
            if 'png' in content_type: extension = 'png'
            elif 'jpeg' in content_type or 'jpg' in content_type: extension = 'jpg'
            elif 'webp' in content_type: extension = 'webp'

        image_filename = f"{post_id}.{extension}"
        local_image_path = LOCAL_IMAGE_DIR / image_filename
        # Define the FINAL web-accessible path where the image will live on the server
        # IMPORTANT: This path must be relative to the web root or an absolute path from the domain root
        # It should match how images are accessed in your HTML (e.g., /blog-posts/images/...)
        server_image_path = f"{FTP_BLOG_DIR.replace('/public_html', '').rstrip('/')}/images/{image_filename}" # Adjust based on your web server config

        print(f"Saving image locally to: {local_image_path}")
        with open(local_image_path, "wb") as f:
            f.write(image_data)
        print("Saved image locally.")

        # 5. Return the FINAL server path
        print(f"Image will be accessible at: {server_image_path}")
        return server_image_path

    except Exception as e:
        print(f"ERROR generating/downloading/saving DALL-E image: {e}")
        print(f"Using fallback image: {fallback_image}")
        return fallback_image # Return fallback URL on any error

# --- Function to Generate Post ---
def generate_blog_post(topic):
    """
    Generates a blog post dictionary including content and metadata.
    """
    print(f"\nGenerating blog post content for: {topic['title']}")

    # Create unique post ID based on timestamp BEFORE generating image
    post_id = int(time.time())

    # --- Get image FIRST using post_id for filename ---
    image_url = get_relevant_image(topic, post_id) # Gets FINAL server path or fallback

    # Select Author
    author = random.choice(AUTHORS)

    # Determine Category
    category = topic.get("category", random.choice(BLOG_CATEGORIES)) # Use provided or random

    # Details
    read_time = random.randint(7, 10)
    post_date = datetime.now().strftime("%B %d, %Y")

    # --- Generate Meta Description ---
    print("Generating meta description...")
    meta_description_prompt = f"""
    Write an SEO-optimized meta description (under 160 chars) for a blog post titled "{topic['title']}" for a semi-truck logistics company. Focus on keywords like trucking, freight, fleet management.
    """
    try:
        meta_response = client.chat.completions.create(
            model=GPT_MODEL, messages=[{"role": "user", "content": meta_description_prompt}]
        )
        meta_description = meta_response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Warning: Failed to generate meta description: {e}")
        meta_description = topic.get('summary', topic['title'])[:155] # Fallback

    # --- Generate Keywords ---
    print("Generating SEO keywords...")
    keywords_prompt = f"""
    Generate 5-7 SEO keywords/phrases for a blog post titled "{topic['title']}" focusing on semi-truck logistics, freight, and fleet operations. Comma-separated list only.
    """
    try:
        keywords_response = client.chat.completions.create(
            model=GPT_MODEL, messages=[{"role": "user", "content": keywords_prompt}]
        )
        keywords = keywords_response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Warning: Failed to generate keywords: {e}")
        keywords = "logistics, trucking, freight, fleet management" # Fallback

    # --- Generate Main Blog Content ---
    print("Generating main blog content (HTML)...")
    content_prompt = f"""
    Write a detailed, 1500-word blog post for a semi-truck logistics company titled "{topic['title']}".
    Context: {topic.get('summary', '')} Relevant because: {topic.get('relevance', '')}.
    Target Audience: Semi-truck fleet operators, logistics managers.
    Structure: Engaging intro, 2-3 main H2 sections with practical insights/data/advice for trucking, use H3 subsections and lists, include a fictional expert quote, conclude with key takeaways.
    Requirements: Trucking-specific terms, optimize for keywords "{keywords}", valuable for 2025, actionable info, HTML format (<p>, <h2>, <h3>, <ul>, <li>, <blockquote>).
    Category: {category}
    """
    try:
        content_response = client.chat.completions.create(
            model=GPT_MODEL, messages=[{"role": "user", "content": content_prompt}],
            max_tokens=3000 # Request longer response
        )
        content = content_response.choices[0].message.content.strip()
    except Exception as e:
        print(f"ERROR: Failed to generate main content: {e}")
        # Create minimal fallback content to allow script to continue
        content = f"<h2>{topic['title']}</h2><p>Content generation failed. Please edit this post.</p><p>Topic Summary: {topic.get('summary', 'N/A')}</p>"


    # --- Create Excerpt ---
    try:
        h = html2text.HTML2Text()
        h.ignore_links = True
        text_content = h.handle(content)
        # Find the first meaningful paragraph
        paragraphs = [p.strip() for p in text_content.split('\n\n') if p.strip() and not p.strip().startswith('#')]
        first_paragraph = paragraphs[0] if paragraphs else text_content[:250]
        excerpt = first_paragraph[:200]
        if len(first_paragraph) > 200:
            excerpt += "..."
    except Exception as e:
        print(f"Warning: Failed to generate excerpt: {e}")
        excerpt = topic.get('summary', topic['title'])[:200] # Fallback


    # --- Assemble Post Data ---
    post = {
        "id": post_id,
        "title": topic['title'],
        "excerpt": excerpt,
        "date": post_date,
        "category": category,
        "author": author["name"],
        "author_position": author["position"],
        "author_bio": author["bio"],
        "author_image": author["image"],
        "read_time": f"{read_time} min read",
        "content": content, # The generated HTML content
        "image": image_url, # FINAL server path or fallback
        "meta": {
            "description": meta_description,
            "keywords": keywords
        },
        "tags": keywords.split(',')[:5] # Use first 5 keywords as initial tags
    }
    print(f"Post data assembled for ID {post_id}")
    return post

# --- Function to Save JSON ---
def save_blog_post(post):
    """Saves the blog post dictionary as a JSON file locally."""
    post_id = post["id"]
    filename = f"{post_id}.json"
    filepath = LOCAL_BLOG_DIR / filename
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(post, f, ensure_ascii=False, indent=2)
        print(f"Saved blog post JSON to {filepath}")
        return filepath
    except IOError as e:
        print(f"ERROR saving JSON file {filepath}: {e}")
        return None # Indicate failure

# --- Function to Create HTML ---
def create_blog_post_html(post):
    """Creates an HTML file for the blog post using the template."""
    post_id = post["id"]
    html_filename = f"post-{post_id}.html"
    html_filepath = LOCAL_BLOG_DIR / html_filename
    template_path = Path("blog-post-template.html") # Assumes template is in same dir as script

    try:
        if not template_path.exists():
            raise FileNotFoundError(f"Template file not found at {template_path}")

        with open(template_path, "r", encoding="utf-8") as f:
            template = f.read()

        # Simple (but less robust) string replacement
        replacements = {
            '<title id="post-title">Blog Post | Pro Truck Logistics</title>': f'<title>{htmlspecialchars(post["title"])} | Pro Truck Logistics</title>',
            '<meta id="meta-description" name="description" content="Logistics and transportation industry insights from Pro Truck Logistics">': f'<meta name="description" content="{htmlspecialchars(post["meta"]["description"])}">',
            '<meta id="meta-keywords" name="keywords" content="logistics, trucking, transportation">': f'<meta name="keywords" content="{htmlspecialchars(post["meta"]["keywords"])}">',
            '<meta id="og-title" property="og:title" content="Blog Post | Pro Truck Logistics">': f'<meta property="og:title" content="{htmlspecialchars(post["title"])} | Pro Truck Logistics">',
            '<meta id="og-description" property="og:description" content="Logistics and transportation industry insights from Pro Truck Logistics">': f'<meta property="og:description" content="{htmlspecialchars(post["meta"]["description"])}">',
            '<meta id="og-image" property="og:image" content="">': f'<meta property="og:image" content="{htmlspecialchars(post["image"])}">',
            "background-image: linear-gradient(rgba(0, 0, 0, 0.5), rgba(0, 0, 0, 0.5)), url('');": f"background-image: linear-gradient(rgba(0, 0, 0, 0.5), rgba(0, 0, 0, 0.5)), url('{htmlspecialchars(post['image'])}');",
            '<span id="post-category" class="post-category">Category</span>': f'<span id="post-category" class="post-category">{htmlspecialchars(post["category"])}</span>',
            '<h1 id="post-title-header" class="post-title">Blog Post Title</h1>': f'<h1 id="post-title-header" class="post-title">{htmlspecialchars(post["title"])}</h1>',
            '<span id="post-date">Date</span>': f'<span id="post-date">{post["date"]}</span>',
            '<span id="post-author">Author</span>': f'<span id="post-author">{htmlspecialchars(post["author"])}</span>',
            '<span id="post-read-time">Read time</span>': f'<span id="post-read-time">{post["read_time"]}</span>',
            '<div id="post-content">\n          <!-- Content will be dynamically inserted here -->\n        </div>': f'<div id="post-content">\n          {post["content"]}\n        </div>', # Insert raw HTML content
            '<img id="author-image" src="" alt="Author">': f'<img id="author-image" src="{htmlspecialchars(post["author_image"])}" alt="{htmlspecialchars(post["author"])}">',
            '<h4 id="author-name" class="author-name">Author Name</h4>': f'<h4 id="author-name" class="author-name">{htmlspecialchars(post["author"])}</h4>',
            '<p id="author-position" class="author-position">Position</p>': f'<p id="author-position" class="author-position">{htmlspecialchars(post["author_position"])}</p>',
            '<p id="author-bio">Author bio will be displayed here.</p>': f'<p id="author-bio">{htmlspecialchars(post["author_bio"])}</p>',
        }

        # --- Replace share URLs ---
        share_url = f"https://protrucklogistics.org/blog-posts/post-{post_id}.html" # Replace with your actual domain/path
        replacements['<a href="#" class="share-button facebook">'] = f'<a href="https://www.facebook.com/sharer/sharer.php?u={share_url}" target="_blank" class="share-button facebook">'
        replacements['<a href="#" class="share-button twitter">'] = f'<a href="https://twitter.com/intent/tweet?url={share_url}&text={htmlspecialchars(post["title"])}" target="_blank" class="share-button twitter">'
        replacements['<a href="#" class="share-button linkedin">'] = f'<a href="https://www.linkedin.com/shareArticle?mini=true&url={share_url}&title={htmlspecialchars(post["title"])}" target="_blank" class="share-button linkedin">'
        replacements['<a href="#" class="share-button email">'] = f'<a href="mailto:?subject={htmlspecialchars(post["title"])}&body=Check out this article: {share_url}" class="share-button email">'

        # Perform replacements
        processed_template = template
        for placeholder, value in replacements.items():
             processed_template = processed_template.replace(placeholder, value)

        # Save the processed HTML file
        with open(html_filepath, "w", encoding="utf-8") as f:
            f.write(processed_template)

        print(f"Created HTML file: {html_filepath}")
        return html_filepath

    except Exception as e:
        print(f"ERROR creating HTML file {html_filepath}: {e}")
        return None # Indicate failure

# Helper for HTML escaping
def htmlspecialchars(text):
    import html
    return html.escape(str(text), quote=True)

# --- Function to Update Index ---
def update_blog_index(posts_to_add):
    """
    Updates the blog index JSON file (index.json).
    Reads existing posts, adds new ones, sorts, and saves.
    """
    index_path = LOCAL_BLOG_DIR / "index.json"
    all_posts = []

    # Read existing index if it exists
    if index_path.exists():
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                all_posts = json.load(f)
            if not isinstance(all_posts, list):
                print("Warning: Existing index.json is not a list. Starting fresh.")
                all_posts = []
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not read or parse existing index.json: {e}. Starting fresh.")
            all_posts = []

    # Create a set of existing IDs for quick lookup
    existing_ids = {p.get('id') for p in all_posts if p.get('id')}

    # Add new posts to the list, avoiding duplicates
    added_count = 0
    for post in posts_to_add:
        if post.get('id') and post['id'] not in existing_ids:
            # Create a simplified version for the index
            index_post = {
                "id": post["id"],
                "title": post["title"],
                "excerpt": post["excerpt"],
                "date": post["date"],
                "category": post["category"],
                "author": post["author"],
                "read_time": post["read_time"],
                "image": post["image"],
                "tags": post.get("tags", []), # Include tags
                "hidden": post.get("hidden", False) # Default to not hidden
            }
            all_posts.append(index_post)
            existing_ids.add(post['id'])
            added_count += 1
        elif post.get('id'):
             print(f"Skipping post ID {post['id']} as it already exists in index.")

    # Sort posts by ID (timestamp) in descending order (newest first)
    all_posts.sort(key=lambda x: x.get("id", 0), reverse=True)

    # Save updated index
    try:
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(all_posts, f, ensure_ascii=False, indent=2)
        print(f"Updated blog index '{index_path}' with {added_count} new post(s). Total posts: {len(all_posts)}")
        return index_path
    except IOError as e:
         print(f"ERROR saving updated index.json: {e}")
         return None


# --- Function to Upload Files (SFTP) ---
def upload_files_via_sftp(file_paths):
    """
    Uploads files to the SFTP server using paramiko.
    Handles subdirectory creation for images.
    """
    transport = None
    sftp = None
    all_successful = True
    try:
        print(f"\nConnecting to SFTP server {FTP_HOST}:{FTP_PORT}...")
        transport = paramiko.Transport((FTP_HOST, FTP_PORT))
        # Increase timeout for slower connections if needed
        transport.set_keepalive(30)
        transport.connect(username=FTP_USER, password=FTP_PASS)
        sftp = paramiko.SFTPClient.from_transport(transport)
        print(f"SFTP Connected. Home directory: {sftp.getcwd()}") # Often starts in user's home

        # --- Navigate to or create the base blog directory ---
        # IMPORTANT: This assumes FTP_BLOG_DIR is relative to the SFTP root OR absolute path
        print(f"Attempting to change directory to: {FTP_BLOG_DIR}")
        try:
            sftp.chdir(FTP_BLOG_DIR)
            print(f"Successfully changed directory to {FTP_BLOG_DIR}")
        except IOError:
            print(f"Directory {FTP_BLOG_DIR} not found. Attempting to create...")
            # Create directories recursively (more robust)
            dirs = FTP_BLOG_DIR.strip('/').split('/')
            current_path = ""
            # Handle absolute paths starting from root
            if FTP_BLOG_DIR.startswith('/'):
                 current_path = "/"
            for directory in dirs:
                 if not directory: continue # Skip empty parts from multiple slashes
                 if current_path == "/":
                     current_path += directory
                 else:
                     current_path += "/" + directory
                 try:
                     sftp.chdir(current_path) # Test if exists
                 except IOError:
                     print(f"Creating remote directory: {current_path}")
                     sftp.mkdir(current_path) # Create if doesn't exist
                     # Optionally set permissions if needed: sftp.chmod(current_path, 0o775)
            # Final chdir after creation
            sftp.chdir(FTP_BLOG_DIR)
            print(f"Successfully created and changed directory to {FTP_BLOG_DIR}")

        # --- Ensure 'images' subdirectory exists within the blog directory ---
        remote_image_dir = "images" # Relative to FTP_BLOG_DIR
        try:
            sftp.stat(remote_image_dir) # Check if exists
            print(f"Remote image directory '{remote_image_dir}' exists.")
        except IOError:
            print(f"Creating remote image directory: {remote_image_dir}")
            sftp.mkdir(remote_image_dir)
            # Optionally set permissions: sftp.chmod(remote_image_dir, 0o775)
            print(f"Created '{remote_image_dir}'.")

        # --- Upload each file ---
        print("\nStarting file uploads...")
        for file_path in file_paths:
            if not file_path or not file_path.exists():
                print(f"Skipping upload for non-existent file: {file_path}")
                continue

            local_file_str = str(file_path.resolve()) # Get absolute path
            file_name = file_path.name

            # Determine the correct remote path (relative to current dir: FTP_BLOG_DIR)
            if file_path.parent.name == 'images':
                remote_path = f"{remote_image_dir}/{file_name}"
                print(f"Uploading image '{file_name}' to '{remote_path}'...")
            else:
                remote_path = file_name
                print(f"Uploading file '{file_name}' to root of blog dir...")

            try:
                sftp.put(local_file_str, remote_path)
                # Optionally set permissions: sftp.chmod(remote_path, 0o664)
                print(f"  -> Success: Uploaded {file_name}")
            except Exception as upload_err:
                 print(f"  -> ERROR uploading {file_name}: {upload_err}")
                 all_successful = False # Mark failure

        print("\nFile upload process finished.")
        return all_successful

    except paramiko.AuthenticationException:
        print("FATAL SFTP ERROR: Authentication failed. Check username/password.")
        return False
    except paramiko.SSHException as sshException:
        print(f"FATAL SFTP ERROR: Could not establish SFTP connection: {sshException}")
        return False
    except Exception as e:
        print(f"FATAL SFTP ERROR: An unexpected error occurred: {e}")
        return False
    finally:
        # Ensure connection is closed
        if sftp:
            sftp.close()
            print("SFTP connection closed.")
        if transport:
            transport.close()
            print("SFTP transport closed.")


# --- Function to Gather and Upload All Files ---
def upload_blog_files():
    """
    Upload all relevant local blog files (HTML, JSON, images) to the SFTP server.
    """
    print("\nGathering files for upload...")
    # Gather all relevant files
    files_to_upload = list(LOCAL_BLOG_DIR.glob("*.json")) + \
                      list(LOCAL_BLOG_DIR.glob("*.html")) + \
                      list(LOCAL_IMAGE_DIR.glob("*.*")) # Images (png, jpg, webp etc.)

    if not files_to_upload:
        print("No local files found to upload.")
        return False

    print(f"Found {len(files_to_upload)} files/images in local directories.")

    # Attempt upload using the SFTP function
    return upload_files_via_sftp(files_to_upload)


# --- Main Execution ---
def main():
    """
    Main function to run the blog generation and upload process.
    """
    start_time = time.time()
    print(f"--- Starting Blog Generation ({datetime.now()}) ---")

    # Fetch Topics
    print("\nStep 1: Fetching Topics...")
    try:
        topics = get_current_logistics_topics()
        if not topics:
             print("No topics found or generated. Exiting.")
             return
    except Exception as e:
        print(f"ERROR: Failed to get topics: {e}")
        return # Exit if topic fetching fails

    # Select topics for this run
    if len(topics) > POSTS_TO_GENERATE:
        selected_topics = random.sample(topics, POSTS_TO_GENERATE)
    else:
        selected_topics = topics
    print(f"Selected {len(selected_topics)} topic(s) for generation.")

    # Generate Posts
    print("\nStep 2: Generating Posts...")
    generated_posts_data = [] # Store data of successfully generated posts
    created_files = []      # Store paths of files created in this run

    for i, topic in enumerate(selected_topics):
        print(f"\n--- Processing Topic {i+1}/{len(selected_topics)}: \"{topic.get('title', 'Untitled')}\" ---")
        try:
            # Generate the blog post data dictionary
            post_data = generate_blog_post(topic)
            if not post_data:
                 raise ValueError("generate_blog_post returned None")

            # Save the post data as JSON
            json_filepath = save_blog_post(post_data)
            if json_filepath:
                created_files.append(json_filepath)
            else:
                 raise IOError("Failed to save JSON file")

            # Create HTML file for the post
            html_filepath = create_blog_post_html(post_data)
            if html_filepath:
                created_files.append(html_filepath)
            else:
                 raise IOError("Failed to create HTML file")

            # Add the local image path IF it was created and saved locally
            image_filename = Path(post_data['image']).name # Get filename from the server path
            local_image_path = LOCAL_IMAGE_DIR / image_filename
            if local_image_path.exists():
                 created_files.append(local_image_path)
            else:
                 print(f"Warning: Local image file {local_image_path} not found, likely used fallback.")


            generated_posts_data.append(post_data) # Add to list of successes
            print(f"--- Successfully generated post for topic {i+1} ---")

        except Exception as e:
            # Log detailed error and continue to the next topic
            print(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            print(f"ERROR processing topic '{topic.get('title', 'Unknown')}' (ID tentative: {post_id if 'post_id' in locals() else 'N/A'}): {e}")
            import traceback
            traceback.print_exc() # Print full traceback for debugging
            print(f"Skipping this topic.")
            print(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            continue # Skip to the next topic

    # Check if any posts were successfully generated
    if not generated_posts_data:
         print("\nNo posts were successfully generated in this run. Exiting.")
         return

    # Update Index
    print("\nStep 3: Updating Blog Index...")
    index_filepath = update_blog_index(generated_posts_data)
    if index_filepath and index_filepath not in created_files:
        # Ensure index is always in the list of files to potentially upload
        # (Needed if only updating index without generating new posts, though less common here)
        created_files.append(index_filepath)
    elif not index_filepath:
         print("WARNING: Failed to update index file. Upload will proceed without index update.")


    # Upload Files
    print("\nStep 4: Uploading Files via SFTP...")
    # Option 1: Upload only files created/updated in THIS run
    # upload_success = upload_files_via_sftp(created_files)

    # Option 2: Upload ALL relevant files found locally (simpler, ensures consistency)
    upload_success = upload_blog_files()

    # Final Summary
    print("\n--- Blog Generation Summary ---")
    end_time = time.time()
    print(f"Duration: {end_time - start_time:.2f} seconds")
    print(f"Successfully generated posts: {len(generated_posts_data)}")
    print(f"Files created/updated locally: {len(created_files)}")
    if upload_success:
        print("SFTP Upload Status: SUCCESSFUL")
    else:
        print("SFTP Upload Status: FAILED or Partially Failed (Check logs above)")
    print("--- Run Finished ---")

if __name__ == "__main__":
    main()
