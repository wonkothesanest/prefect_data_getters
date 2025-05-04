"""
Email processor that extracts one field per chain, using Mistral-Nemo via Ollama.
Dates are handled explicitly; empty / missing values are allowed.
"""

from __future__ import annotations
import datetime as _dt
from dataclasses import dataclass
import os
from typing import Dict, List, Any
from langchain_community.chat_models import ChatOllama
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from langchain.chains.llm import LLMChain
from langchain_openai import ChatOpenAI

# --------------------------------------------------------------------------- #
# Constants                                                                   #
# --------------------------------------------------------------------------- #

CATEGORIES = [
    "Account Issues","Team","Collaboration","Interview","Personal Info",
    "Job Opportunity","Project","Task","Request","Onboarding","Kickoff","Meeting",
    "Technical Issue","Engineering","System Alert","System Update","Error Report",
    "Announcement","Info Sharing","Discussion","Reminder","Survey","Marketing",
    "Event","LinkedIn","Industry News","Security","IT Support","Spam","Unsolicited",
]
TEAMS = [
    "Client Team","OCI","Data Acquisition Team","Onboarding Team",
    "Accounts Payable","Backend Team","Capital Markets",
    "Client Success", "Client and Customer Engagement","Operations","Data Engineering","Data Science",
    "Engineering","Executive Team","HR","Legal",
    "Product Team","QA","Sales","Security","Software Engineering",
]
PROJECTS = [
    "2025 Roadmap","BUSA Onboarding","Client Engagement",
    "Commercial Ops","Company Initiatives","Data Acquisition","Engineering Roadmap",
    "Hyperion","Metadata Verification","Onboarding","PVT","Ops Efficiency & TTR",
    "Client Portal", "Customer Portal", "Reporting","VEE Ledger",
    "Residential Ops","Service Cloud Launch","SolCharged Event","VEE Project","Q1", "Q2", "Q3", "Q4"
]
SYSTEMS = [
    "APIs","Asana","Atlassian","Bitbucket","Confluence","Databricks",
    "Enphase","EverBright","Google Analytics","Green Power Monitor","Jira",
    "LastPass","Okta","Resolv","Salesforce","Service Cloud","Sigma","Slack","Slab",
    "Zendesk",
]

# --------------------------------------------------------------------------- #
# Generic “one-field” chain builder                                           #
# --------------------------------------------------------------------------- #

def _build_field_chain(
    llm,
    *,
    name: str,
    description: str,
    allowed_values: List[str] | None = None,
    boolean: bool = False,
    context_keys: List[str] | None = None,
) -> LLMChain:
    """
    Builds a chain whose ONLY job is to return JSON with the single key `name`.
    If the value is missing → return [] for arrays, "" for strings, or false/null.
    """
    context_keys = context_keys or []

    # --------------- system prompt -----------------------------------------
    sys_tmpl = (
        "You are a precise extraction assistant.\n"
        f"Return ONLY valid JSON with a single key \"{name}\".\n"
        f"{description}\n"
        "• Do NOT invent or guess — if the email does not supply information, "
        "return an empty list [] (for arrays), an empty string \"\" (for strings), "
        "or false/null (for booleans).\n"
    )
    if allowed_values:
        sys_tmpl += f"Allowed values: {allowed_values}\n"

    system_msg = SystemMessagePromptTemplate.from_template(sys_tmpl.strip())

    # --------------- human prompt ------------------------------------------
    human_lines = []
    for k in context_keys:
        human_lines.append(f"{k.replace('_',' ').title()}: {{{k}}}")
    human_lines.append("Email:\n{text}\n\n")
    human_lines.append(sys_tmpl)
    human_msg = ChatPromptTemplate.from_template("\n".join(human_lines))

    # --------------- output schema -----------------------------------------
    schema_type = "boolean" if boolean else (
        "array" if allowed_values else "string"
    )
    schema = ResponseSchema(name=name, description=description, type=schema_type)
    parser = StructuredOutputParser.from_response_schemas([schema])

    return LLMChain(
        llm=llm,
        prompt=ChatPromptTemplate.from_messages([system_msg, human_msg]),
        output_parser=parser,
    )

# --------------------------------------------------------------------------- #
# ParsedEmail dataclass                                                       #
# --------------------------------------------------------------------------- #

@dataclass
class ParsedEmail:
    summary: str
    reason: str
    is_important: bool
    is_urgent: bool
    categories: List[str]
    teams: List[str]
    projects: List[str]
    systems: List[str]
    action_items: List[str]
    deadlines_or_dates: List[str]
    attachments_summary: str
    notes_for_memory: List[str]

# --------------------------------------------------------------------------- #
# EmailExtractor                                                              #
# --------------------------------------------------------------------------- #

