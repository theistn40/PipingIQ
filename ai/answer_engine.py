"""
===========================================================
PipingIQ Answer Engine
===========================================================
"""

class AnswerEngine:

    def __init__(self):
        pass

    # -----------------------------------------------------

    def generate_answer(self, question, search_results):

        if not search_results:

            return "No engineering references were found."

        best = search_results[0]

        text = best["text"]

        text = text.replace("\n", " ")

        while "  " in text:
            text = text.replace("  ", " ")

        if len(text) > 800:
            text = text[:800] + "..."

        answer = []

        answer.append("=" * 70)
        answer.append("PIPINGIQ ENGINEERING ANSWER")
        answer.append("=" * 70)
        answer.append("")
        answer.append(f"Question:")
        answer.append(question)
        answer.append("")
        answer.append("Best Source")
        answer.append(f"Book : {best['book']}")
        answer.append(f"Page : {best['page']}")
        answer.append("")
        answer.append("Reference Text")
        answer.append(text)
        answer.append("")
        answer.append("=" * 70)

        return "\n".join(answer)