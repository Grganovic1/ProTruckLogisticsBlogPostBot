#!/usr/bin/env python3
"""
Blog Post Generator for Pro Truck Logistics

This script:
1. Fetches current logistics/transportation news
2. Uses GPT-3.5 Turbo to generate blog posts
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
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from openai import OpenAI

# Configuration - these will come from GitHub Secrets in production
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "your-api-key-here")
FTP_HOST = os.environ.get("FTP_HOST", "ftp.yourdomain.com")
FTP_USER = os.environ.get("FTP_USER", "your-username")
FTP_PASS = os.environ.get("FTP_PASS", "your-password")
FTP_BLOG_DIR = "/public_html/blog-posts/" # Update this to your blog directory on Namecheap

# Local blog post storage
LOCAL_BLOG_DIR = Path("blog-posts")
LOCAL_BLOG_DIR.mkdir(exist_ok=True)

# Number of blog posts to generate
POSTS_TO_GENERATE = 3

# Blog post categories
BLOG_CATEGORIES = [
    "Industry Trends", "Supply Chain", "Driver Tips", "Sustainability", 
    "Technology", "Safety", "Regulations", "Fleet Management"
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

def fetch_logistics_news():
    """
    Fetches recent news from logistics and transportation industry sources.
    Returns a list of news articles with titles and summaries.
    """
    news_articles = []
    
    # Try multiple sources to ensure we get some news
    try:
        # Transport Topics
        response = requests.get("https://www.ttnews.com/articles/logistics", timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            articles = soup.find_all('article', class_='article-card')
            
            for article in articles[:5]:  # Get top 5 articles
                title_element = article.find('h2')
                title = title_element.text.strip() if title_element else "Unknown Title"
                
                summary_element = article.find('div', class_='field--name-field-deckhead')
                summary = summary_element.text.strip() if summary_element else ""
                
                news_articles.append({"title": title, "summary": summary})
    except Exception as e:
        print(f"Error fetching from Transport Topics: {e}")
    
    # Try Logistics Management as backup
    if len(news_articles) < 3:
        try:
            response = requests.get("https://www.logisticsmgmt.com/topic/category/transportation", timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                articles = soup.find_all('article')
                
                for article in articles[:5]:
                    title_element = article.find('h2') or article.find('h3')
                    title = title_element.text.strip() if title_element else "Unknown Title"
                    
                    summary_element = article.find('p')
                    summary = summary_element.text.strip() if summary_element else ""
                    
                    news_articles.append({"title": title, "summary": summary})
        except Exception as e:
            print(f"Error fetching from Logistics Management: {e}")
    
    # Fallback topics if we couldn't get any news
    if len(news_articles) == 0:
        news_articles = [
            {"title": "Supply Chain Resilience Strategies", "summary": "How companies are strengthening their supply chains against disruptions"},
            {"title": "Electric Truck Adoption Rates Climbing", "summary": "Latest market data shows accelerating shift to electric commercial vehicles"},
            {"title": "New Hours of Service Regulations Impact", "summary": "Analysis of how recent regulatory changes are affecting the industry"},
            {"title": "Warehouse Automation Technologies", "summary": "Emerging technologies transforming logistics warehouse operations"},
            {"title": "Last-Mile Delivery Optimization", "summary": "Strategies for improving efficiency in the most expensive segment of delivery"}
        ]
    
    print(f"Fetched {len(news_articles)} news articles")
    return news_articles

def get_relevant_image(topic):
    """
    Gets a relevant image URL from Unsplash based on the topic.
    """
    try:
        # Create search query based on topic
        search_terms = "+".join(topic.lower().split()[:3])
        search_query = f"{search_terms}+logistics+transportation+truck"
        
        # Use Unsplash source for a random image matching the query
        url = f"https://source.unsplash.com/1600x900/?{search_query}"
        response = requests.get(url, timeout=10)
        
        # Unsplash redirects to a random image URL matching the query
        if response.status_code == 200:
            return response.url
    except Exception as e:
        print(f"Error fetching image: {e}")
    
    # Fallback images
    fallback_images = [
        "https://images.unsplash.com/photo-1519003722824-194d4455a60c?ixlib=rb-4.0.3", # Truck on highway
        "https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?ixlib=rb-4.0.3", # Truck driver
        "https://images.unsplash.com/photo-1620066326605-44146cb883cd?ixlib=rb-4.0.3", # Supply chain
        "https://images.unsplash.com/photo-1611858246382-da4877c6476d?ixlib=rb-4.0.3", # Electric truck
        "https://images.unsplash.com/photo-1577041677443-8bbdfd8cce62?ixlib=rb-4.0.3", # Truck safety
        "https://images.unsplash.com/photo-1494412574643-ff11b0a5c1c3?ixlib=rb-4.0.3", # Road
        "https://images.unsplash.com/photo-1591453089816-0fbb971b454c?ixlib=rb-4.0.3"  # Warehouse
    ]
    return random.choice(fallback_images)

def generate_blog_post(topic, category):
    """
    Generate a complete blog post using OpenAI.
    Returns a dictionary with the post details and content.
    """
    print(f"Generating blog post about: {topic}")
    
    # Select a random author
    author = random.choice(AUTHORS)
    
    # Generate a reasonable reading time (1000-2000 words is about 5-10 mins)
    read_time = random.randint(5, 10)
    
    # Current date for the post
    post_date = datetime.now().strftime("%B %d, %Y")
    
    # Generate SEO meta description
    print("Generating meta description...")
    meta_description_prompt = f"""
    Write an SEO-optimized meta description for a blog post about "{topic}" in the logistics and transportation industry.
    The description should be compelling, include keywords, and be under 160 characters.
    """
    
    meta_description_response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": meta_description_prompt}]
    )
    meta_description = meta_description_response.choices[0].message.content.strip()
    
    # Generate SEO keywords
    print("Generating SEO keywords...")
    keywords_prompt = f"""
    Generate 5-7 SEO keywords or phrases for a blog post about "{topic}" in the logistics and transportation industry. 
    Format them as a comma-separated list only. No numbering or bullets.
    """
    
    keywords_response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": keywords_prompt}]
    )
    keywords = keywords_response.choices[0].message.content.strip()
    
    # Generate blog post title
    print("Generating blog post title...")
    title_prompt = f"""
    Create an engaging, SEO-optimized title for a blog post about "{topic}" in the logistics industry.
    The title should be compelling, include keywords, and be under 60 characters if possible.
    Make it specific and action-oriented.
    """
    
    title_response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": title_prompt}]
    )
    title = title_response.choices[0].message.content.strip()
    
    # Generate blog post content
    print("Generating main blog content...")
    content_prompt = f"""
    Write a comprehensive, detailed, and informative blog post about "{topic}" for Pro Truck Logistics company blog.
    The post should be targeted at professionals in the transportation and logistics industry.
    
    Current date: {post_date}
    
    Follow this structure:
    1. An engaging introduction explaining why this topic matters to logistics and transportation professionals
    2. 2-3 main sections with descriptive headings (using H2 tags) covering different aspects of the topic
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
        model="gpt-3.5-turbo",
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
        "title": title,
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
    share_url = f"https://www.yourdomain.com/post-{post_id}.html"  # Update with your actual domain
    
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
    
    # Fetch current news for blog topics
    news_articles = fetch_logistics_news()
    
    # Select random topics from the news
    if len(news_articles) > POSTS_TO_GENERATE:
        selected_topics = random.sample(news_articles, POSTS_TO_GENERATE)
    else:
        selected_topics = news_articles
    
    # Generate and save blog posts
    generated_posts = []
    for topic in selected_topics:
        # Select a random category for this post
        category = random.choice(BLOG_CATEGORIES)
        
        # Generate the blog post
        post = generate_blog_post(topic["title"], category)
        
        # Save the post data as JSON
        save_blog_post(post)
        
        # Create HTML file for the post
        create_blog_post_html(post)
        
        generated_posts.append(post)
    
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