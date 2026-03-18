"""physics_expert node — extracts parameters from paper or user input via RAG."""
from __future__ import annotations
from pathlib import Path
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from simagents.graph.state import ExtractionState

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "physics_expert.md"


def _load_prompt(target_software: str, input_context: str, custom_prompt: str | None) -> str:
    template = _PROMPT_PATH.read_text(encoding="utf-8")
    return template.format(target_software=target_software, input_context=input_context, custom_prompt=custom_prompt or "")


def _build_input_context(state: ExtractionState) -> str:
    mode = state.get("input_mode", "paper")
    parts = []
    if mode in ("paper", "hybrid"):
        parts.append("A scientific paper has been provided. Use the search tool to find parameter values.")
    if mode in ("chat", "hybrid"):
        user_params = state.get("user_parameters", {})
        parts.append(f"User-provided parameters: {user_params}")
        if mode == "hybrid":
            parts.append("User-provided values take precedence over paper values.")
    missing = state.get("missing_parameters", [])
    if missing:
        parts.append(f"\nPrevious iteration found these parameters MISSING: {', '.join(missing)}")
        parts.append("Please search specifically for these missing parameters.")
    user_answers = state.get("user_answers", [])
    if user_answers:
        parts.append(f"\nUser provided these answers: {user_answers}")
    return "\n".join(parts)


def physics_expert(state: ExtractionState, config: RunnableConfig) -> dict:
    configurable = config.get("configurable", {})
    llm = configurable["llm"]
    paper_retriever = configurable.get("paper_retriever")
    target_software = state.get("target_software", "mp-gadget")
    input_context = _build_input_context(state)
    system_prompt = _load_prompt(target_software, input_context, state.get("custom_prompt"))
    user_msg_parts = ["Please extract the simulation parameters from the provided source."]
    if paper_retriever and state.get("input_mode") in ("paper", "hybrid"):
        search_queries = ["cosmological parameters simulation", "box size resolution particle number", "initial conditions redshift"]
        missing = state.get("missing_parameters", [])
        if missing:
            search_queries.append(" ".join(missing))
        retrieved_chunks = []
        for query in search_queries:
            docs = paper_retriever.invoke(query)
            for doc in docs:
                retrieved_chunks.append(doc.page_content)
        if retrieved_chunks:
            context = "\n---\n".join(retrieved_chunks)
            user_msg_parts.append(f"\n## Relevant sections from the paper:\n{context}")
    messages = [SystemMessage(content=system_prompt), HumanMessage(content="\n".join(user_msg_parts))]
    response = llm.invoke(messages)
    iteration = state.get("iteration", 0)
    return {
        "raw_parameters": response.content,
        "iteration": iteration + 1,
        "messages": [HumanMessage(content=f"[Iteration {iteration + 1}] Extract parameters"), response],
    }
