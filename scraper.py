import time
import xml.etree.ElementTree as ET

from datetime import datetime, timezone
from email.utils import format_datetime
from urllib.parse import quote

import requests


# ============================================================
# CONFIGURATION
# ============================================================

API_URL = (
    "https://ec.europa.eu/transparency/"
    "comitology-register/core/api/front/documents/search"
)

OUTPUT_FILE = "comitology.xml"

REGISTER_URL = (
    "https://ec.europa.eu/transparency/"
    "comitology-register/screen/documents?lang=en"
)

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Language": "en",
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent": (
        "Mozilla/5.0 "
        "(compatible; Comitology-RSS/1.0)"
    ),
}

MAX_ATTEMPTS = 3


# ============================================================
# GET DOCUMENTS FROM COMMISSION API
# ============================================================

def get_documents(page=0, size=100):

    params = {
        "page": page,
        "size": size,
        "sort": "updateDate,desc",
    }

    print()
    print("Requesting Comitology API...")
    print("Method: POST")
    print(f"Page: {page}")
    print(f"Size: {size}")
    print("Sort: updateDate,desc")

    for attempt in range(1, MAX_ATTEMPTS + 1):

        print()
        print(
            f"Request attempt "
            f"{attempt}/{MAX_ATTEMPTS}"
        )

        try:

            response = requests.post(
                API_URL,
                params=params,
                headers=HEADERS,
                json={
                    "reset": False
                },
                timeout=60,
            )

        except requests.RequestException as error:

            print()
            print(
                "ERROR connecting to "
                "Commission API:"
            )
            print(error)

            if attempt == MAX_ATTEMPTS:
                raise

            wait_seconds = 10 * attempt

            print(
                f"Retrying in "
                f"{wait_seconds} seconds..."
            )

            time.sleep(
                wait_seconds
            )

            continue

        print(
            f"API status: "
            f"{response.status_code}"
        )

        content_type = response.headers.get(
            "Content-Type",
            ""
        ).lower()

        # ----------------------------------------------------
        # Successful JSON response
        # ----------------------------------------------------

        if (
            response.status_code == 200
            and "application/json" in content_type
        ):

            try:

                return response.json()

            except ValueError as error:

                print()
                print(
                    "ERROR: Commission API "
                    "returned invalid JSON."
                )

                print(
                    response.text[:5000]
                )

                if attempt == MAX_ATTEMPTS:
                    raise RuntimeError(
                        "Commission API returned "
                        "invalid JSON."
                    ) from error

        # ----------------------------------------------------
        # Server temporarily unavailable
        # ----------------------------------------------------

        if (
            response.status_code == 200
            and "text/html" in content_type
        ):

            print()
            print(
                "Commission API returned "
                "an HTML page instead of JSON."
            )

            print(
                "The Commission service may "
                "be temporarily unavailable."
            )

            if attempt == MAX_ATTEMPTS:

                print()
                print(
                    "Response from Commission:"
                )

                print(
                    response.text[:5000]
                )

                raise RuntimeError(
                    "Commission API is temporarily "
                    "unavailable or returned an "
                    "HTML error page."
                )

        # ----------------------------------------------------
        # HTTP error
        # ----------------------------------------------------

        else:

            print()
            print(
                "Commission API returned "
                "an unexpected response."
            )

            print(
                f"Content-Type: "
                f"{content_type}"
            )

            print()
            print(
                "Response:"
            )

            print(
                response.text[:5000]
            )

            if attempt == MAX_ATTEMPTS:

                response.raise_for_status()

                raise RuntimeError(
                    "Commission API returned "
                    "an unexpected response."
                )

        # ----------------------------------------------------
        # Retry
        # ----------------------------------------------------

        if attempt < MAX_ATTEMPTS:

            wait_seconds = 10 * attempt

            print()
            print(
                f"Retrying in "
                f"{wait_seconds} seconds..."
            )

            time.sleep(
                wait_seconds
            )

    raise RuntimeError(
        "Unable to retrieve documents "
        "from the Commission API."
    )


