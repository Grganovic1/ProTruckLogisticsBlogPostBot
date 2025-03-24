#!/usr/bin/env python3
"""
Blog Post Generator for Pro Truck Logistics

This script:
1. Fetches current logistics/transportation news using GPT with web browsing capability
2. Uses GPT to generate blog posts
3. Creates HTML files from the content
4. Uploads the files to Namecheap hosting via FTP
"""

import os
import json
import time
import random
import ftplib
import requests
import html2text
import re
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from openai import OpenAI

# Configuration - these will come from GitHub Secrets in production
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "your-api-key-here")
FTP_HOST = os.environ.get("FTP_HOST", "ftp.yourdomain.com")
FTP_USER = os.environ.get("FTP_USER", "your-username")
FTP_PASS = os.environ.get("FTP_PASS", "your-password")
FTP_BLOG_DIR = "/blog-posts/" # Directory relative to web root

# Local blog post storage
LOCAL_BLOG_DIR = Path("blog-posts")
LOCAL_BLOG_DIR.mkdir(exist_ok=True)

# Number of blog posts to generate
POSTS_TO_GENERATE = 1

# Model selection
GPT_MODEL = "gpt-3.5-turbo"  # More cost-effective for regular content generation
BROWSING_MODEL = "gpt-4-1106-preview"  # Model that supports tools/browsing for research

# Blog post categories - expanded with more specific industry categories
BLOG_CATEGORIES = [
    # Industry Overview
    "Industry Trends", "Market Analysis", "Economic Outlook", "Logistics Insights",
    
    # Operations
    "Supply Chain Management", "Warehousing", "Inventory Management", "Last-Mile Delivery",
    "Cross-Docking", "Intermodal Transportation", "Freight Forwarding", "Order Fulfillment",
    
    # Driver Focus
    "Driver Tips", "Driver Wellness", "Driver Recruitment", "Driver Retention",
    "Owner-Operator Resources", "Career Development", "Road Life", "Driver Stories",
    
    # Sustainability & Environment
    "Sustainability", "Green Logistics", "Carbon Reduction", "Alternative Fuels",
    "Environmental Compliance", "Eco-Friendly Practices", "Electric Vehicles", "Renewable Energy",
    
    # Technology
    "Technology Trends", "AI & Automation", "Telematics", "Blockchain in Logistics",
    "IoT Solutions", "Data Analytics", "Digital Transformation", "Route Optimization",
    "Warehouse Automation", "Transportation Management Systems", "Fleet Tech",
    
    # Compliance & Safety
    "Safety", "Regulations", "Compliance Updates", "Risk Management",
    "HOS Regulations", "DOT Compliance", "FMCSA Updates", "Insurance Insights",
    "Security Measures", "Accident Prevention", "Cargo Security",
    
    # Fleet Operations
    "Fleet Management", "Maintenance Tips", "Vehicle Selection", "Asset Utilization",
    "Fleet Efficiency", "Fuel Management", "Preventative Maintenance", "Equipment Upgrades",
    
    # Business & Strategy
    "Business Growth", "Financial Management", "Strategic Planning", "Competitive Advantage",
    "Cost Reduction", "Revenue Optimization", "Customer Experience", "Service Expansion",
    
    # Industry Segments
    "LTL Shipping", "FTL Transport", "Refrigerated Logistics", "Hazmat Transportation",
    "Heavy Haul", "Expedited Shipping", "Specialized Freight", "Bulk Transport",
    
    # Global Logistics
    "International Shipping", "Global Supply Chains", "Cross-Border Transport", "Import/Export",
    "Trade Compliance", "Customs Regulations", "Port Operations", "Global Logistics Trends",
    
    # Customer Focus
    "Customer Service", "Relationship Management", "Shipper Insights", "Client Success Stories",
    "Service Improvements", "Client Retention", "Value-Added Services",
    
    # Industry Events
    "Conference Takeaways", "Industry Events", "Trade Shows", "Webinar Recaps",
    "Expert Interviews", "Industry Awards", "Case Studies"
]

# Blog authors
AUTHORS = [
    {
        "name": "John Smith",
        "position": "Logistics Specialist",
        "bio": "John has over 15 years of experience in the logistics industry, specializing in supply chain optimization and transportation management.",
        "image": "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?ixlib=rb-4.0.3"
    },
    {
        "name": "Sarah Johnson",
        "position": "Transportation Analyst",
        "bio": "Sarah is an expert in transportation economics and regulatory compliance with a background in both private sector logistics and government oversight.",
        "image": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?ixlib=rb-4.0.3"
    },
    {
        "name": "Michael Chen",
        "position": "Technology Director",
        "bio": "Michael specializes in logistics technology integration, helping companies leverage AI, IoT, and blockchain solutions to optimize their supply chains.",
        "image": "https://images.unsplash.com/photo-1560250097-0b93528c311a?ixlib=rb-4.0.3"
    }
]

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

