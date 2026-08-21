fetimport html
import xml.etree.ElementTree as ET

from datetime import datetime, timezone
from email.utils import format_datetime
from urllib.parse import quote

import requests


API_URL = (
    "https://ec.europa.eu/transparency/"
    "comitology-register/core/api/front/documents/search"
)

OUTPUT_FILE = "comitology.xml"

REGISTER_URL = (
    "https://ec.europa.eu/transparency/"
    "comitology-register/screen/documents"
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


def get_documents(page=0, size=5):

    params = {
        "page": page,
        "size": size,
        "sort": "documentReference,asc",
    }

    response = requests.post(
        API_URL,
        params=params,
        headers=HEADERS,
        json={"reset": False},
        timeout=60,
    )

    print("API status:", response.status_code)

    if response.status_code != 200:
        print("API response:")
        print(response.text)

    response.raise_for_status()

    return response.json()


def document_url(document):

    reference = document["documentReference"]
    version = document["version"]

    return (
        "https://ec.europa.eu/transparency/"
        "comitology-register/screen/documents/"
        f"{quote(str(reference))}/{version}"
    )


def parse_date(value):

    if not value:
        return None

    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )


def create_description(document):

    parts = []

    parts.append(
        f"Document reference: "
        f"{document['documentReference']}/"
        f"{document['version']}"
    )

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

        # Convert API label to something readable.
        label = label.replace(
            "label.",
            ""
        ).replace(
            "_",
            " "
        )

        parts.append(
            f"Document type: "
            f"{letter} — {label}"
        )

    if document.get("committeeTitle"):

        parts.append(
            f"Committee: "
            f"{document['committeeTitle']}"
        )

    if document.get("committeeCode"):

        parts.append(
            f"Committee code: "
            f"{document['committeeCode']}"
        )

    if document.get("meetingCode"):

        parts.append(
            f"Meeting: "
            f"{document['meetingCode']}"
        )

    if document.get("meetingStartDate"):

        parts.append(
            f"Meeting start: "
            f"{document['meetingStartDate']}"
        )

    if document.get("meetingEndDate"):

        parts.append(
            f"Meeting end: "
            f"{document['meetingEndDate']}"
        )

    return "\n".join(parts)


def create_rss(documents):

    rss = ET.Element(
        "rss",
        {
            "version": "2.0",
        },
    )

    channel = ET.SubElement(
        rss,
        "channel",
    )

    ET.SubElement(
        channel,
        "title",
    ).text = (
        "European Commission Comitology Register"
    )

    ET.SubElement(
        channel,
        "link",
    ).text = REGISTER_URL

    ET.SubElement(
        channel,
        "description",
    ).text = (
        "Latest documents from the European "
        "Commission Comitology Register"
    )

    ET.SubElement(
        channel,
        "language",
    ).text = "en"

    ET.SubElement(
        channel,
        "lastBuildDate",
    ).text = format_datetime(
        datetime.now(timezone.utc)
    )

    for document in documents:

        item = ET.SubElement(
            channel,
            "item",
        )

        reference = (
            f"{document['documentReference']}/"
            f"{document['version']}"
        )

        title = document.get(
            "title",
            "Untitled document"
        )

        # Make the RSS title particularly useful.
        rss_title = (
            f"{reference} — {title}"
        )

        ET.SubElement(
            item,
            "title",
        ).text = rss_title

        url = document_url(
            document
        )

        ET.SubElement(
            item,
            "link",
        ).text = url

        # Reference + version makes a useful stable GUID.
        ET.SubElement(
            item,
            "guid",
            {
                "isPermaLink": "true"
            },
        ).text = url

        date = parse_date(
            document.get(
                "updateDate"
            )
        )

        if date:

            ET.SubElement(
                item,
                "pubDate",
            ).text = format_datetime(
                date
            )

        description = html.escape(
            create_description(
                document
            )
        )

        ET.SubElement(
            item,
            "description",
        ).text = description

        document_type = document.get(
            "documentType"
        )

        if document_type:

            label = document_type.get(
                "label",
                ""
            ).replace(
                "label.",
                ""
            ).replace(
                "_",
                " "
            )

            if label:

                ET.SubElement(
                    item,
                    "category",
                ).text = label

    return ET.ElementTree(
        rss
    )


def main():

    documents = []

    # Fetch several pages of the newest documents.
    #
    # 5 pages × 100 = up to 500 documents.
    #
    # This gives us plenty of room to catch new
    # documents even if the Action doesn't run for
    # a few hours.
    for page in range(1):

        print(
            f"Fetching page {page}..."
        )

        data = get_documents(
            page=page,
            size=5,
        )

        page_documents = data.get(
            "content",
            []
        )

        print(
            f"  Found "
            f"{len(page_documents)} documents"
        )

        documents.extend(
            page_documents
        )

        if data.get("last"):
            break

    # Deduplicate by document reference + version.
    unique = {}

    for document in documents:

        key = (
            document["documentReference"],
            document["version"],
        )

        unique[key] = document

    documents = list(
        unique.values()
    )

    print(
        f"Total documents: "
        f"{len(documents)}"
    )

    if not documents:

        raise RuntimeError(
            "The Comitology API returned "
            "no documents."
        )

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
        xml_declaration=True,
    )

    print(
        f"RSS written to "
        f"{OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()
