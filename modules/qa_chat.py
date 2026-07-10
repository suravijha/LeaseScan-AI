"""
Retrieval-augmented chat over the lease.

Turns the analyzer from a one-shot "score + flags" tool into an
interactive assistant the user can actually ask questions of, with
answers grounded in (and citing) the retrieved lease excerpts rather
than the model's general knowledge.
"""

from modules.vectorstore import LeaseVectorStore

CHAT_PROMPT_TEMPLATE = """You are a helpful tenant-advocate assistant answering a question about a specific lease.
Answer ONLY using the excerpts below. If the excerpts don't contain the answer, say so plainly -
do not guess or use outside knowledge about "typical" leases as if it were this lease.

Cite the page number(s) you used, like "(Page 4)".

Lease excerpts:
{excerpts}

Question: {question}

Answer in 2-4 sentences, plain English, then a short "Source: Page X" line.
"""


def answer_question(model, store: LeaseVectorStore, question: str, k: int = 5) -> str:
    retrieved = store.search(question, k=k)

    if not retrieved:
        return "I don't have enough information from this document to answer that."

    excerpts = "\n\n".join(f"[Page {r.chunk.page_number}]\n{r.chunk.text}" for r in retrieved)
    prompt = CHAT_PROMPT_TEMPLATE.format(excerpts=excerpts, question=question)

    return model.generate_content(prompt).text.strip()
