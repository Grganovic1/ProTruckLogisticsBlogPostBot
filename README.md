# Pro Truck Logistics Blog Generator

This repository contains an automated blog post generation system for Pro Truck Logistics. It uses OpenAI's GPT-3.5 Turbo to create high-quality, SEO-optimized blog posts about logistics and transportation topics, then uploads them to the website via FTP.

## How It Works

1. **Daily Automation**: Every day at 8:00 AM UTC, GitHub Actions runs the blog generation script
2. **Topic Selection**: The script fetches current logistics industry news for relevant topics
3. **AI Content Generation**: OpenAI GPT-3.5 Turbo creates detailed, SEO-optimized blog posts
4. **Image Selection**: Each post gets a relevant image from Unsplash
5. **FTP Upload**: All files are automatically uploaded to the Namecheap hosting server
6. **Website Display**: The blog.html page displays posts using blog-loader.js

## Repository Structure
pro-truck-blog-generator/
│
├── .github/workflows/           # GitHub Actions configuration
│   └── blog-generator.yml       # Workflow definition file
│
├── blog-posts/                  # Local storage for generated posts
│
├── blog-post-template.html      # Template for individual blog posts
├── blog-loader.js               # JavaScript to load and display posts
├── generate_blogs.py            # Python script for blog generation
└── README.md                    # Documentation (this file)

## Setup Instructions

### Prerequisites

- GitHub account
- OpenAI API key
- Namecheap hosting with FTP access

### GitHub Secrets Configuration

The following secrets must be configured in your GitHub repository:

1. `OPENAI_API_KEY`: Your OpenAI API key
2. `FTP_HOST`: Your Namecheap FTP hostname (usually ftp.yourdomain.com)
3. `FTP_USER`: Your FTP username
4. `FTP_PASS`: Your FTP password

To add these secrets:
1. Go to your repository on GitHub
2. Click on "Settings" → "Secrets and variables" → "Actions"
3. Click "New repository secret" and add each secret

### Namecheap Setup

1. Upload `blog.html` to your website's public_html directory
2. Upload `blog-loader.js` to your website's public_html directory
3. Create a `blog-posts` directory in your public_html folder

## Customization

### Modifying Blog Categories

Edit the `BLOG_CATEGORIES` list in `generate_blogs.py` to change the categories for blog posts.

### Changing Post Frequency

To change how many posts are generated each day, edit the `POSTS_TO_GENERATE` variable in `generate_blogs.py`.

### Scheduling

To change when posts are generated, edit the cron schedule in `.github/workflows/blog-generator.yml`.

## Troubleshooting

### No Posts Appearing

1. Check if the GitHub Action ran successfully
2. Verify FTP credentials are correct
3. Check if the `blog-posts` directory exists on your server
4. Look for JavaScript errors in your browser's console

### API Key Issues

If you see authentication errors in the GitHub Actions logs, check your OpenAI API key.

## Costs

This system uses GPT-3.5 Turbo, which costs approximately $0.15 per day for generating 3 blog posts.

## License

This project is for exclusive use by Pro Truck Logistics and is not available for redistribution.

## Support

For support, please contact the repository administrator.