"""Thin wrappers around the three providers, returning plain strings.

We intentionally avoid LangChain's message abstractions for the per-node calls
because Attacker/Defender/Evaluator all just need a (system, user) -> str API.
This keeps the agents readable and easy to swap.
"""
from __future__ import annotations

import os
from functools import lru_cache

from anthropic import Anthropic, AnthropicBedrock
from google import generativeai as genai
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

# ── Model IDs ───────────────────────────────────────────────────────
# 환경변수는 *호출 시점에* 다시 읽는다. 모듈 최상단에서 굳히면 import 가
# load_dotenv() 보다 먼저 실행될 때(예: orchestrator.py) 기본값으로 굳혀
# 버려 인증이 실패한다.

def _gpt_model() -> str:
    return os.getenv("GPT_MODEL", "gpt-4o")

def _gemini_model_id() -> str:
    return os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

def _claude_provider() -> str:
    return os.getenv("CLAUDE_PROVIDER", "anthropic").lower()

def _aws_region() -> str:
    return os.getenv("AWS_REGION", "ap-northeast-2")


# Backward-compat 노출 (다른 모듈이 import 하는 경우 대비)
GPT_MODEL = os.getenv("GPT_MODEL", "gpt-4o")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")


@lru_cache(maxsize=1)
def _openai() -> OpenAI:
    return OpenAI(api_key=os.environ["OPENAI_API_KEY"])


@lru_cache(maxsize=1)
def _anthropic():
    """Claude client — Anthropic 직접 API 또는 AWS Bedrock."""
    if _claude_provider() == "bedrock":
        # AnthropicBedrock 은 표준 AWS 자격증명 체인을 사용한다
        # (AWS_BEARER_TOKEN_BEDROCK / AWS_ACCESS_KEY_ID / ~/.aws/credentials 등).
        return AnthropicBedrock(aws_region=_aws_region())
    return Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def _claude_model() -> str:
    if _claude_provider() == "bedrock":
        return os.getenv(
            "CLAUDE_BEDROCK_MODEL", "global.anthropic.claude-sonnet-4-6"
        )
    return os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")


@lru_cache(maxsize=1)
def _gemini():
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    # Disable Gemini's built-in safety filters so the Defender's *own* safety
    # behavior — not Google's input filter — is what we measure.
    return genai.GenerativeModel(
        GEMINI_MODEL,
        safety_settings=[
            {"category": c, "threshold": "BLOCK_NONE"}
            for c in (
                "HARM_CATEGORY_HARASSMENT",
                "HARM_CATEGORY_HATE_SPEECH",
                "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "HARM_CATEGORY_DANGEROUS_CONTENT",
            )
        ],
    )


@retry(stop=stop_after_attempt(4), wait=wait_exponential(min=2, max=30))
def call_gpt(
    system: str,
    history: list[dict],
    *,
    temperature: float = 0.8,
    top_p: float | None = None,
    frequency_penalty: float | None = None,
    presence_penalty: float | None = None,
) -> str:
    msgs = [{"role": "system", "content": system}, *history]
    kwargs: dict = {"model": GPT_MODEL, "messages": msgs, "temperature": temperature}
    if top_p is not None:
        kwargs["top_p"] = top_p
    if frequency_penalty is not None:
        kwargs["frequency_penalty"] = frequency_penalty
    if presence_penalty is not None:
        kwargs["presence_penalty"] = presence_penalty
    r = _openai().chat.completions.create(**kwargs)
    return r.choices[0].message.content or ""


@retry(stop=stop_after_attempt(4), wait=wait_exponential(min=2, max=30))
def call_gemini(
    system: str,
    history: list[dict],
    *,
    temperature: float = 0.8,
    top_p: float | None = None,
    # Gemini doesn't support frequency/presence penalties — accept & ignore for API parity
    frequency_penalty: float | None = None,  # noqa: ARG001
    presence_penalty: float | None = None,   # noqa: ARG001
) -> str:
    contents = []
    for i, m in enumerate(history):
        role = "user" if m["role"] == "user" else "model"
        text = m["content"] if i > 0 else f"{system}\n\n{m['content']}"
        contents.append({"role": role, "parts": [text]})
    gen_cfg: dict = {"temperature": temperature}
    if top_p is not None:
        gen_cfg["top_p"] = top_p
    r = _gemini().generate_content(contents, generation_config=gen_cfg)
    return (r.text or "").strip()


@retry(stop=stop_after_attempt(4), wait=wait_exponential(min=2, max=30))
def call_claude(system: str, history: list[dict], *, temperature: float = 0.2,
                max_tokens: int = 2048) -> str:
    # messages.create API 는 Anthropic 직접/Bedrock 동일 — 모델 id 만 다르다.
    # 데이터셋 확장처럼 긴 JSON 배열을 받을 때는 호출 측에서 max_tokens 를 올린다.
    r = _anthropic().messages.create(
        model=_claude_model(),
        max_tokens=max_tokens,
        system=system,
        messages=history,
        temperature=temperature,
    )
    return "".join(b.text for b in r.content if hasattr(b, "text"))


# ── Role → provider dispatch ────────────────────────────────────────
# Experiment A: Attacker=GPT, Defender=Gemini, Evaluator=Claude
# Experiment B: Attacker=Gemini, Defender=GPT, Evaluator=Claude
ATTACKER_FN = {"A": call_gpt, "B": call_gemini}
DEFENDER_FN = {"A": call_gemini, "B": call_gpt}
EVALUATOR_FN = call_claude
