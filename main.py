from google.auth.transport.requests import Request
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import os.path
import pickle

from enum import Enum
import re

SCOPES = ["https://www.googleapis.com/auth/documents"]

try:
    from google.colab import auth

    IN_COLAB = True
except:
    IN_COLAB = False


class Mode(Enum):
    """Enum representing different parsing modes for markdown processing.

    Modes:
        NONE: Default state
        LIST: Currently parsing a list
        FOOTER: Currently parsing footer content
    """

    NONE = 1
    LIST = 2
    FOOTER = 3

    def __str__(self):
        return self.name


class DocumentService:
    """Service class for interacting with the Google Docs API.

    Handles document operations including creation, updates, and footer management.
    """

    def __init__(self):
        self.credentials = None
        self.service = None

        self._initialize_service()
        pass

    def get_document(self, doc_id):
        """Retrieve a Google Doc by its ID.

        Args:
            doc_id (str): The Google Document ID

        Returns:
            dict: Document data if successful, None if failed
        """
        try:
            res = self.service.documents().get(documentId=doc_id).execute()
            return res
        except HttpError as error:
            if error.resp.status == 404:
                print(f"Document {doc_id} not found")
            else:
                print(f"API error: {error}")
            return None
        except Exception as error:
            print(f"An unexpected error occurred: {error}")
            return None
            print(f"Failed to update footer: {error}")
            return None

    def create_document(self, title="New Document"):
        """Create a new Google Doc.

        Args:
            title (str): Title for the new document

        Returns:
            dict: New document data if successful, None if failed
        """
        try:
            document = self.service.documents().create(body={"title": title}).execute()

            print(f"Created document with title: {title}")
            print(f"Document ID: {document.get('documentId')}")

            return document
        except HttpError as error:
            print(f"API error: {error}")
            return None
        except Exception as error:
            print(f"An unexpected error occurred: {error}")
            return None

    def update_document(self, doc_id, data):
        """Update a Google Doc with batch requests.

        Args:
            doc_id (str): The Google Document ID
            data (list): List of update requests

        Returns:
            dict: Update response if successful, None if failed
        """
        try:
            res = (
                self.service.documents()
                .batchUpdate(documentId=doc_id, body={"requests": data})
                .execute()
            )
            print(res)
            return res

        except HttpError as error:
            if error.resp.status == 404:
                print(f"Document {doc_id} not found")
            else:
                print(f"API error: {error}")
            return None
        except Exception as error:
            print(f"An unexpected error occurred: {error}")
            return None

    def update_footer(self, doc_id, footer_text):
        """Create or update the footer of a Google Doc.

        Args:
            doc_id (str): The Google Document ID
            footer_text (str): Text content for the footer

        Returns:
            dict: Update response if successful, None if failed
        """
        try:
            document = self.get_document(doc_id)
            if not document.get("footers"):
                req = [
                    {
                        "createFooter": {
                            "type": "DEFAULT",
                        }
                    }
                ]
                self.service.documents().batchUpdate(
                    documentId=doc_id, body={"requests": req}
                ).execute()
                document = self.get_document(doc_id)

            footer_id = list(document["footers"].keys())[0]

            requests = [
                {
                    "insertText": {
                        "location": {"segmentId": footer_id},
                        "text": footer_text,
                    }
                }
            ]

            res = (
                self.service.documents()
                .batchUpdate(documentId=doc_id, body={"requests": requests})
                .execute()
            )
            print(res)
        except HttpError as error:
            if error.resp.status == 404:
                print(f"Document {doc_id} not found")
            else:
                print(f"API error: {error}")
            return None
        except Exception as error:
            print(f"An unexpected error occurred: {error}")
            return None

    def _get_credentials(self):
        """Get Google docs api credentials.

        Stores retrieved credentials for future runs
        """
        credentials = None
        credentials_file = "credentials.json"
        if IN_COLAB:
            # Check if credentials file exists, if not, prompt for upload
            # File name must match credentials_file
            if not os.path.exists(credentials_file):
                print("Credentials file not found. Please upload it.")
                from google.colab import files

                files.upload()

            # Set credentials
            credentials = service_account.Credentials.from_service_account_file(
                credentials_file, scopes=SCOPES
            )
        else:
            import pickle
            from google_auth_oauthlib.flow import InstalledAppFlow

            # Check for stored credentials
            if os.path.exists("token.pickle"):
                with open("token.pickle", "rb") as token:
                    credentials = pickle.load(token)

            # If there are no valid credentials available, prompt user to log in
            if not credentials or not credentials.valid:
                if credentials and credentials.expired and credentials.refresh_token:
                    credentials.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        credentials_file, SCOPES
                    )
                    credentials = flow.run_local_server(port=0)

                # Store credentials for future use
                with open("token.pickle", "wb") as token:
                    pickle.dump(credentials, token)

        self.credentials = credentials

    def _initialize_service(self):
        try:
            self._get_credentials()
            docs_service = build("docs", "v1", credentials=self.credentials)
            self.service = docs_service
        except Exception as error:
            print(f"An unexpected error occurred: {error}")
            return None