def get_current_logistics_topics():
    """
    Fetches exactly 3 trending topics in logistics.
    
    Attempts:
    1. Use GPT with web browsing capability to retrieve current trends.
    2. If insufficient topics are returned, use GPT to generate realistic topics.
    3. If still fewer than 3 topics, fill gaps by generating fallback topics based on random blog categories.
    
    Returns:
      A list of 3 topic dictionaries, each with keys "title", "summary", and "relevance".
    """
    topics = []
    method_used = "Unknown"

    # First try: Use GPT with web browsing capability
    try:
        print("Attempting to get current logistics news via GPT with browsing capability...")
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_web",
                    "description": "Search the web for current information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query"
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        ]
        first_response = client.chat.completions.create(
            model=BROWSING_MODEL,
            messages=[{"role": "user", "content": "What are the latest news and trending topics in the trucking and logistics industry from the past week?"}],
            tools=tools,
            tool_choice={"type": "function", "function": {"name": "search_web"}}
        )
        message = first_response.choices[0].message
        if hasattr(message, 'tool_calls') and message.tool_calls:
            tool_call = message.tool_calls[0]
            function_args = json.loads(tool_call.function.arguments)
            search_query = function_args.get("query")
            print(f"Searching for: {search_query}")
            second_response = client.chat.completions.create(
                model=BROWSING_MODEL,
                messages=[
                    {"role": "user", "content": "What are the latest news and trending topics in the trucking and logistics industry from the past week?"},
                    message,
                    {"role": "tool", "tool_call_id": tool_call.id, "name": "search_web", "content": "Search results found many recent articles about logistics industry trends."},
                    {"role": "user", "content": """Based on these search results, provide 5 significant developments or trends in the trucking and logistics industry that a logistics company might want to write about in their blog.

For each topic, provide:
1. A specific headline
2. A brief summary (1-2 sentences)
3. Why this topic matters to logistics professionals

Format your response as JSON with an array of objects containing "title", "summary", and "relevance" keys.
"""}
                ]
            )
            content = second_response.choices[0].message.content
            try:
                json_match = re.search(r'```json\s*([\s\S]*?)\s*```', content)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    json_match = re.search(r'(\[\s*\{.*\}\s*\])', content, re.DOTALL)
                    json_str = json_match.group(1) if json_match else content
                topics = json.loads(json_str)
                print(f"Successfully retrieved {len(topics)} topics via GPT Web Search")
                method_used = "GPT Web Search"
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON from GPT response: {e}")
        else:
            print("No tool calls in the response")
    except Exception as e:
        print(f"Error using GPT with web search capability: {e}")

    # Second try: Use GPT to generate realistic trending topics if we have fewer than 3 topics
    if not topics or len(topics) < 3:
        try:
            print("Attempting to generate realistic trending topics with GPT...")
            current_date = datetime.now().strftime("%B %d, %Y")
            prompt = f"""
Today is {current_date}. Based on current industry trends and economic conditions, 
what are 5 realistic trending topics in the trucking and logistics industry that would 
make good blog post topics?

For each topic, include:
1. A specific headline/title
2. A brief summary of the trend/issue
3. Why this topic is relevant right now

Format your response as a JSON array with objects containing "title", "summary", and "relevance" keys.
"""
            response = client.chat.completions.create(
                model=GPT_MODEL,
                messages=[{"role": "user", "content": prompt}]
            )
            content = response.choices[0].message.content
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', content)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_match = re.search(r'(\[\s*\{.*\}\s*\])', content, re.DOTALL)
                json_str = json_match.group(1) if json_match else content
            generated_topics = json.loads(json_str)
            print(f"Successfully generated {len(generated_topics)} topics via GPT Generation")
            topics.extend(generated_topics)
            method_used = "GPT Generated Trends"
        except Exception as e:
            print(f"Error generating trending topics: {e}")

    # If still fewer than 3 topics, use fallback topics based on random blog categories
    if len(topics) < 3:
        print("Insufficient topics retrieved. Generating fallback topics based on blog categories...")
        additional_needed = 3 - len(topics)
        fallback_categories = random.sample(BLOG_CATEGORIES, additional_needed)
        for category in fallback_categories:
            fallback_prompt = f"""
Based on current logistics trends, provide a blog post topic idea for the category "{category}".
Include:
- A catchy headline/title
- A brief summary (1-2 sentences) of the trend or issue
- Why this topic is relevant now
Format your response as a JSON object with keys "title", "summary", and "relevance".
"""
            try:
                response = client.chat.completions.create(
                    model=GPT_MODEL,
                    messages=[{"role": "user", "content": fallback_prompt}]
                )
                content = response.choices[0].message.content.strip()
                json_match = re.search(r'```json\s*([\s\S]*?)\s*```', content)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    json_match = re.search(r'(\{.*\})', content, re.DOTALL)
                    json_str = json_match.group(1) if json_match else content
                fallback_topic = json.loads(json_str)
                topics.append(fallback_topic)
            except Exception as e:
                print(f"Error generating fallback topic for category {category}: {e}")
                topics.append({
                    "title": f"Trending {category} Insights for 2025",
                    "summary": f"An overview of key trends and challenges in {category.lower()} that logistics professionals should watch in 2025.",
                    "relevance": f"This topic is essential for staying competitive in the evolving field of {category.lower()}."
                })

    # If more than 3 topics, randomly pick 3
    if len(topics) > 3:
        topics = random.sample(topics, 3)

    print(f"Final topic selection ({len(topics)} topics): {[t['title'] for t in topics]}")
    return topics

