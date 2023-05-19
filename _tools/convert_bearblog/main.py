import csv
import re
import os
import time

import requests

# Made with ChatGPT

def create_markdown_file(article):
    # Extract necessary information from the article
    title = article['title']
    published_date = re.sub(r'\s+', '-', article['published date'].split('T')[0])
    slug = article['slug']
    meta_description = article['meta description']
    meta_image = article['meta image']
    content = article['content']

    # Create the filename for the Markdown file
    filename = f"{published_date}-{slug}.md"

    # Create the YAML front matter
    yaml_front_matter = "---\nlayout: post\n"
    yaml_front_matter += f"title: {title}\n"

    if len(meta_description) > 0:
        yaml_front_matter += f"meta_description: {meta_description}\n"

    if len(meta_image) > 0:
        yaml_front_matter += f"meta_image: {meta_image}\n"

    yaml_front_matter += "---\n\n"

    # Create the Markdown content
    markdown_content = f"{yaml_front_matter}{content}"

    # Save the Markdown file
    with open(filename, 'w', encoding='utf-8') as file:
        file.write(markdown_content)


def import_csv(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            create_markdown_file(row)

def extract_image_urls(file_path):
    image_urls = {}
    with open(file_path, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            slug = row['slug']
            content = row['content']
            urls = re.findall(r'https?://bear-images\.sfo2\.cdn\.digitaloceanspaces\.com/\S+', content)
            if urls:
                image_urls[slug] = [url[:-1] for url in urls]
    return image_urls

def download_images(image_urls, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}

    for slug, urls in image_urls.items():
        for i, url in enumerate(urls, 1):
            time.sleep(1)
            _, ext = os.path.splitext(url)
            filename = os.path.join(output_dir, f"{slug}-{i}{ext}")
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                with open(filename, 'wb') as file:
                    file.write(response.content)
                    print(f"Downloaded: {filename}")
            else:
                print(f"Failed to download: {url}")

if __name__ == "__main__":
    # Specify the path to the CSV file
    csv_file_path = '20230518_post_export.csv'
    #
    # Import the CSV file and create Markdown files
    import_csv(csv_file_path)


    # images = extract_image_urls("20230518_post_export.csv")
    # download_images(images, "assets")

    # with open("20230518_post_export.csv", 'r') as file:
    #     posts = file.read()
    #
    #     for title, urls in images.items():
    #         for i, url in enumerate(urls, 1):
    #             _, ext = os.path.splitext(url)
    #             posts = posts.replace(url, f"assets/{title}-{i}{ext}")
    #
    # with open("20230518_post_export.csv", 'w') as file:
    #     file.write(posts)