class MarkdownParser:
    """Parser for converting markdown text to Google Docs request API format.

    Handles parsing of lists, headings, tags, and footers, generating
    appropriate Google Docs API requests.
    """

    REGEX = {
        "list": r"^(\s*)[-*] (\[ \])*(.*)$",
        "heading": r"^(#+)\s(.*)$",
        "tag": r"(\@\w*):",
        "footer": r"^-+$",
    }

    def __init__(self):
        self.index = 1
        self.mode = Mode.NONE
        self.list_start = 0
        self.indents = 0
        self.list_type = ""
        self.footer_text = ""
        self.requests = []

    def parse_file(self, filepath):
        """Parse a markdown file and generate Google Docs API requests.

        Args:
            filepath (str): Path to the markdown file

        Returns:
            tuple: (list of requests, footer content)
        """
        with open(filepath) as file:
            for line in file:
                if line.strip():
                    if self.mode == Mode.FOOTER:
                        self.footer_text += line
                    else:
                        self._parse_line(line)
        return self.requests, self.footer_text

    def _parse_line(self, line):
        """Process a single line of markdown text.
        Parsed request json are stored in self.requests

        Args:
            line (str): Line of text to parse
        """
        if self._check_footer(line):
            return

        line = self._parse_list_item(line)
        line = self._parse_heading(line)

        self._parse_tag(line)
        self.index += len(line.replace("\\", ""))

    def _parse_list_item(self, line):
        """Parse a markdown list item.

        Args:
            line (str): Line of text to parse

        Returns:
            str: Final parse text
        """
        match = re.search(self.REGEX["list"], line)
        if not match:
            if self.mode == Mode.LIST:
                self._end_list()
            return line

        indent_spaces, is_checkbox, text = match.groups()

        if not self.mode == Mode.LIST:
            self.list_start = self.index
            self.mode = Mode.LIST
            self.list_type = "CHECKBOX" if is_checkbox else "DISC_CIRCLE_SQUARE"

        indent_level = len(indent_spaces) // 2
        text = ("\t" * indent_level) + text + "\n"
        self.indents += indent_level

        self.requests.append(
            {"insertText": {"location": {"index": self.index}, "text": text}},
        )
        return text

    def _parse_heading(self, line):
        """Parse a markdown heading.

        Args:
            line (str): Line of text to parse

        Returns:
            str: Processed heading text
        """
        match = re.search(self.REGEX["heading"], line)
        if not match:
            return line

        level, text = match.groups()
        level = len(level)

        self.requests.extend(
            [
                {
                    "insertText": {
                        "location": {"index": self.index},
                        "text": text + "\n",
                    }
                },
                {
                    "updateParagraphStyle": {
                        "range": {
                            "startIndex": self.index,
                            "endIndex": self.index + len(text),
                        },
                        "paragraphStyle": {
                            "namedStyleType": f"HEADING_{level}",
                        },
                        "fields": "namedStyleType",
                    }
                },
            ]
        )

        self.index += 1

        return text

    def _parse_tag(self, line):
        """Parse an @tag in the text.

        Args:
            line (str): Line of text to parse

        Returns:
            bool: True if tag was found and processed
        """
        match = re.search(self.REGEX["tag"], line)
        if not match:
            return False

        self.requests.append(
            {
                "updateTextStyle": {
                    "range": {
                        "startIndex": self.index + match.start(),
                        "endIndex": self.index + match.end() - 1,
                    },
                    "textStyle": {"bold": True},
                    "fields": "bold",
                }
            }
        )

        return True

    def _check_footer(self, line):
        """Check if line indicates start of footer section.

        Args:
            line (str): Line of text to check

        Returns:
            bool: True if footer delimiter found
        """
        match = re.search(self.REGEX["footer"], line)
        if not match:
            return False

        if self.mode == Mode.LIST:
            self._end_list()

        self.mode = Mode.FOOTER
        return True

    def _end_list(self):
        """Finalize the current list processing and reset list state."""
        self.requests.append(
            {
                "createParagraphBullets": {
                    "range": {
                        "startIndex": self.list_start,
                        "endIndex": self.index,
                    },
                    "bulletPreset": f"BULLET_{self.list_type}",
                }
            }
        )

        self.index -= self.indents
        self.mode = Mode.NONE
        self.list_start = 0
        self.indents = 0
        pass


if __name__ == "__main__":
    service = DocumentService()
    parser = MarkdownParser()

    doc_id = ""
    if not doc_id:
        doc_id = service.create_document("New Note").get("documentId")

    requests, footer_content = parser.parse_file("note.md")
    service.update_document(doc_id, requests)

    if footer_content:
        service.update_footer(doc_id, footer_content)
