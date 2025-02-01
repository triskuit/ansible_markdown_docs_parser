## Description
Python script for parsing and converting markdown files into Google Docs files.
Includes
- gDocs authentication
- support for heading style, lists, and footers
- support for running both locally and in google colab

## Setup
To run locally, clone this repo, install dependencies from `reqruirements.txt`, and setup authentication (instructions provided below)
To run on Google Colab, open a new notebook in Colab and select Github, enter https://github.com/triskuit/ansible_markdown_docs_parser and select the `notebook.ipynb`. Follow the authentication instructions to setup Google Docs API access.

In both cases your markdown file should be uploaded to your working directory and named `note.md`

### Authentication
Authenticating with Google Docs requires setting up a project within Google Cloud Console and then creating and downloading the appropriate credentials.
1. console.cloud.google.com
2. Create or select a project
3. Enable the Google Docs API (search Google Docs in the search bar)
4. Go to APIs & Services > Credentials
5. Select "Create Credentials"
- To create credentials to use in a local application with OAuth support select OAuth clinet Id and follow the setup flow
- To create credentials to run in a colab environment select Service Account and follow the setup flow
6. Download the newly created credentials by either selecting the download action for the OAth Client ID in the credentials pane OR by selecting the service account > Keys > Add Key
7. Rename the credential file to `credentials.json` and move it into the root of your working directory

## Dependencies
Locally install dependencies with `pip install -r requirements.txt`
On Colab run the `!pip install google-....` line

## Colab
Example [here](https://colab.research.google.com/drive/1Ld83Um6v_ck2vu0iNM9gr6Qdhy4VDOLA?usp=sharing)