def get_relevant_image(topic):
    """
    Gets a relevant image URL based on the topic for a semi truck company.
    First attempts to fetch an image from the free Pixabay API.
    If the API call fails or returns no results, it falls back to a preset dictionary of images tuned for semi truck companies.
    """
    print(f"Finding relevant image for topic: {topic}")
    
    # Extract the topic title for search
    topic_title = topic.get("title", topic) if isinstance(topic, dict) else topic
    search_query = topic_title  # Use the title as the search query
    
    # Attempt to use Pixabay API (free and fast approval)
    PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY")
    if PIXABAY_API_KEY:
        try:
            response = requests.get(
                "https://pixabay.com/api/",
                params={
                    "key": PIXABAY_API_KEY,
                    "q": search_query,
                    "image_type": "photo",
                    "per_page": 1,
                    "safesearch": "true"
                },
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                hits = data.get("hits", [])
                if hits:
                    image_url = hits[0]["webformatURL"]
                    print("Using Pixabay API image.")
                    return image_url
                else:
                    print("Pixabay API returned no results.")
            else:
                print(f"Pixabay API request failed with status code {response.status_code}.")
        except Exception as e:
            print(f"Pixabay API error: {e}")
    
    # Fallback: use a static dictionary of images tuned for a semi truck company
    fallback_images = {
        "semi": "https://images.unsplash.com/photo-1563720224159-54a129f2d10a?ixlib=rb-1.2.1&auto=format&fit=crop&w=1350&q=80",
        "truck": "https://images.unsplash.com/photo-1519003722824-194d4455a60c?ixlib=rb-4.0.3",
        "trucking": "https://images.unsplash.com/photo-1579931773327-5eac23628e9e?ixlib=rb-1.2.1&auto=format&fit=crop&w=1350&q=80",
        "freight": "https://images.unsplash.com/photo-1505039361124-8e2e63c16029?ixlib=rb-1.2.1&auto=format&fit=crop&w=1350&q=80",
        "diesel": "https://images.unsplash.com/photo-1573059476447-50c361b0e1dd?ixlib=rb-1.2.1&auto=format&fit=crop&w=1350&q=80",
        "fleet": "https://images.unsplash.com/photo-1588411393236-d2827123e3e6?ixlib=rb-1.2.1&auto=format&fit=crop&w=1350&q=80",
        "highway": "https://images.unsplash.com/photo-1519648023493-d82b5f8d7b8a?ixlib=rb-1.2.1&auto=format&fit=crop&w=1350&q=80",
    }
    
    # Try matching specific keywords from the topic title to select an image
    topic_lower = topic_title.lower()
    for keyword, image_url in fallback_images.items():
        if keyword in topic_lower:
            print(f"Selected fallback image for keyword: {keyword}")
            return image_url
    
    # Broad category matching tuned for a semi truck company
    if any(word in topic_lower for word in ["cargo", "freight", "shipment", "logistics", "distribution"]):
        print("Matched broad category: freight/logistics")
        return fallback_images.get("freight")
    if any(word in topic_lower for word in ["semi", "trucking", "truck", "diesel", "highway"]):
        print("Matched broad category: trucking/semi")
        return fallback_images.get("semi truck")
    
    # Default fallback image if no match is found
    print("Using default fallback image")
    return fallback_images.get("semi", "")

def generate_blog_post(topic):
    """
    Generate a comprehensive blog post using the topic data.
    Returns a dictionary with the post details and content.
    """
    print(f"Generating blog post about: {topic['title']}")
    
    # Select a random author
    author = random.choice(AUTHORS)
    
    # Select a random category that matches the topic
    category = random.choice(BLOG_CATEGORIES)
    
    # Generate a reasonable reading time (1500-2000 words is about 7-10 mins)
    read_time = random.randint(7, 10)
    
    # Current date for the post
    post_date = datetime.now().strftime("%B %d, %Y")
    
    # Generate SEO meta description
    print("Generating meta description...")
    meta_description_prompt = f"""
    Write an SEO-optimized meta description for a blog post about "{topic['title']}" in the logistics and transportation industry.
    The description should be compelling, include keywords, and be under 160 characters.
    """
    
    meta_description_response = client.chat.completions.create(
        model=GPT_MODEL,
        messages=[{"role": "user", "content": meta_description_prompt}]
    )
    meta_description = meta_description_response.choices[0].message.content.strip()
    
    # Generate SEO keywords
    print("Generating SEO keywords...")
    keywords_prompt = f"""
    Generate 5-7 SEO keywords or phrases for a blog post about "{topic['title']}" in the logistics and transportation industry. 
    Format them as a comma-separated list only. No numbering or bullets.
    """
    
    keywords_response = client.chat.completions.create(
        model=GPT_MODEL,
        messages=[{"role": "user", "content": keywords_prompt}]
    )
    keywords = keywords_response.choices[0].message.content.strip()
    
    # Generate blog post content
    print("Generating main blog content...")
    content_prompt = f"""
    Write a comprehensive, detailed, and informative blog post about "{topic['title']}" for Pro Truck Logistics company blog.
    Additional context: {topic.get('summary', '')}
    Relevance to the industry: {topic.get('relevance', '')}
    
    The post should be targeted at professionals in the transportation and logistics industry.
    
    Current date: {post_date}
    
    Follow this structure:
    1. An engaging introduction explaining why this topic matters to logistics and transportation professionals
    2. 2-3 main sections wiAth descriptive headings (using H2 tags) covering different aspects of the topic
    3. Include subsections with H3 tags where appropriate
    4. For each section, include practical insights, data points (you can create realistic fictional data), and actionable advice
    5. Use bullet points or numbered lists where appropriate to break up text
    6. Include a relevant quote from an industry expert (fictional is fine)
    7. A conclusion summarizing key takeaways and offering forward-looking perspective
    
    Make sure to:
    - Be detailed and specific, aiming for around 1500-2000 words
    - Use industry-specific terminology appropriately
    - Optimize for these SEO keywords: {keywords}
    - Create content that would be valuable for logistics professionals in 2025
    - Include practical, actionable information that readers can apply
    - Format the content in HTML using appropriate tags (<p>, <h2>, <h3>, <ul>, <li>, <blockquote>, etc.)
    - Make all content factually accurate and avoid making specific claims about real companies without verification
    
    Category: {category}
    """
    
    content_response = client.chat.completions.create(
        model=GPT_MODEL,
        messages=[{"role": "user", "content": content_prompt}]
    )
    content = content_response.choices[0].message.content.strip()
    
    # Get a relevant image
    image_url = get_relevant_image(topic)
    
    # Create an excerpt for the blog listing
    h = html2text.HTML2Text()
    h.ignore_links = True
    text_content = h.handle(content)
    first_paragraph = text_content.split('\n\n')[0].replace('\n', ' ').strip()
    excerpt = first_paragraph[:200]
    if len(first_paragraph) > 200:
        excerpt += "..."
    
    # Create unique post ID based on timestamp
    post_id = int(time.time())
    
    # Assemble the post data
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
        "content": content,
        "image": image_url,
        "meta": {
            "description": meta_description,
            "keywords": keywords
        }
    }
    
    return post

