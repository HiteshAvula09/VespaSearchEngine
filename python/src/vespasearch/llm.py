import httpx

from .config import get_settings


SYSTEM_PROMPT = """You are VespaSearch, an enterprise search assistant.

Rules:
1. First use the retrieved context supplied to you.
2. If the retrieved context contains enough relevant information to answer
   the question, answer from that context.
3. When using retrieved context, support factual claims with citations
   such as [1], [2].
4. Cite only context items that actually support the claim.
5. If the retrieved context is insufficient or unrelated, you may answer
   using your general knowledge.
6. When using general knowledge, clearly begin that portion with:
   "General answer:"
7. Do not attach indexed-source citations to information that came from
   general knowledge.
8. Never claim that general knowledge came from the indexed enterprise
   sources.
9. If part of the answer is supported by indexed context and another part
   requires general knowledge, clearly separate those two portions.
10. 10. Keep the final answer short and simple, with a maximum of 3 sentences.
"""


MAX_CONTEXT_CHARS_PER_RESULT = 1800


def build_context(results: list[dict]) -> str:
    blocks = []

    for index, result in enumerate(results, 1):
        content = (result.get("content") or "").strip()

        if len(content) > MAX_CONTEXT_CHARS_PER_RESULT:
            content = (
                content[:MAX_CONTEXT_CHARS_PER_RESULT]
                + "\n[content truncated]"
            )

        source = result.get("source") or "unknown"
        source_type = result.get("source_type") or "unknown"
        title = result.get("title") or "Untitled"
        url = result.get("url") or ""

        blocks.append(
            f"[{index}]\n"
            f"Source: {source}\n"
            f"Type: {source_type}\n"
            f"Title: {title}\n"
            f"URL: {url}\n"
            f"Content:\n{content}\n"
        )

    return "\n---\n".join(blocks)


def grounded_answer(
    question: str,
    results: list[dict],
) -> str:
    settings = get_settings()

    if not settings.llm_enabled:
        return (
            "LLM generation is disabled. "
            "Retrieved evidence is returned below."
        )

    if settings.llm_provider.lower() != "groq":
        return (
            f"Unsupported LLM provider: "
            f"{settings.llm_provider}"
        )

    if not settings.groq_api_key:
        return (
            "Groq API key is not configured. "
            "Add GROQ_API_KEY to your .env file."
        )

    # If Vespa returns no results at all, Groq can still provide
    # a general-knowledge answer.
    if results:
        context = build_context(results)
    else:
        context = (
            "No relevant indexed enterprise context "
            "was retrieved for this question."
        )

    prompt = f"""QUESTION:
{question}

RETRIEVED CONTEXT:
{context}

INSTRUCTIONS:
First determine whether the retrieved context contains enough relevant
information to answer the question.

If the retrieved context is relevant:
- Answer primarily from the retrieved context.
- Use citations in the form [1], [2], etc.
- Cite only retrieved items that actually support the answer.
- Do not use citations for claims that are not supported by the retrieved
  context.

If the retrieved context is insufficient, unrelated, or no indexed
context was retrieved:
- Answer using your general knowledge.
- Begin the answer with "General answer:"
- Do not use [1], [2], or any indexed-source citations for general
  knowledge.
- Do not pretend the information came from the indexed sources.

If part of the answer is supported by indexed context and another part
requires general knowledge:
- Clearly separate the indexed portion from the general-knowledge portion.
- Use citations only for the indexed portion.
- Begin the general-knowledge portion with "General answer:"

Keep the answer concise and useful.
"""

    payload = {
        "model": settings.groq_model,
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "temperature": 0.1,
        "max_completion_tokens": 400,
        "reasoning_effort": "low",
        "include_reasoning": False,
    }

    headers = {
        "Authorization": f"Bearer {settings.groq_api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = httpx.post(
            (
                f"{settings.groq_url.rstrip('/')}"
                "/chat/completions"
            ),
            headers=headers,
            json=payload,
            timeout=60,
        )

        response.raise_for_status()

        data = response.json()

        choices = data.get("choices", [])

        if not choices:
            return (
                "The Groq LLM did not return "
                "a usable answer."
            )

        answer = (
            choices[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )

        if not answer:
            return (
                "The Groq LLM did not return "
                "a usable answer."
            )

        return answer

    except httpx.ConnectError:
        return (
            "The Groq API is unavailable. "
            "Check your internet connection and try again."
        )

    except httpx.TimeoutException:
        return (
            "The Groq API took too long to respond. "
            "Please try again."
        )

    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code

        if status_code == 401:
            return (
                "Groq authentication failed. "
                "Check your GROQ_API_KEY."
            )

        if status_code == 429:
            return (
                "Groq rate limit reached. "
                "Please wait a moment and try again."
            )

        try:
            error_data = exc.response.json()
            error_message = (
                error_data
                .get("error", {})
                .get("message", "")
            )
        except Exception:
            error_message = ""

        if error_message:
            return (
                f"Groq returned an error "
                f"({status_code}): {error_message}"
            )

        return (
            f"Groq returned an error: "
            f"{status_code}"
        )

    except Exception as exc:
        print(f"Groq generation error: {exc}")

        return (
            "The Groq LLM could not generate "
            "an answer."
        )