class EmailExtractor:
    """
    Breaks extraction into many tiny chains so the model never juggles
    more than one field at a time.
    """
    def __init__(self, model_name: str = "mistral-nemo:latest"):
        self.llm = ChatOllama(model=model_name, temperature=0.2)
        # self.llm = ChatOpenAI(
        #     model="gpt-4o",
        #     temperature=0.2,
        # )

        # --- build chains ---------------------------------------------------
        self.summary_chain     = _build_field_chain(
            self.llm,
            name="summary",
            description="≤2-sentence summary of the email.",
        )

        # arrays
        self.categories_chain  = _build_field_chain(
            self.llm, name="categories",
            description="String Array of categories mentioned.",
            allowed_values=CATEGORIES,
        )
        self.teams_chain       = _build_field_chain(
            self.llm, name="teams",
            description="String Array of teams explicitly referenced.",
            allowed_values=TEAMS,
        )
        self.projects_chain    = _build_field_chain(
            self.llm, name="projects",
            description="String Array of projects explicitly referenced.",
            allowed_values=PROJECTS,
        )
        self.systems_chain     = _build_field_chain(
            self.llm, name="systems",
            description="String Array of systems explicitly referenced.",
            allowed_values=SYSTEMS,
        )

        # free-form lists / strings
        date_keys = ["email_date", "current_date"]
        self.action_chain      = _build_field_chain(
            self.llm, name="action_items",
            description=(
                "String array of Bullet-point tasks. **Any dates MUST be ISO-8601 (YYYY-MM-DD)**."
            ),
            context_keys=date_keys,
        )
        self.deadline_chain    = _build_field_chain(
            self.llm, name="deadlines_or_dates",
            description=(
                "String array of explicit deadlines or schedule references. "
                "Return each date in the string in ISO-8601."
            ),
            context_keys=date_keys,
        )
        self.attach_chain      = _build_field_chain(
            self.llm, name="attachments_summary",
            description="String array of Short description of attachments.",
        )
        self.memory_chain      = _build_field_chain(
            self.llm, name="notes_for_memory",
            description="String array of Long-term context worth remembering.",
        )

        # reason depends on summary -----------------------------------------
        self.reason_chain      = _build_field_chain(
            self.llm, name="reason",
            description="One paragraph on priority rationale, why can dusty ignore this email or why is it important that he reads and addresses this email for Dusty to know about the management of his teams or projects. Do not give a high priority to any emails that have been sent out to a wide audience. Also give your final judgement (true or false) if this is high prioirty and important",
            context_keys=["summary"],
        )

        # booleans depend on summary + reason -------------------------------
        context_sr = ["summary", "reason"]
        self.important_chain   = _build_field_chain(
            self.llm, name="is_important", boolean=True,
            description="true ↔ Dusty must act personally or this is vital information for Dusty to know about the management of his teams or projects. Do not include any emails that have been sent out to a wide audience.",
            context_keys=context_sr,
        )
        self.urgent_chain      = _build_field_chain(
            self.llm, name="is_urgent", boolean=True,
            description="true ↔ needs reply < 24 h.",
            context_keys=context_sr,
        )

    # --------------------------------------------------------------------- #
    def parse_email(self, email: Dict[str, str]) -> ParsedEmail:
        """
        email keys expected: to, from, subject, date (ISO string), text
        """
        state: Dict[str, Any] = {
            "text": email["text"],
            "email_date": email["date"],
            "current_date": _dt.date.today().isoformat(),
        }

        # 1) summary first --------------------------------------------------
        state.update(self.summary_chain.run(state))

        # 2) parallel-ish independents -------------------------------------
        for chain in [
            self.categories_chain, self.teams_chain, self.projects_chain,
            self.systems_chain, self.action_chain, self.deadline_chain,
            self.attach_chain, self.memory_chain
        ]:
            state.update(chain.run(state))

        # 3) reason, then booleans -----------------------------------------
        state.update(self.reason_chain.run(state))
        state.update(self.important_chain.run(state))
        state.update(self.urgent_chain.run(state))

        # 4) remove helper keys before dataclass ---------------------------
        for k in ("text", "email_date", "current_date"):
            state.pop(k, None)

        try:
            ParsedEmail(**state)
        except TypeError as e:
            raise TypeError(
                f"Failed to parse email: {email['subject']}\n"
                f"State: {state}\n"
                f"Error: {e}"
            )

        return state

# --------------------------------------------------------------------------- #
# Example usage with several emails ----------------------------------------- #
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    examples: List[Dict[str, str]] = [
        # A normal “needs-input” mail
        {
            "to": "dusty@omnidian.com",
            "from": "john@example.com",
            "subject": "Phase-2 Roll-out timeline",
            "date": "2025-04-22",
            "text": (
                "Hey Dusty,\n\n"
                "Could you meet next Thursday (2025-04-24) at 14:00 to lock the "
                "Phase-2 roll-out? I’ll also need your feedback on the new "
                "ingestion metrics by 2025-05-01.\n\n– John"
            ),
        },
        # An email with *no* teams / projects / systems mentioned
        {
            "to": "dusty@omnidian.com",
            "from": "hr@omnidian.com",
            "subject": "401k Plan Changes",
            "date": "2025-04-21",
            "text": (
                "Hi Dusty,\n\nWe’re moving our 401k administrator to Vanguard. "
                "No action is required from you at this time; details will follow "
                "in June.\n\nThanks, HR"
            ),
        },
        # Spam / unsolicited
        {
            "to": "dusty@omnidian.com",
            "from": "sales@randomsaas.com",
            "subject": "🚀 Boost productivity with AI-Foo!",
            "date": "2025-04-20",
            "text": (
                "Hi there! Want to 10× your engineering team’s velocity? "
                "Try AI-Foo today (30-day FREE trial)!\n\nBest, Random SaaS Sales"
            ),
        },
    ]

    processor = EmailExtractor()
    for ex in examples:
        parsed = processor.process_email(ex)
        print(f"\n----- {ex['subject']} -----")
        print(parsed)
