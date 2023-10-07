import openai
import requests
import nbformat
import chardet
import re
import streamlit as st
import os
from config import api_key, github_token
import json
from langchain import PromptTemplate


# Set up your OpenAI API credentials
openai.api_key = api_key
github_token = github_token

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
            preprocessed_contents.extend(preprocess_jupyter_notebook(content))
        elif file_type == "package_file":
            preprocessed_contents.extend(preprocess_package_file(content))
        elif file_type == "regular_file":
            preprocessed_contents.extend(preprocess_regular_file(content))

    #convert preprocessed_contents to a string
    preprocessed_contents = [str(content) for content in preprocessed_contents]

    # Combine preprocessed contents into a single string
    preprocessed_content = " ".join(preprocessed_contents)

    # Limit the token count to 2000
    if len(preprocessed_content.split()) > 2000:
        preprocessed_content = " ".join(preprocessed_content.split()[:2000])

    return preprocessed_content


def preprocess_files(repository):
    repository_url = repository["url"]
    files = fetch_repository_files(repository_url, github_token)
    contents = []
    for file in files:
        file_path = file["name"]
        content = fetch_file_content(file["download_url"])
        contents.append({"name": file_path, "type": file["type"], "content": content})

    return contents

def fetch_repository_files(repo_url, github_token):
    # Construct the API endpoint to fetch repository contents
    api_url = repo_url.replace("https://github.com/", "https://api.github.com/repos/") + "/contents"
    
    headers = {
        "Authorization": "token " + github_token,
        "Accept": "application/vnd.github.v3+json"
    }

    response = requests.get(api_url, headers=headers, timeout=10)
    if response.status_code == 200:
        try:
            data = response.json()
            files = []
            fetch_files_recursive(data, files)
            return files
        except json.JSONDecodeError as e:
            print(f"Error: Failed to parse API response as JSON - {e}")
            return []
    else:
        print(f"Error: Failed to fetch files in the repository.")
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

# def preprocess_jupyter_notebook(content):
#     notebook = nbformat.reads(content, nbformat.NO_CONVERT)
#     preprocessed_cells = []
#     for cell in notebook.cells:
#         if cell.cell_type == "code":
#             preprocessed_cells.append(preprocess_code_cell(cell))

#     # Flatten the preprocessed cells into a single string
#     preprocessed_content = " ".join(preprocessed_cells)

#     # Limit the token count to 500
#     if len(preprocessed_content.split()) > 500:
#         preprocessed_content = " ".join(preprocessed_content.split()[:500])

#     return preprocessed_content

def preprocess_jupyter_notebook(content):
    notebook = nbformat.reads(content, nbformat.NO_CONVERT)
    preprocessed_cells = []
    for cell in notebook.cells:
        if cell.cell_type == "code":
            preprocessed_cells.append(preprocess_code_cell(cell))

    return preprocessed_cells

def preprocess_package_file(content):
    # You can limit the token count or chunk the file as necessary
    # Example: Limit the token count to 1000
    if len(content.split()) > 500:
        content = " ".join(content.split()[:500])

    return [content]

def preprocess_regular_file(content):
    result = chardet.detect(content)
    encoding = result["encoding"]

    if encoding is None:
        encoding = "utf-8"

    try:
        decoded_content = content.decode(encoding, errors="ignore")
        if len(decoded_content.split()) > 200:
            decoded_content = " ".join(decoded_content.split()[:200])

        return [decoded_content]
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
    #the models max token count is 2048, so we need to limit the token count to 2000
    if len(code.split()) > 100:
        code = " ".join(code.split()[:100])
    
    prompt = f"""
    Generate a code complexity score for the following code snippet:
    --------------------------------------------------
    Code:
    {code}
    --------------------------------------------------

    """

    return prompt

# def generate_prompt(repository, code):
#     #the models max token count is 2048, so we need to limit the token count to 2000
#     if len(code.split()) > 100:
#         code = " ".join(code.split()[:100])
    
#     Prompt = PromptTemplate.from_template(
#         """Generate a code complexity score for the following code snippet:
#         --------------------------------------------------
#         Code:
#         {code}
#         --------------------------------------------------
#         """
#     )
#     prompt = Prompt.render(code=code)
#     return prompt

# Use GPT-3 to analyze the code
def analyze_code(prompts):
    complexity_scores = []
    for prompt in prompts:
        response = openai.Completion.create(
            engine="ada",
            prompt=prompt,
            max_tokens=100,
            temperature=0.7,
            n=1,
            stop=None
        )
        score = extract_complexity_score(response.choices[0].text)
        complexity_scores.append(score if score is not None else 0)
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
    #the models max token count is 2048, so we need to limit the token count to 2000
    if len(repository.split()) > 2000:
        repository = " ".join(repository.split()[:2000])
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

# def generate_justification(repository):
#     #the models max token count is 2048, so we need to limit the token count to 2000
#     if len(repository.split()) > 2000:
#         repository = " ".join(repository.split()[:2000])
#     Prompt = PromptTemplate.from_template(
#         """Justify why the repository '{repository}' is considered the most complex:
#         """
#     )
#     prompt = Prompt.render(repository=repository)

#     response = openai.Completion.create(
#         engine="babbage",
#         prompt=prompt,
#         max_tokens=200,
#         temperature=0.7,
#         n=1,
#         stop=None
#     )

#     if response.choices:
#         justification = response.choices[0].text.strip()
#         return justification
#     else:
#         return ""

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
