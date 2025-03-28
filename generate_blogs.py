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
import paramiko
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from openai import OpenAI
from PIL import Image
from io import BytesIO

# Configuration - these will come from GitHub Secrets in production
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "your-api-key-here")
FTP_HOST = os.environ.get("FTP_HOST", "ftp.yourdomain.com")
FTP_USER = os.environ.get("FTP_USER", "your-username")
FTP_PASS = os.environ.get("FTP_PASS", "your-password")
FTP_BLOG_DIR = "/blog-posts/" # Directory relative to web root
FTP_IS_SFTP = os.environ.get("FTP_IS_SFTP", "false").lower() == "true"  # Set to true for SFTP instead of FTP

# Local blog post storage
LOCAL_BLOG_DIR = Path("blog-posts")
LOCAL_BLOG_DIR.mkdir(exist_ok=True)

# Create images directory
IMAGES_DIR = LOCAL_BLOG_DIR / "images"
IMAGES_DIR.mkdir(exist_ok=True)

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
    Fetches current trending topics in logistics using GPT with web search capabilities.
    Falls back to category-based topic generation if web search fails.
    Returns a list of news articles with titles and summaries.
    """
    method_used = "Unknown"
    
    # First try: Use GPT with tool use capability and more specific trucking focus
    try:
        print("Attempting to get current logistics news via GPT with browsing capability...")
        
        # Updated tools format for web browsing
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
        
        # First message to call the search function with more specific semi-truck focus
        first_response = client.chat.completions.create(
            model=BROWSING_MODEL,  # Use a model that supports function calling
            messages=[{"role": "user", "content": "What are the latest news and trending topics in the semi-truck transportation and logistics industry from the past week? Focus specifically on commercial trucking, freight hauling, and long-haul transportation."}],
            tools=tools,
            tool_choice={"type": "function", "function": {"name": "search_web"}}
        )
        
        # Check if we have a tool call in the response
        message = first_response.choices[0].message
        
        if hasattr(message, 'tool_calls') and message.tool_calls:
            # Get the search query
            tool_call = message.tool_calls[0]
            function_args = json.loads(tool_call.function.arguments)
            search_query = function_args.get("query")
            
            print(f"Searching for: {search_query}")
            
            # Try multiple search queries for better results
            search_queries = [
                search_query,
                "latest semi truck industry news and developments",
                "commercial trucking industry trends this month",
                "freight transportation challenges and innovations"
            ]
            
            # Second call to process the "search results" with more specific instructions
            second_response = client.chat.completions.create(
                model=BROWSING_MODEL,
                messages=[
                    {"role": "user", "content": "What are the latest news and trending topics in the semi-truck transportation and logistics industry from the past week? Focus specifically on commercial trucking, freight hauling, and long-haul transportation."},
                    message,
                    {
                        "role": "tool", 
                        "tool_call_id": tool_call.id,
                        "name": "search_web",
                        "content": f"Search results found many recent articles about semi-truck logistics industry trends using queries: {', '.join(search_queries)}"
                    },
                    {
                        "role": "user",
                        "content": """Based on these search results, provide 5 significant developments or trends in the semi-truck transportation and logistics industry that a trucking company might want to write about in their blog.
                        
                        For each topic, provide:
                        1. A specific headline that would appeal to commercial truck fleet operators and logistics managers
                        2. A brief summary (1-2 sentences) focused on semi-trucks and freight transportation
                        3. Why this topic matters to semi-truck logistics professionals
                        
                        Make sure topics are specifically relevant to a semi-truck logistics company, not general logistics.
                        
                        Format your response as JSON with an array of objects containing "title", "summary", and "relevance" keys."""
                    }
                ]
            )
            
            content = second_response.choices[0].message.content
            
            # Try to extract JSON from the response
            try:
                # Check for JSON code blocks
                json_match = re.search(r'```json\s*([\s\S]*?)\s*```', content)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    # Look for array pattern
                    json_match = re.search(r'(\[\s*\{.*\}\s*\])', content, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(1)
                    else:
                        json_str = content
                
                topics = json.loads(json_str)
                
                # Validate that topics are actually about semi-trucks/commercial trucking
                valid_topics = []
                for topic in topics:
                    title = topic.get('title', '').lower()
                    summary = topic.get('summary', '').lower()
                    if any(term in title or term in summary for term in ['truck', 'fleet', 'haul', 'freight', 'driver', 'diesel', 'semi', 'transport']):
                        valid_topics.append(topic)
                
                if len(valid_topics) >= 3:
                    print(f"Successfully retrieved {len(valid_topics)} trending topics via GPT")
                    method_used = "GPT Web Search"
                    return valid_topics
                else:
                    print("Retrieved topics weren't specifically about semi-trucks, trying another method")
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON from GPT response: {e}")
                # Continue to second try below
        else:
            print("No tool calls in the response")
    
    except Exception as e:
        print(f"Error using GPT with web search capability: {e}")
    
    # Second try: Generate realistic trending topics with GPT with more semi-truck focus
    try:
        print("Attempting to generate realistic trending topics with GPT...")
        
        current_date = datetime.now().strftime("%B %d, %Y")
        
        prompt = f"""
        Today is {current_date}. Based on current industry trends and economic conditions, 
        what are 5 realistic trending topics in the semi-truck transportation and logistics industry that would 
        make good blog post topics for a commercial trucking company?

        For each topic, include:
        1. A specific headline/title that mentions semi-trucks, commercial trucking, or freight hauling
        2. A brief summary of the trend/issue specifically for semi-truck operators and fleet managers
        3. Why this topic is relevant right now to the commercial trucking industry

        Focus on topics that would be relevant in 2025 such as:
        - New regulations or compliance issues affecting semi-truck operators
        - Technology adoption in commercial trucking fleets
        - Diesel prices and alternative fuels for semi-trucks
        - Supply chain resilience for freight haulers
        - Labor market trends for commercial truck drivers
        - Market conditions affecting long-haul shipping rates
        - Semi-truck maintenance and fleet management innovations
        - Safety technologies for commercial trucks

        Format your response as a JSON array with objects containing "title", "summary", and "relevance" keys.
        """
        
        response = client.chat.completions.create(
            model=GPT_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        
        content = response.choices[0].message.content
        
        # Try to extract JSON
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', content)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_match = re.search(r'(\[\s*\{.*\}\s*\])', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = content
        
        try:
            topics = json.loads(json_str)
            print(f"Successfully generated {len(topics)} trending topics via GPT")
            method_used = "GPT Generated Trends"
            return topics
        except:
            print("Failed to parse JSON from GPT trend generation")
            # Continue to fallback below
    except Exception as e:
        print(f"Error generating trending topics: {e}")
    
    # Third try: Use trucking-specific websites
    try:
        print("Attempting to fetch news from trucking websites...")
        news_articles = []
        
        # Try multiple trucking industry websites
        websites = [
            {"url": "https://www.ttnews.com/articles/logistics", "article_selector": "article", "title_selector": "h2", "summary_selector": "div.field--name-field-deckhead"},
            {"url": "https://www.ccjdigital.com/", "article_selector": "article", "title_selector": "h2,h3", "summary_selector": "p.entry-summary"},
            {"url": "https://www.overdriveonline.com/", "article_selector": "article", "title_selector": "h2,h3", "summary_selector": "p"},
            {"url": "https://www.fleetowner.com/", "article_selector": "div.node--type-article", "title_selector": "h2,h3", "summary_selector": "div.field--name-field-subheadline"}
        ]
        
        for site in websites:
            try:
                response = requests.get(site["url"], timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    articles = soup.select(site["article_selector"])
                    
                    for article in articles[:3]:  # Get top 3 articles from each site
                        title_element = article.select_one(site["title_selector"])
                        title = title_element.text.strip() if title_element else "Unknown Title"
                        
                        summary_element = article.select_one(site["summary_selector"])
                        summary = summary_element.text.strip() if summary_element else ""
                        
                        # Create relevance if missing
                        relevance = f"This topic is relevant to semi-truck operators and fleet managers because it addresses current industry challenges and opportunities in {datetime.now().year}."
                        
                        # Only add if it seems to be about trucking
                        if any(term in title.lower() or term in summary.lower() for term in ['truck', 'fleet', 'haul', 'freight', 'driver', 'diesel', 'semi', 'transport']):
                            news_articles.append({
                                "title": title, 
                                "summary": summary, 
                                "relevance": relevance
                            })
            except Exception as e:
                print(f"Error fetching from {site['url']}: {e}")
                continue
        
        if len(news_articles) >= 3:
            print(f"Successfully fetched {len(news_articles)} articles from trucking websites")
            method_used = "Website Scraping"
            return news_articles
    except Exception as e:
        print(f"Error fetching from trucking websites: {e}")
    
    # Final fallback: Generate topics based on blog categories
    print("Using category-based topic generation")
    method_used = "Category-Based Generation"
    
    # Select random categories to generate topics for
    selected_categories = random.sample(BLOG_CATEGORIES, min(5, len(BLOG_CATEGORIES)))
    
    category_topics = []
    for category in selected_categories:
        try:
            # Generate a topic based on the category
            prompt = f"""
            Generate a blog post topic for a semi-truck logistics company in the category: "{category}".
            
            The topic should be:
            1. Specifically about commercial trucking, semi-trucks, or freight hauling
            2. Relevant to fleet managers and truck operators
            3. Timely and interesting for 2025
            
            Return a JSON object with:
            - "title": A catchy headline that mentions trucks, fleets, or freight
            - "summary": A brief 1-2 sentence description of the topic
            - "relevance": Why this matters to semi-truck logistics professionals
            
            Make sure the topic is specifically about semi-trucks and commercial trucking, not general logistics.
            """
            
            response = client.chat.completions.create(
                model=GPT_MODEL,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response.choices[0].message.content
            
            # Try to extract JSON
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', content)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_match = re.search(r'(\{.*\})', content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    json_str = content
            
            topic = json.loads(json_str)
            
            # Add the category to the topic
            topic["category"] = category
            
            category_topics.append(topic)
            print(f"Generated topic for category: {category}")
            
        except Exception as e:
            print(f"Error generating topic for category {category}: {e}")
            continue
    
    if category_topics:
        return category_topics
    
    # Absolute last resort - hardcoded topics with semi-truck focus
    print("Using hardcoded semi-truck topics as last resort")
    fallback_topics = [
        {
            "title": "Next-Gen Semi-Truck Cabs: How Driver Comfort is Revolutionizing Fleet Retention",
            "summary": "Modern semi-truck cab designs are incorporating unprecedented comfort features, from premium sleeping quarters to advanced climate control systems, transforming the driver experience.",
            "relevance": "With driver turnover rates still above 90% in many fleets, investing in driver comfort has become a critical strategy for retaining experienced operators."
        },
        {
            "title": "Commercial Fleet Electrification: Real-World ROI Data from Early Semi-Truck Adopters",
            "summary": "New data reveals the actual cost savings and operational impacts from logistics companies that were early adopters of electric semi-trucks on specific routes.",
            "relevance": "As more manufacturers release commercial electric vehicles, fleet managers need concrete data from similar operations to make informed transition decisions."
        },
        {
            "title": "AI-Powered Route Optimization: Saving Diesel and Hours for Long-Haul Truckers",
            "summary": "Advanced AI algorithms are revolutionizing semi-truck route planning, reducing delivery times by up to 25% and cutting fuel consumption for commercial fleets.",
            "relevance": "With diesel prices remaining volatile, logistics companies must leverage technology to maintain competitive advantages in the long-haul sector."
        },
        {
            "title": "Semi-Truck Maintenance Revolution: Predictive Analytics Cutting Downtime by 60%",
            "summary": "New predictive maintenance systems for commercial trucks are identifying potential failures before they happen, dramatically reducing costly roadside breakdowns.",
            "relevance": "Each day of semi-truck downtime costs operators thousands in lost revenue and penalties, making preventative maintenance a top priority for fleet managers."
        },
        {
            "title": "Navigating HOS Regulations: Smart Compliance Tools for Fleet Dispatchers",
            "summary": "New dispatcher-focused software is helping fleet managers optimize loads while ensuring drivers remain compliant with Hours of Service regulations.",
            "relevance": "With increased enforcement of electronic logging device regulations, fleets need smarter tools to maximize efficiency while avoiding costly violations."
        }
    ]
    
    return fallback_topics

def get_relevant_image(topic):
    """
    First generates a custom DALL-E prompt based on the blog post topic,
    then uses that prompt to generate a unique image.
    """
    print(f"Generating custom image for topic: {topic}")
    
    # Extract title and summary for the prompt if topic is a dictionary
    topic_title = topic.get('title', '') if isinstance(topic, dict) else topic
    topic_summary = topic.get('summary', '') if isinstance(topic, dict) else ''
    topic_relevance = topic.get('relevance', '') if isinstance(topic, dict) else ''
    
    # Generate a custom DALL-E prompt using GPT
    print("Creating custom image prompt with GPT...")
    
    prompt_creation_prompt = f"""
    Create a detailed and specific prompt for DALL-E to generate an image for a blog post about:
    
    Title: "{topic_title}"
    Summary: {topic_summary}
    Relevance: {topic_relevance}
    
    The prompt should:
    1. Describe a specific, visually interesting scene related to the blog topic
    2. Include details about composition, perspective, lighting, mood, and setting
    3. Be highly specific to avoid generic stock photo aesthetics
    4. Ensure the image will clearly relate to commercial trucking and logistics
    5. Include clear visual elements that connect to the blog's main points
    6. Specify photorealistic style and professional quality
    7. Be unexpected and original - avoid clichéd trucking images
    
    Keep the prompt between 100-150 words for optimal results.
    Output only the prompt itself with no additional text or explanation.
    """
    
    # Get the custom prompt from GPT
    prompt_response = client.chat.completions.create(
        model=GPT_MODEL,
        messages=[{"role": "user", "content": prompt_creation_prompt}]
    )
    
    custom_image_prompt = prompt_response.choices[0].message.content.strip()
    print(f"Generated custom DALL-E prompt: {custom_image_prompt[:100]}...")
    
    # Generate image using the custom prompt
    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=custom_image_prompt,
            size="1024x1024",
            quality="standard",
            n=1
        )
        
        # Get the URL from the response
        image_url = response.data[0].url
        print(f"Successfully generated unique image with DALL-E")
        return image_url
    except Exception as e:
        print(f"DALL-E image generation failed: {e}")
        raise RuntimeError(f"DALL-E image generation failed: {e}")

def download_and_save_image(image_url, post_id):
    """
    Downloads an image from a URL and saves it to the local images directory.
    Returns the local path to the saved image.
    """
    
    # Generate a filename based on post ID
    local_filename = f"post-image-{post_id}.png"
    local_path = IMAGES_DIR / local_filename
    
    print(f"Downloading image from {image_url} to {local_path}")
    
    try:
        # Download the image
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        # Save the image
        img = Image.open(BytesIO(response.content))
        img.save(local_path)
        
        print(f"Image saved successfully to {local_path}")
        
        # Return the relative path for use in HTML
        return f"blog-posts/images/{local_filename}"
    except Exception as e:
        print(f"Error downloading/saving image: {e}")
        # Return a placeholder image in case of failure
        return "https://i.imgur.com/tRwURlo.jpeg"
    
def generate_blog_post(topic):
    """
    Generate a comprehensive blog post using the topic data.
    Returns a dictionary with the post details and content.
    """
    print(f"Generating blog post about: {topic['title']}")
    
    # Select a random author
    author = random.choice(AUTHORS)
    
    # Use the topic's category if available, otherwise select a relevant one
    if "category" in topic:
        category = topic["category"]
    else:
        # Try to match a relevant category based on the topic
        topic_text = (topic['title'] + ' ' + topic.get('summary', '')).lower()
        
        # Define category keywords for matching
        category_keywords = {
            "Industry Trends": ["trend", "industry", "market", "outlook", "future"],
            "Market Analysis": ["market", "analysis", "data", "statistics", "report"],
            "Economic Outlook": ["economic", "economy", "forecast", "financial", "cost"],
            "Supply Chain Management": ["supply chain", "inventory", "procurement", "sourcing"],
            "Driver Recruitment": ["recruit", "hiring", "driver shortage", "talent", "workforce"],
            "Driver Retention": ["retention", "turnover", "driver satisfaction", "career"],
            "Sustainability": ["sustainable", "green", "environment", "emission", "carbon"],
            "Technology Trends": ["technology", "tech", "innovation", "digital", "software"],
            "Safety": ["safety", "accident", "prevention", "risk", "secure"],
            "Regulations": ["regulation", "compliance", "law", "legal", "requirement"],
            "Fleet Management": ["fleet", "management", "maintenance", "vehicle", "asset"],
            "Fuel Management": ["fuel", "diesel", "gas", "consumption", "efficiency"]
        }
        
        # Find the best matching category
        best_match = None
        best_score = 0
        
        for cat, keywords in category_keywords.items():
            score = sum(topic_text.count(keyword) for keyword in keywords)
            if score > best_score:
                best_score = score
                best_match = cat
        
        # If no good match, pick from the most relevant categories for a trucking company
        if best_match is None or best_score == 0:
            trucking_focused_categories = [
                "Fleet Management", "Driver Retention", "Fuel Management", 
                "Safety", "Regulations", "Technology Trends"
            ]
            category = random.choice(trucking_focused_categories)
        else:
            category = best_match
    
    # Generate a reasonable reading time (1500-2000 words is about 7-10 mins)
    read_time = random.randint(7, 10)
    
    # Current date for the post
    post_date = datetime.now().strftime("%B %d, %Y")
    
    # Generate SEO meta description
    print("Generating meta description...")
    meta_description_prompt = f"""
    Write an SEO-optimized meta description for a blog post about "{topic['title']}" for a semi-truck logistics company.
    The description should:
    - Be compelling and include keywords related to commercial trucking
    - Mention semi-trucks, fleet management, or freight hauling
    - Be under 160 characters
    - Appeal to truck fleet operators and logistics managers
    """
    
    meta_description_response = client.chat.completions.create(
        model=GPT_MODEL,
        messages=[{"role": "user", "content": meta_description_prompt}]
    )
    meta_description = meta_description_response.choices[0].message.content.strip()
    
    # Generate SEO keywords
    print("Generating SEO keywords...")
    keywords_prompt = f"""
    Generate 5-7 SEO keywords or phrases for a blog post about "{topic['title']}" for a semi-truck logistics company. 
    Include keywords specifically related to commercial trucking, semi-trucks, and freight hauling.
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
    
    The post should be targeted at semi-truck fleet operators, commercial truck drivers, and logistics managers in the trucking industry.
    
    Current date: {post_date}
    
    Follow this structure:
    1. An engaging introduction explaining why this topic matters specifically to semi-truck operators and fleet managers
    2. 2-3 main sections with descriptive headings (using H2 tags) covering different aspects of the topic as it relates to commercial trucking
    3. Include subsections with H3 tags where appropriate
    4. For each section, include practical insights, data points (you can create realistic fictional data), and actionable advice for trucking companies
    5. Use bullet points or numbered lists where appropriate to break up text
    6. Include a relevant quote from a trucking industry expert (fictional is fine)
    7. A conclusion summarizing key takeaways and offering forward-looking perspective for semi-truck fleet operators
    
    Make sure to:
    - Be detailed and specific, aiming for around 1500-2000 words
    - Use trucking industry-specific terminology appropriately (semi, rig, haul, fleet, etc.)
    - Mention semi-trucks, commercial trucking, or freight hauling frequently
    - Optimize for these SEO keywords: {keywords}
    - Create content that would be valuable for semi-truck logistics professionals in 2025
    - Include practical, actionable information that truck fleet managers can apply
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
    dalle_image_url = get_relevant_image(topic)
    
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
    
    # Download and save the image locally
    local_image_path = download_and_save_image(dalle_image_url, post_id)
    
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
        "image": local_image_path,
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
        
    # Get the correct image path 
    image_path = post["image"]
    
    # Ensure the image path is absolute (starts with /) for consistent referencing
    if image_path and not image_path.startswith('/') and not image_path.startswith('http'):
        image_path = f"/{image_path}"
    
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