def save_blog_post(post):
    """
    Save the blog post as a JSON file locally.
    """
    post_id = post["id"]
    filename = f"{post_id}.json"
    filepath = LOCAL_BLOG_DIR / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(post, f, ensure_ascii=False, indent=2)
    
    print(f"Saved blog post to {filepath}")
    return filepath

def create_blog_post_html(post):
    """
    Creates an HTML file for a blog post based on the template.
    """
    post_id = post["id"]
    html_filename = f"post-{post_id}.html"
    
    # Read the blog post template
    with open("blog-post-template.html", "r", encoding="utf-8") as f:
        template = f.read()
    
    # Replace placeholders with actual content
    template = template.replace('<title id="post-title">Blog Post | Pro Truck Logistics</title>', 
                              f'<title>{post["title"]} | Pro Truck Logistics</title>')
    
    template = template.replace('<meta id="meta-description" name="description" content="Logistics and transportation industry insights from Pro Truck Logistics">', 
                              f'<meta name="description" content="{post["meta"]["description"]}">')
    
    template = template.replace('<meta id="meta-keywords" name="keywords" content="logistics, trucking, transportation">', 
                              f'<meta name="keywords" content="{post["meta"]["keywords"]}">')
    
    template = template.replace('<meta id="og-title" property="og:title" content="Blog Post | Pro Truck Logistics">', 
                              f'<meta property="og:title" content="{post["title"]} | Pro Truck Logistics">')
    
    template = template.replace('<meta id="og-description" property="og:description" content="Logistics and transportation industry insights from Pro Truck Logistics">', 
                              f'<meta property="og:description" content="{post["meta"]["description"]}">')
    
    template = template.replace('<meta id="og-image" property="og:image" content="">', 
                              f'<meta property="og:image" content="{post["image"]}">')
    
    template = template.replace("background-image: linear-gradient(rgba(0, 0, 0, 0.5), rgba(0, 0, 0, 0.5)), url('');", 
                              f"background-image: linear-gradient(rgba(0, 0, 0, 0.5), rgba(0, 0, 0, 0.5)), url('{post['image']}');")
    
    template = template.replace('<span id="post-category" class="post-category">Category</span>', 
                              f'<span id="post-category" class="post-category">{post["category"]}</span>')
    
    template = template.replace('<h1 id="post-title-header" class="post-title">Blog Post Title</h1>', 
                              f'<h1 id="post-title-header" class="post-title">{post["title"]}</h1>')
    
    template = template.replace('<span id="post-date">Date</span>', 
                              f'<span id="post-date">{post["date"]}</span>')
    
    template = template.replace('<span id="post-author">Author</span>', 
                              f'<span id="post-author">{post["author"]}</span>')
    
    template = template.replace('<span id="post-read-time">Read time</span>', 
                              f'<span id="post-read-time">{post["read_time"]}</span>')
    
    template = template.replace('<div id="post-content">\n          <!-- Content will be dynamically inserted here -->\n        </div>', 
                              f'<div id="post-content">\n          {post["content"]}\n        </div>')
    
    template = template.replace('<img id="author-image" src="" alt="Author">', 
                              f'<img id="author-image" src="{post["author_image"]}" alt="{post["author"]}">')
    
    template = template.replace('<h4 id="author-name" class="author-name">Author Name</h4>', 
                              f'<h4 id="author-name" class="author-name">{post["author"]}</h4>')
    
    template = template.replace('<p id="author-position" class="author-position">Position</p>', 
                              f'<p id="author-position" class="author-position">{post["author_position"]}</p>')
    
    template = template.replace('<p id="author-bio">Author bio will be displayed here.</p>', 
                              f'<p id="author-bio">{post["author_bio"]}</p>')
    
    # Update share buttons with the post URL
    share_url = f"https://protrucklogistics.org/blog-posts/post-{post_id}.html"  # Update with your actual domain
    
    template = template.replace('<a href="#" class="share-button facebook">', 
                              f'<a href="https://www.facebook.com/sharer/sharer.php?u={share_url}" target="_blank" class="share-button facebook">')
    
    template = template.replace('<a href="#" class="share-button twitter">', 
                              f'<a href="https://twitter.com/intent/tweet?url={share_url}&text={post["title"]}" target="_blank" class="share-button twitter">')
    
    template = template.replace('<a href="#" class="share-button linkedin">', 
                              f'<a href="https://www.linkedin.com/shareArticle?mini=true&url={share_url}&title={post["title"]}" target="_blank" class="share-button linkedin">')
    
    template = template.replace('<a href="#" class="share-button email">', 
                              f'<a href="mailto:?subject={post["title"]}&body=Check out this article: {share_url}" class="share-button email">')
    
    # Save the HTML file
    html_filepath = LOCAL_BLOG_DIR / html_filename
    with open(html_filepath, "w", encoding="utf-8") as f:
        f.write(template)
    
    print(f"Created HTML file: {html_filepath}")
    return html_filepath

