"""
Multi-agent lease analysis pipeline.

Each specialist agent only sees the lease chunks retrieved for its
own domain (via the vector store), rather than the entire document.
A coordinator then merges the per-agent findings into one structured
result. This is both a better prompting strategy (smaller, focused
context per call) and a stronger architecture to describe on a
resume than "one prompt does everything."
"""

from dataclasses import dataclass, field
import json

from modules.vectorstore import LeaseVectorStore

# Each agent's name, the retrieval query used to pull relevant chunks,
# and the domain description injected into its system prompt.
AGENT_SPECS = [
    {
        "name": "Financial",
        "query": "rent amount due date late fee security deposit charges increase",
        "focus": "rent, fees, deposits, and any financial obligations or penalties",
    },
    {
        "name": "Privacy & Access",
        "query": "landlord entry notice access inspection privacy",
        "focus": "landlord's right of entry, notice periods, and tenant privacy",
    },
    {
        "name": "Termination & Renewal",
        "query": "termination early exit lease end automatic renewal notice period",
        "focus": "how the lease ends, renews, or can be terminated early, and by whom",
    },
    {
        "name": "Maintenance & Repairs",
        "query": "maintenance repairs responsibility plumbing appliances habitability",
        "focus": "who is responsible for repairs, maintenance, and habitability issues",
    },
    {
        "name": "Legal & Liability",
        "query": "arbitration waiver liability indemnification governing law disputes",
        "focus": "arbitration clauses, liability waivers, indemnification, and legal rights the tenant may be giving up",
    },
]


@dataclass
class Flag:
    issue: str
    risk: str
    level: str  # HIGH / MED / LOW
    evidence_page: int | None
    evidence_quote: str
    confidence: int  # 0-100
    recommendation: str


@dataclass
class AgentResult:
    agent_name: str
    focus: str
    category_score: int  # 0-100, 100 = tenant-friendly
    flags: list[Flag] = field(default_factory=list)


@dataclass
class AnalysisResult:
    overall_score: int
    summary: str
    agents: list[AgentResult]
    used_ocr: bool = False

    @property
    def all_flags(self) -> list[Flag]:
        return [f for agent in self.agents for f in agent.flags]


AGENT_PROMPT_TEMPLATE = """You are a specialist "{agent_name}" agent on a tenant-advocacy review team.
Your ONLY job is to review the lease excerpts below for issues related to: {focus}.
Ignore anything outside your specialty - other agents handle that.

CRITICAL INSTRUCTIONS:
1. Be realistic. Standard, common clauses are NOT red flags. Only flag things that are
   genuinely predatory, illegal, unusual, or meaningfully unfavorable to the tenant.
2. Every flag MUST include a short verbatim quote (under 25 words) from the excerpts as evidence,
   and the page number that excerpt came from.
3. If nothing in your specialty is concerning, return an empty "flags" list and a high category_score.
4. category_score: 0-100, where 100 = very tenant-friendly / no concerns in this category, 0 = severe issues.

Return ONLY this JSON object, no markdown, no commentary:
{{
  "category_score": <0-100 integer>,
  "flags": [
    {{
      "issue": "short name of the issue",
      "risk": "1-2 sentence plain-English explanation of why this matters for the tenant",
      "level": "HIGH" | "MED" | "LOW",
      "evidence_page": <page number as integer>,
      "evidence_quote": "short verbatim quote, under 25 words",
      "confidence": <0-100 integer, how confident you are this is a real issue>,
      "recommendation": "1 sentence on what the tenant should ask for or do"
    }}
  ]
}}

Lease excerpts (each tagged with its page number):
{excerpts}
"""

COORDINATOR_PROMPT_TEMPLATE = """You are the coordinator of a tenant-advocacy lease review team.
Below are the category scores from five specialist agents. Write ONE overview.

Category scores:
{scores_summary}

Return ONLY this JSON object:
{{
  "overall_score": <0-100 integer, a holistic weighted view - do not just average blindly,
                    weight HIGH-severity categories more heavily>,
  "summary": "1-2 sentence plain-English overview of the lease's overall risk profile"
}}
"""


def _format_excerpts(retrieved) -> str:
    return "\n\n".join(f"[Page {r.chunk.page_number}]\n{r.chunk.text}" for r in retrieved)


def _call_gemini_json(model, prompt: str) -> dict:
    raw = model.generate_content(prompt).text
    clean = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(clean)


def run_agent(model, store: LeaseVectorStore, spec: dict, k: int = 5) -> AgentResult:
    retrieved = store.search(spec["query"], k=k)
    excerpts = _format_excerpts(retrieved)

    if not excerpts:
        return AgentResult(agent_name=spec["name"], focus=spec["focus"], category_score=100, flags=[])

    prompt = AGENT_PROMPT_TEMPLATE.format(
        agent_name=spec["name"], focus=spec["focus"], excerpts=excerpts
    )
    data = _call_gemini_json(model, prompt)

    flags = [
        Flag(
            issue=f.get("issue", "Unnamed issue"),
            risk=f.get("risk", ""),
            level=f.get("level", "LOW"),
            evidence_page=f.get("evidence_page"),
            evidence_quote=f.get("evidence_quote", ""),
            confidence=int(f.get("confidence", 50)),
            recommendation=f.get("recommendation", ""),
        )
        for f in data.get("flags", [])
    ]

    return AgentResult(
        agent_name=spec["name"],
        focus=spec["focus"],
        category_score=int(data.get("category_score", 70)),
        flags=flags,
    )


def run_coordinator(model, agent_results: list[AgentResult]) -> tuple[int, str]:
    scores_summary = "\n".join(
        f"- {a.agent_name}: {a.category_score}/100 ({len(a.flags)} flags)" for a in agent_results
    )
    prompt = COORDINATOR_PROMPT_TEMPLATE.format(scores_summary=scores_summary)
    data = _call_gemini_json(model, prompt)
    return int(data.get("overall_score", 70)), data.get("summary", "")


def run_full_analysis(model, store: LeaseVectorStore, used_ocr: bool = False) -> AnalysisResult:
    """Run every specialist agent, then the coordinator, and return one result."""
    agent_results = [run_agent(model, store, spec) for spec in AGENT_SPECS]
    overall_score, summary = run_coordinator(model, agent_results)

    return AnalysisResult(
        overall_score=overall_score,
        summary=summary,
        agents=agent_results,
        used_ocr=used_ocr,
    )
