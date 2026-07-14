"""
===========================================================
PipingIQ Engineering Knowledge Library
knowledge_library.py
===========================================================
"""

from pathlib import Path


class KnowledgeLibrary:

    def __init__(self, library_path):

        self.library_path = Path(library_path)

        self.documents = []

    # -----------------------------------------------------

    def scan_library(self):

        self.documents = []

        for pdf in sorted(self.library_path.glob("*.pdf")):

            self.documents.append({

                "title": pdf.stem,

                "filename": pdf.name,

                "path": str(pdf),

                "size_mb": round(pdf.stat().st_size / 1024 / 1024, 2)

            })

        return self.documents

    # -----------------------------------------------------

    def print_library(self):

        print()

        print("=" * 60)

        print("PIPINGIQ ENGINEERING KNOWLEDGE LIBRARY")

        print("=" * 60)

        print()

        for number, doc in enumerate(self.documents, start=1):

            print(f"{number}. {doc['title']}")

            print(f"   File : {doc['filename']}")

            print(f"   Size : {doc['size_mb']} MB")

            print()