def upload_files_to_server():
    """
    Uploads all files in the blog-posts directory to the server.
    Handles both FTP and SFTP connections.
    """
    print(f"Uploading files to server {FTP_HOST}...")
    
    if FTP_IS_SFTP:
        return upload_files_via_sftp()
    else:
        return upload_files_via_ftp()

def upload_files_via_sftp():
    """
    Uploads files using SFTP protocol.
    """
    try:
        # Create an SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        print(f"Connecting to SFTP server {FTP_HOST}...")
        ssh.connect(hostname=FTP_HOST, username=FTP_USER, password=FTP_PASS)
        sftp = ssh.open_sftp()
        
        # Check if blog directory exists, create if needed
        try:
            sftp.stat(FTP_BLOG_DIR)
        except FileNotFoundError:
            print(f"Creating directory {FTP_BLOG_DIR}")
            # Create the directory and any parent directories
            path_parts = FTP_BLOG_DIR.strip('/').split('/')
            current_path = ""
            for part in path_parts:
                current_path += f"/{part}"
                try:
                    sftp.stat(current_path)
                except FileNotFoundError:
                    sftp.mkdir(current_path)
        
        # Check if images directory exists, create if needed
        images_remote_path = f"{FTP_BLOG_DIR}/images"
        try:
            sftp.stat(images_remote_path)
        except FileNotFoundError:
            print(f"Creating directory {images_remote_path}")
            sftp.mkdir(images_remote_path)
        
        # Get all files in the blog directory
        all_files = list(LOCAL_BLOG_DIR.glob("*.json")) + list(LOCAL_BLOG_DIR.glob("*.html"))
        
        # Get all files in the images subdirectory
        image_files = list(IMAGES_DIR.glob("*.*"))
        
        # Upload regular blog files
        for file_path in all_files:
            remote_path = f"{FTP_BLOG_DIR}/{file_path.name}"
            print(f"Uploading {file_path.name} to {remote_path}...")
            sftp.put(str(file_path), remote_path)
            print(f"Successfully uploaded {file_path.name}")
        
        # Upload image files
        for file_path in image_files:
            remote_path = f"{images_remote_path}/{file_path.name}"
            print(f"Uploading image {file_path.name} to {remote_path}...")
            sftp.put(str(file_path), remote_path)
            print(f"Successfully uploaded image {file_path.name}")
        
        # Close connections
        sftp.close()
        ssh.close()
        
        print("All files uploaded successfully via SFTP")
        return True
    except Exception as e:
        print(f"Error uploading files via SFTP: {e}")
        return False

