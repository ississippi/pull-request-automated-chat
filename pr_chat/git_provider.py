import os
import boto3
import json
import time
import requests
from github import Github
from github import Auth
from datetime import datetime, timezone
from dateutil import tz
from zoneinfo import ZoneInfo
from pathlib import Path

owner = "TheAlgorithms"
repo = "Python"
owner = "public-apis"
repo = "public-apis"
pull_number = 25653  # Replace with the desired PR number
url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}"
pulls_url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
# vinta_pulls = "https://api.github.com/vinta/awesome-python/pulls"  # Example for a different repo
SUPPORTED_EXTENSIONS = {'.py', '.js', '.ts', '.java', '.cs', '.cpp', '.c', '.go', '.rb'}

# Create an SSM client
ssm = boto3.client('ssm')
def get_parameter(name):
    """Fetch parameter value from Parameter Store"""
    response = ssm.get_parameter(
        Name=name,
        WithDecryption=True
    )
    return response['Parameter']['Value']

# Load secrets from AWS at cold start
GIT_API_KEY = get_parameter("/prreview/GIT_API_KEY")
if GIT_API_KEY is None:
    raise ValueError("GIT_API_KEY was not found in the parameter store.")

headers = {
    "Accept": "application/vnd.github.v3+json",
    # Optional: Add token for higher rate limits
    # "Authorization": "Bearer YOUR_TOKEN"
}

def get_pr_details():
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        pr_data = response.json()
        print("PR Title:", pr_data["title"])
        print("Source Branch:", pr_data["head"]["ref"])
        print("Target Branch:", pr_data["base"]["ref"])
        print("Diff URL:", pr_data["diff_url"])
    else:
        print(f"Error: {response.status_code}, {response.json().get('message')}")

def get_pr_diff(repo,pr_number):
    # Headers for diff request
    diff_headers = {
        "Accept": "application/vnd.github.v3.diff",
    }
    token = GIT_API_KEY
    # print(f"Using GitHub API Key: {token}")
    if token:
        headers["Authorization"] = f"token {token}"

    # Construct the diff URL
    url = f"https://github.com/{repo}/pull/{pr_number}.diff"
    # Get the diff for this PR
    # print(f"Fetching diff for PR #{pr_number} in {repo}...")
    response = requests.get(url, headers=diff_headers)
    if response.status_code == 200:
        diff = response.text
        #print(f'Diff: {diff}')
        return diff
    else:
        print(f"Error: {response.status_code}")

def get_supported_diffs(repo, pr_number):
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/files"
    headers = {
            "Authorization": f"token {GIT_API_KEY}",
            "Accept": "application/vnd.github.v3+json"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    all_files = response.json()
    #print(f"File: {all_files[0]}")

        
    # Check if the response contains a list of files

    # Keep only files with a supported extension
    supported_diffs = [
        file for file in all_files
        if os.path.splitext(file['filename'])[1] in SUPPORTED_EXTENSIONS and 'patch' in file
    ]
    if len(all_files) != len(supported_diffs):   
        print(f"Found {len(all_files) - len(supported_diffs)} out of {len(all_files)} filetypes in diffs which are not supported for PR #{pr_number} in {repo}.")

    return supported_diffs

def get_pr_files(repo, pr_number):
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/files"
    # print(f"Using GitHub API Key: {token}")
    headers = {
        "Authorization": f"Bearer {GIT_API_KEY}",
        "Accept": "application/vnd.github.v3+json",
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()  # Raise an error for bad responses

    files = response.json()
    for file in files:
        filename = file.get("filename")
        status = file.get("status")  # e.g. 'added', 'modified', 'removed'
        print(f"{status.upper()}: {filename}")
    
    return files


def get_pull_requests(state='open'):
    """
    Fetch pull requests from a GitHub repository.
    
    Args:
        owner (str): Repository owner (e.g., 'octocat')
        repo (str): Repository name (e.g., 'hello-world')
        token (str, optional): GitHub Personal Access Token for authentication
        state (str): State of PRs to fetch ('open', 'closed', or 'all')
    
    Returns:
        list: List of pull requests
    """
    params = {
        "state": state,
        "per_page": 5  # Maximum number of PRs per page
    }
    
    pull_requests = []
    page = 1
    print(f"Fetching {state} pull requests from {pulls_url}...")
    #while True:
    params["page"] = page
    response = requests.get(pulls_url, headers=headers, params=params)
    
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.json().get('message', 'Unknown error')}")
        return
    
    prs = response.json()
    # if not prs:  # No more PRs to fetch
    #     break
        
    pull_requests.extend(prs)
    #page += 1
    
    return pull_requests

def print_pull_requests(prs):
    """
    Print basic information about pull requests.
    
    Args:
        prs (list): List of pull requests
    """
    for pr in prs:
        print(f"State: {pr['state'].capitalize()}")
        print(f"{pr['title']}")
        user_name = pr['user']['login'] if 'user' in pr else 'Unknown User'
        created_at = pr['created_at']
        if created_at:
            local_timezone = tz.tzlocal()
            date_object = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ")
            local_time = date_object.astimezone(local_timezone) 
                    
            created_at = local_time.strftime("%Y-%m-%d at %H:%M:%S")
        else:
            created_at = "Unknown Date"
        print(f"PR #{pr['number']} opened by {user_name} on {created_at}")

        print(f"URL: {pr['html_url']}")
        print("-" * 50)

def post_review(repo, pr_number, decision, review):
    headers = {
        "Accept": "application/vnd.github.v3.diff",
        "X-GitHub-Api-Version" : "2022-11-28"
    }
    if GIT_API_KEY:
        headers["Authorization"] = f"token {GIT_API_KEY}"
    
    payload = {
        "body": f"{review}",
        "event": f"{decision}",
        "comments": [
            {
                "path": "path/to/file.py",
                "position": 1,
                "body": "Please change this line to improve readability."
            }
        ]
    }    
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/reviews"
    response = requests.post(url, headers=headers)
    if response.status_code == 200:
        review_data = response.json()
        print("Review submitted successfully.")
        print(f"Review ID: {review_data['id']}")
        print(f"State: {review_data['state']}")
        print(f"Submitted by: {review_data['user']['login']}")
        print(f"HTML URL: {review_data['html_url']}")
    else:
        print(f"Failed to submit review: {response.status_code} - {response.text}")


def request_review(repo, pr_number, reviewer):
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/requested_reviewers"
    headers = {
        "Authorization": f"token {GIT_API_KEY}",
        "Accept": "application/vnd.github+json"
    }
    payload = {
        "reviewers": [reviewer]
        # Optional: "team_reviewers": ["team-slug"]
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 201:
        print("Reviewers requested successfully.")
    else:
        print(f"Failed to request reviewers: {response.status_code} - {response.text}")    


if __name__ == "__main__":
    # repo = "ississippi/pull-request-test-repo"
    repo = "ississippi/pull-request-automated-review"
    pr_number = 13    
    # get_pr_details()
    # get_pr_files()
    # get_pr_diff("ississippi/pull-request-test-repo", 16)
    # Fetch pull requests
    # prs = get_pull_requests()
    # # Print results
    # print(f"Found {len(prs)} pull requests:")
    # print_pull_requests(prs)  
    # git_pr_list()  : needs work
    # get_pr_files(owner=owner,repo=repo,pr_number=pr_number)
    # request_review(repo, 10, "ississippi")
    # decision = "REQUEST_CHANGES"
    # review = "This is close to perfect! Please address the suggested inline change."
    # post_review(repo, 10, decision, review)
    get_supported_diffs(repo, pr_number)
