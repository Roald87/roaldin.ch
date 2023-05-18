import csv
import re

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


if __name__ == "__main__":
    # Specify the path to the CSV file
    csv_file_path = '20230518_post_export.csv'

    # Import the CSV file and create Markdown files
    import_csv(csv_file_path)
