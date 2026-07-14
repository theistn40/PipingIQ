"""
===========================================================
PipingIQ Search Engine
===========================================================
"""

import fitz


class SearchEngine:

    def __init__(self, library):
        self.library = library

    # -----------------------------------------------------

    def search(self, phrase):

        results = []

        phrase = phrase.lower()

        for doc in self.library.documents:

            pdf = fitz.open(doc["path"])

            for page_number in range(len(pdf)):

                page = pdf[page_number]

                text = page.get_text()

                lower = text.lower()

                score = lower.count(phrase)

                if score == 0:
                    continue

                # Bonus if phrase appears near top of page
                first = lower.find(phrase)

                if first < 300:
                    score += 10

                # Bonus if page contains chapter heading
                if "chapter" in lower:
                    score += 3

                # Bonus if page contains equation
                if "equation" in lower:
                    score += 2

                results.append({
                    "book": doc["title"],
                    "page": page_number + 1,
                    "score": score,
                    "matches": lower.count(phrase),
                    "text": text
                })

            pdf.close()

        results.sort(key=lambda r: r["score"], reverse=True)

        return results