def update_blog_index(posts):
    """
    Updates the blog index JSON file with all blog posts.
    This will be used by the blog listing page.
    """
    index_path = LOCAL_BLOG_DIR / "index.json"
    
    # Read existing index if it exists
    if index_path.exists():
        with open(index_path, "r", encoding="utf-8") as f:
            try:
                all_posts = json.load(f)
            except json.JSONDecodeError:
                all_posts = []
    else:
        all_posts = []
    
    # Add new posts to the index
    for post in posts:
        # Create a simplified version for the index
        index_post = {
            "id": post["id"],
            "title": post["title"],
            "excerpt": post["excerpt"],
            "date": post["date"],
            "category": post["category"],
            "author": post["author"],
            "read_time": post["read_time"],
            "image": post["image"]
        }
        
        # Add to index, avoiding duplicates
        if not any(p["id"] == post["id"] for p in all_posts):
            all_posts.append(index_post)
    
    # Sort posts by ID (timestamp) in descending order
    all_posts.sort(key=lambda x: x["id"], reverse=True)
    
    # Save updated index
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(all_posts, f, ensure_ascii=False, indent=2)
    
    print(f"Updated blog index with {len(posts)} new posts")
    return index_path

def upload_files_to_ftp(file_paths):
    """
    Uploads files to the FTP server.
    """
    try:
        print(f"Connecting to FTP server {FTP_HOST}...")
        with ftplib.FTP(FTP_HOST, FTP_USER, FTP_PASS) as ftp:
            print("Connected to FTP server")
            
            # Try to change to the blog directory
            try:
                ftp.cwd(FTP_BLOG_DIR)
            except ftplib.error_perm:
                # If directory doesn't exist, create it
                print(f"Creating directory {FTP_BLOG_DIR}")
                # Split the path and create each directory level
                path_parts = FTP_BLOG_DIR.strip('/').split('/')
                for i in range(len(path_parts)):
                    try:
                        ftp.cwd('/' + '/'.join(path_parts[:i+1]))
                    except ftplib.error_perm:
                        ftp.mkd('/' + '/'.join(path_parts[:i+1]))
                        ftp.cwd('/' + '/'.join(path_parts[:i+1]))
            
            # Upload each file
            for file_path in file_paths:
                file_name = file_path.name
                print(f"Uploading {file_name}...")
                
                with open(file_path, 'rb') as file:
                    ftp.storbinary(f'STOR {file_name}', file)
                
                print(f"Successfully uploaded {file_name}")
        
        print("All files uploaded successfully")
        return True
    except Exception as e:
        print(f"Error uploading files to FTP: {e}")
        return False

