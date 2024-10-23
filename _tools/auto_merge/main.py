import os
from datetime import datetime
from github import Github

# Authenticate with GitHub
g = Github(os.getenv('GITHUB_TOKEN'))
repo = g.get_repo(os.getenv('GITHUB_REPOSITORY'))
prs = repo.get_pulls(state='open')

today = datetime.today().strftime('%Y-%m-%d')

for pr in prs:
    files = pr.get_files()
    for file in files:
        print(f"Checking file {file}")
        if file.filename.startswith('_posts/') and file.filename.endswith('.md'):
            post_date = file.filename.split('/')[1].split('-')[:3]
            post_date_str = '-'.join(post_date)
            if post_date_str == today:
                pr.merge(merge_method='squash')
                print(f'Merged PR #{pr.number} with post {file.filename}')
