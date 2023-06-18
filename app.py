import openai
import requests
import nbformat
import chardet
import re
import streamlit as st
import os
from config import api_key



# Set up your OpenAI API credentials
openai.api_key = api_key

def get_user_repositories(github_url):
    # Extract the username from the GitHub URL
    global username 
    username = github_url.split("/")[-1]

    # Make the API request to retrieve the user's repositories
    url = f"https://api.github.com/users/{username}/repos"
    headers = {"Accept": "application/vnd.github.v3+json"}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        # Parse the JSON response and extract the repository names and URLs
        repositories = []
        data = response.json()
        for repo in data:
            repo_name = repo["name"]
            repo_url = repo["html_url"]
            repositories.append({"name": repo_name, "url": repo_url})

        return repositories
    else:
        # Handle API request errors
        print("Error: Failed to fetch user repositories.")
        return []

def preprocess_code(repository):
    processed_files = set()
    contents = preprocess_files(repository)
    preprocessed_contents = []
    for file in contents:
        file_type = file["type"]
        content = file["content"]
        if file_type == "jupyter_notebook":
            preprocessed_contents.append(preprocess_jupyter_notebook(content))
        elif file_type == "package_file":
            preprocessed_contents.append(preprocess_package_file(content))
        elif file_type == "regular_file":
            preprocessed_contents.append(preprocess_regular_file(content))

    return preprocessed_contents

def preprocess_files(repository):
    files = fetch_repository_files(repository)
    contents = []
    for file in files:
        file_path = file["name"]
        content = fetch_file_content(file["download_url"])
        contents.append({"name": file_path, "type": file["type"], "content": content})

    return contents

def fetch_repository_files(repository):
    url = f"https://api.github.com/repos/{username}/{repository['name']}/contents"
    headers = {"Accept": "application/vnd.github.v3+json"}
    response = requests.get(url, headers=headers, timeout=10)

    if response.status_code == 200:
        files = []
        data = response.json()
        fetch_files_recursive(data, files)

        return files
    else:
        print(f"Error: Failed to fetch files in repository {repository['name']}.")
        return []

def fetch_files_recursive(data, files):
    for item in data:
        if item["type"] == "file":
            file_name = item["name"]
            file_extension = file_name.split(".")[-1].lower()
            if file_extension not in ["jpg", "jpeg", "png", "gif", "ico", "h5", "pkl", "gitignore", "json", "node"]:
                file_type = determine_file_type(file_name)
                files.append({"name": file_name, "type": file_type, "download_url": item["download_url"]})
        elif item["type"] == "dir":
            url = item["url"]
            headers = {"Accept": "application/vnd.github.v3+json"}
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                subdir_data = response.json()
                fetch_files_recursive(subdir_data, files)
            else:
                print(f"Error: Failed to fetch files in directory {item['name']}.")

def determine_file_type(file_name):
    if file_name.endswith(".ipynb"):
        return "jupyter_notebook"
    elif file_name.endswith(".py"):
        return "package_file"
    elif file_name.endswith(".h5") or file_name.endswith(".pkl"):
        return "binary_file"
    else:
        return "regular_file"

def fetch_file_content(download_url):
    response = requests.get(download_url)

    if response.status_code == 200:
        return response.content
    else:
        print(f"Error: Failed to fetch file content from {download_url}.")
        return None

def preprocess_jupyter_notebook(content):
    notebook = nbformat.reads(content, nbformat.NO_CONVERT)
    preprocessed_cells = []
    for cell in notebook.cells:
        if cell.cell_type == "code":
            preprocessed_cells.append(preprocess_code_cell(cell))

    return preprocessed_cells

def preprocess_package_file(content):
    # Implement your preprocessing logic for package files
    # You can limit the token count or chunk the file as necessary
    # Example: Limit the token count to 1000
    if len(content.split()) > 500:
        content = " ".join(content.split()[:500])

    return content

def preprocess_regular_file(content):
    result = chardet.detect(content)
    encoding = result["encoding"]

    if encoding is None:
        encoding = "utf-8"

    try:
        decoded_content = content.decode(encoding, errors="ignore")
        if len(decoded_content.split()) > 200:
            decoded_content = " ".join(decoded_content.split()[:200])

        return decoded_content
    except UnicodeDecodeError:
        print("Error: Failed to decode file content.")