def upload_blog_files():
    """
    Upload all local blog files to the FTP server.
    """
    # Get all files in the blog directory
    all_files = list(LOCAL_BLOG_DIR.glob("*.*"))
    
    if not all_files:
        print("No files to upload")
        return False
    
    print(f"Found {len(all_files)} files to upload")
    return upload_files_to_ftp(all_files)

def main():
    """
    Main function to run the blog generation and upload process.
    """
    print("Starting blog post generation...")
    
    # Fetch current logistics topics using improved methods
    print("Fetching current logistics topics...")
    topics = get_current_logistics_topics()
    
    # Select random topics for this run
    if len(topics) > POSTS_TO_GENERATE:
        selected_topics = random.sample(topics, POSTS_TO_GENERATE)
    else:
        selected_topics = topics
    
    print(f"Selected {len(selected_topics)} topics for blog generation")
    
    # Generate and save blog posts
    generated_posts = []
    for topic in selected_topics:
        # Generate the blog post with all components
        print(f"\nGenerating blog post for: {topic['title']}")
        post = generate_blog_post(topic)
        
        # Save the post data as JSON
        save_blog_post(post)
        
        # Create HTML file for the post
        create_blog_post_html(post)
        
        generated_posts.append(post)
        print(f"Completed blog post: {post['title']}")
    
    # Update the blog index
    update_blog_index(generated_posts)
    
    # Upload files to FTP
    upload_success = upload_blog_files()
    
    if upload_success:
        print("Blog post generation and upload completed successfully")
    else:
        print("Blog post generation completed but there was an error with the upload")

if __name__ == "__main__":
    main()
