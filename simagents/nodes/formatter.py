"""formatter node — validates and formats parameters against software docs via RAG."""
from __future__ import annotations
import json
import re
from pathlib import Path
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from simagents.graph.state import ExtractionState

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "formatter.md"


def _load_prompt(target_software: str, raw_parameters: str) -> str:
    template = _PROMPT_PATH.read_text(encoding="utf-8")
    return template.format(target_software=target_software, raw_parameters=raw_parameters)


def _extract_json(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    code_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if code_match:
        try:
            return json.loads(code_match.group(1))
        except json.JSONDecodeError:
            pass
    json_match = re.search(r"\{.*\}", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    raise ValueError(f"Could not extract JSON from response: {text[:200]}...")


def formatter(state: ExtractionState, config: RunnableConfig) -> dict:
    configurable = config.get("configurable", {})
    llm = configurable["llm"]
    docs_retriever = configurable["docs_retriever"]
    target_software = state.get("target_software", "mp-gadget")
    raw_parameters = state.get("raw_parameters", "")
    system_prompt = _load_prompt(target_software, raw_parameters)
    search_queries = [f"{target_software} required parameters", f"{target_software} parameter format units", "cosmological parameters configuration"]
    retrieved_docs = []
    for query in search_queries:
        docs = docs_retriever.invoke(query)
        for doc in docs:
            retrieved_docs.append(doc.page_content)
    doc_context = "\n---\n".join(retrieved_docs) if retrieved_docs else "No documentation found."
    user_msg = f"## Documentation Reference\n{doc_context}\n\n## Extracted Parameters\n{raw_parameters}\n\nPlease validate and format these parameters according to {target_software} documentation."
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_msg)]
    response = llm.invoke(messages)
    try:
        parsed = _extract_json(response.content)
    except ValueError:
        retry_msg = HumanMessage(content="Your response was not valid JSON. Please respond with ONLY the JSON object, no other text.")
        response = llm.invoke(messages + [response, retry_msg])
        try:
            parsed = _extract_json(response.content)
        except ValueError:
            return {
                "formatted_parameters": {"genic": {}, "gadget": {}, "comment": response.content, "sources": []},
                "status": "incomplete",
                "missing_parameters": ["JSON_PARSE_FAILED"],
                "messages": [response],
            }
    return {
        "formatted_parameters": parsed,
        "status": parsed.get("status", "incomplete"),
        "missing_parameters": parsed.get("missing_parameters", []),
        "user_questions": parsed.get("user_questions", []),
        "messages": [response],
    }