def preprocess_code_cell(cell):
    # Implement your preprocessing logic for code cells within Jupyter notebooks
    # You can limit the token count or handle large code cells as necessary
    # Example: Limit the token count to 200
    if len(cell["source"].split()) > 100:
        cell["source"] = " ".join(cell["source"].split()[:100])

    return cell["source"]

def generate_prompt(repository, code):
    prompt = f"""
    Generate a code complexity score for the following code snippet:
    --------------------------------------------------
    Code:
    {code}
    --------------------------------------------------

    """
    return prompt

# Use GPT-3 to analyze the code
def analyze_code(prompts):
    response = openai.Completion.create(
        engine="ada",
        prompt=prompts,
        max_tokens=100,
        temperature=0.7,
        n=len(prompts),
        stop=None
    )
    complexity_scores = []
    for choice in response.choices:
        score = extract_complexity_score(choice.text)
        if score is not None:
            complexity_scores.append(score)
        else:
            complexity_scores.append(0)
    return complexity_scores

def extract_complexity_score(text):
    # Extract the complexity score using a regular expression
    pattern = r"Complexity Score: (\d+)"
    match = re.search(pattern, text)
    if match:
        complexity_score = int(match.group(1))
        return complexity_score
    else:
        return None

# def identify_most_complex_repository(repositories):
#     complexity_scores = {}

#     for repository in repositories:
#         preprocessed_contents = preprocess_code(repository)
#         if preprocessed_contents:
#             prompts = []
#             for content in preprocessed_contents:
#                 prompt = generate_prompt(repository, content)
#                 prompts.append(prompt)

#             scores = analyze_code(prompts)
#             avg_score = sum(scores) / len(scores)
#             complexity_scores[repository["name"]] = avg_score

#     most_complex_repository = max(complexity_scores, key=complexity_scores.get)
#     return most_complex_repository

# def main():
#     st.title("Code Complexity Analyzer")

#     st.write("Enter your GitHub username to analyze your repositories:")
#     github_url = st.text_input("GitHub URL", "")

#     if st.button("Analyze"):
#         st.write("Analyzing repositories...")

#         repositories = get_user_repositories(github_url)

#         if repositories:
#             most_complex_repository = identify_most_complex_repository(repositories)

#             st.write("Analysis complete!")
#             st.write(f"The most complex repository is: {most_complex_repository}")
#         else:
#             st.write("No repositories found.")

# if __name__ == "__main__":
#     main()

def identify_most_complex_repository(repositories):
    complexity_scores = {}

    for repository in repositories:
        preprocessed_contents = preprocess_code(repository)
        if preprocessed_contents:
            prompts = []
            for content in preprocessed_contents:
                prompt = generate_prompt(repository, content)
                prompts.append(prompt)

            scores = analyze_code(prompts)
            complexity_score = sum(scores) / len(scores)
            complexity_scores[repository["name"]] = complexity_score

    if complexity_scores:
        most_complex_repository = max(complexity_scores, key=complexity_scores.get)
        justification = generate_justification(most_complex_repository)
        most_complex_repo_url = None
        for repo in repositories:
            if repo["name"] == most_complex_repository:
                most_complex_repo_url = repo["url"]
                break
        return most_complex_repository, complexity_scores[most_complex_repository], justification, most_complex_repo_url
    else:
        return None, 0, "", None


def generate_justification(repository):
    prompt = f"Justify why the repository '{repository}' is considered the most complex:"

    response = openai.Completion.create(
        engine="babbage",
        prompt=prompt,
        max_tokens=200,
        temperature=0.7,
        n=1,
        stop=None
    )

    if response.choices:
        justification = response.choices[0].text.strip()
        return justification
    else:
        return ""

# Streamlit app
def main():
    st.set_page_config(page_title="Code Complexity Analyzer")
    st.title("Code Complexity Analyzer")
    #title on the tab
    

    github_url = st.text_input("Enter GitHub URL:")
    if st.button("Analyze"):
        repositories = get_user_repositories(github_url)
        if repositories:
            most_complex_repository, complexity_score, justification, most_complex_repo_url = identify_most_complex_repository(repositories)
            if most_complex_repository:
                st.success(f"The most complex repository is {most_complex_repository}.")
                st.markdown(f"**Repository URL**: {most_complex_repo_url}")
                st.markdown(f"**Justification**: {justification}")
            else:
                st.warning("No code files found in the user's repositories.")
        else:
            st.error("No repositories found for the given GitHub URL.")

if __name__ == "__main__":
    main()