def upload_files_via_ftp():
    """
    Uploads files using traditional FTP protocol.
    """
    try:
        import ftplib
        
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
            
            # Create images directory if it doesn't exist
            try:
                ftp.cwd('images')
                ftp.cwd('..')  # Go back to parent directory
            except ftplib.error_perm:
                try:
                    ftp.mkd('images')
                    print("Created 'images' directory on FTP server")
                except ftplib.error_perm as e:
                    print(f"Error creating images directory: {e}")
            
            # Get all files in the blog directory
            all_files = list(LOCAL_BLOG_DIR.glob("*.json")) + list(LOCAL_BLOG_DIR.glob("*.html"))
            
            # Get all files in the images subdirectory
            image_files = list(IMAGES_DIR.glob("*.*"))
            
            # Upload regular blog files
            for file_path in all_files:
                file_name = file_path.name
                print(f"Uploading {file_name}...")
                
                with open(file_path, 'rb') as file:
                    ftp.storbinary(f'STOR {file_name}', file)
                
                print(f"Successfully uploaded {file_name}")
            
            # Upload image files
            if image_files:
                ftp.cwd('images')
                for file_path in image_files:
                    file_name = file_path.name
                    print(f"Uploading image {file_name}...")
                    
                    with open(file_path, 'rb') as file:
                        ftp.storbinary(f'STOR {file_name}', file)
                    
                    print(f"Successfully uploaded image {file_name}")
                ftp.cwd('..')  # Go back to parent directory
        
        print("All files uploaded successfully via FTP")
        return True
    except Exception as e:
        print(f"Error uploading files via FTP: {e}")
        return False
    
def upload_blog_files():
    """
    Upload all local blog files to the FTP server.
    """
    # Get all files in the blog directory
    all_files = list(LOCAL_BLOG_DIR.glob("*.*"))
    
    # Get all files in the images subdirectory
    image_files = list((LOCAL_BLOG_DIR / "images").glob("*.*"))
    
    # Combine both lists
    all_files.extend(image_files)
    
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
    upload_success = upload_files_to_server()
    
    if upload_success:
        print("Blog post generation and upload completed successfully")
    else:
        print("Blog post generation completed but there was an error with the upload")

if __name__ == "__main__":
    main()