# ============================================================
# CREATE DOCUMENT URL
# ============================================================

def document_url(document):

    reference = str(
        document.get(
            "documentReference",
            ""
        )
    )

    version = str(
        document.get(
            "version",
            ""
        )
    )

    return (
        "https://ec.europa.eu/transparency/"
        "comitology-register/screen/documents/"
        f"{quote(reference)}/{quote(version)}"
    )


# ============================================================
# PARSE API DATE
# ============================================================

def parse_date(value):

    if not value:
        return None

    try:

        return datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00"
            )
        )

    except ValueError:

        return None


# ============================================================
# CREATE RSS DESCRIPTION
# ============================================================

def create_description(document):

    parts = []

    reference = document.get(
        "documentReference",
        ""
    )

    version = document.get(
        "version",
        ""
    )

    parts.append(
        f"Document reference: "
        f"{reference}/{version}"
    )

    # --------------------------------------------------------
    # Document type
    # --------------------------------------------------------

    document_type = document.get(
        "documentType"
    )

    if document_type:

        letter = document_type.get(
            "letter",
            ""
        )

        label = document_type.get(
            "label",
            ""
        )

        label = (
            label
            .replace(
                "label.",
                ""
            )
            .replace(
                "_",
                " "
            )
            .title()
        )

        if letter:

            parts.append(
                f"Document type: "
                f"{letter} — {label}"
            )

        elif label:

            parts.append(
                f"Document type: {label}"
            )

    # --------------------------------------------------------
    # Committee
    # --------------------------------------------------------

    committee_title = document.get(
        "committeeTitle"
    )

    if committee_title:

        parts.append(
            f"Committee: "
            f"{committee_title}"
        )

    committee_code = document.get(
        "committeeCode"
    )

    if committee_code:

        parts.append(
            f"Committee code: "
            f"{committee_code}"
        )

    # --------------------------------------------------------
    # Meeting
    # --------------------------------------------------------

    meeting_code = document.get(
        "meetingCode"
    )

    if meeting_code:

        parts.append(
            f"Meeting: "
            f"{meeting_code}"
        )

    meeting_start = document.get(
        "meetingStartDate"
    )

    if meeting_start:

        parts.append(
            f"Meeting start: "
            f"{meeting_start}"
        )

    meeting_end = document.get(
        "meetingEndDate"
    )

    if meeting_end:

        parts.append(
            f"Meeting end: "
            f"{meeting_end}"
        )

    # --------------------------------------------------------
    # Dates
    # --------------------------------------------------------

    creation_date = document.get(
        "creationDate"
    )

    if creation_date:

        parts.append(
            f"Created: "
            f"{creation_date}"
        )

    update_date = document.get(
        "updateDate"
    )

    if update_date:

        parts.append(
            f"Updated: "
            f"{update_date}"
        )

    return "\n".join(parts)


# ============================================================
# CREATE RSS
# ============================================================

def create_rss(documents):

    rss = ET.Element(
        "rss",
        {
            "version": "2.0"
        }
    )

    channel = ET.SubElement(
        rss,
        "channel"
    )

    # --------------------------------------------------------
    # Channel information
    # --------------------------------------------------------

    ET.SubElement(
        channel,
        "title"
    ).text = (
        "European Commission "
        "Comitology Register"
    )

    ET.SubElement(
        channel,
        "link"
    ).text = REGISTER_URL

    ET.SubElement(
        channel,
        "description"
    ).text = (
        "Latest documents from the "
        "European Commission Comitology Register"
    )

    ET.SubElement(
        channel,
        "language"
    ).text = "en"

    ET.SubElement(
        channel,
        "lastBuildDate"
    ).text = format_datetime(
        datetime.now(
            timezone.utc
        )
    )

    # --------------------------------------------------------
    # Documents
    # --------------------------------------------------------

    for document in documents:

        item = ET.SubElement(
            channel,
            "item"
        )

        reference = str(
            document.get(
                "documentReference",
                ""
            )
        )

        version = str(
            document.get(
                "version",
                ""
            )
        )

        title = document.get(
            "title",
            "Untitled document"
        )

        # ----------------------------------------------------
        # RSS title
        # ----------------------------------------------------

        rss_title = (
            f"{reference}/{version} — {title}"
        )

        ET.SubElement(
            item,
            "title"
        ).text = rss_title

        # ----------------------------------------------------
        # Document URL
        # ----------------------------------------------------

        url = document_url(
            document
        )

        ET.SubElement(
            item,
            "link"
        ).text = url

        # ----------------------------------------------------
        # GUID
        # ----------------------------------------------------

        ET.SubElement(
            item,
            "guid",
            {
                "isPermaLink": "true"
            }
        ).text = url

        # ----------------------------------------------------
        # Publication date
        # ----------------------------------------------------

        date = parse_date(
            document.get(
                "updateDate"
            )
        )

        if date:

            ET.SubElement(
                item,
                "pubDate"
            ).text = format_datetime(
                date
            )

        # ----------------------------------------------------
        # Description
        # ----------------------------------------------------

        ET.SubElement(
            item,
            "description"
        ).text = create_description(
            document
        )

        # ----------------------------------------------------
        # Category
        # ----------------------------------------------------

        document_type = document.get(
            "documentType"
        )

        if document_type:

            label = document_type.get(
                "label",
                ""
            )

            label = (
                label
                .replace(
                    "label.",
                    ""
                )
                .replace(
                    "_",
                    " "
                )
                .title()
            )

            if label:

                ET.SubElement(
                    item,
                    "category"
                ).text = label

    return ET.ElementTree(
        rss
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("COMITOLOGY RSS GENERATOR")
    print("=" * 60)

    documents = []

    # --------------------------------------------------------
    # Currently fetching one page for testing.
    #
    # Once confirmed working, increase the number of pages
    # or implement pagination as required.
    # --------------------------------------------------------

    for page in range(1):

        print()
        print(
            f"Fetching page {page}..."
        )

        data = get_documents(
            page=page,
            size=100
        )

        page_documents = data.get(
            "content",
            []
        )

        print(
            f"Found "
            f"{len(page_documents)} documents"
        )

        documents.extend(
            page_documents
        )

        # ----------------------------------------------------
        # Show what we received
        # ----------------------------------------------------

        for document in page_documents:

            reference = document.get(
                "documentReference",
                ""
            )

            version = document.get(
                "version",
                ""
            )

            title = document.get(
                "title",
                ""
            )

            print()
            print(
                f"  {reference}/{version}"
            )

            print(
                f"  {title}"
            )

    # --------------------------------------------------------
    # Deduplicate
    # --------------------------------------------------------

    unique_documents = {}

    for document in documents:

        key = (
            document.get(
                "documentReference"
            ),
            document.get(
                "version"
            )
        )

        unique_documents[key] = document

    documents = list(
        unique_documents.values()
    )

    print()
    print(
        f"Total unique documents: "
        f"{len(documents)}"
    )

    # --------------------------------------------------------
    # Make sure we actually received data
    # --------------------------------------------------------

    if not documents:

        raise RuntimeError(
            "The Commission API returned "
            "zero documents."
        )

    # --------------------------------------------------------
    # Generate RSS
    # --------------------------------------------------------

    rss = create_rss(
        documents
    )

    ET.indent(
        rss,
        space="  "
    )

    rss.write(
        OUTPUT_FILE,
        encoding="utf-8",
        xml_declaration=True
    )

    print()
    print(
        f"RSS successfully written to "
        f"{OUTPUT_FILE}"
    )

    print()
    print("=" * 60)
    print("SUCCESS")
    print("=" * 60)


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()
