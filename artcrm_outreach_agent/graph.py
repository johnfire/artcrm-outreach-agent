"""
Outreach agent.

Fetches contacts with status='cold', checks GDPR compliance, drafts a
personalized first-contact email per contact, and queues each draft for
human approval. Nothing is sent until a human approves via the UI.

Pipeline position: research → enrich → scout → outreach → followup
"""
import logging

from langchain_core.messages import SystemMessage, HumanMessage

from .protocols import (
    AgentMission, LanguageModel, ReadyContactFetcher, InteractionFetcher,
    ComplianceChecker, ApprovalQueuer, PageFetcher, RunStarter, RunFinisher,
)
from .prompts import draft_email_prompt
from ._utils import parse_json_response

logger = logging.getLogger(__name__)


class _OutreachAgent:
    def __init__(
        self,
        llm: LanguageModel,
        fetch_ready_contacts: ReadyContactFetcher,
        fetch_interactions: InteractionFetcher,
        fetch_page: PageFetcher,
        check_compliance: ComplianceChecker,
        queue_for_approval: ApprovalQueuer,
        start_run: RunStarter,
        finish_run: RunFinisher,
        mission: AgentMission,
    ):
        self._llm = llm
        self._fetch_ready_contacts = fetch_ready_contacts
        self._fetch_interactions = fetch_interactions
        self._fetch_page = fetch_page
        self._check_compliance = check_compliance
        self._queue_for_approval = queue_for_approval
        self._start_run = start_run
        self._finish_run = finish_run
        self._mission = mission

    def invoke(self, inputs: dict) -> dict:
        limit = inputs.get("limit", 20)
        learnings = inputs.get("learnings", [])
        run_id = self._start_run("outreach_agent", {"limit": limit})
        errors = []

        contacts = self._fetch(limit, errors)
        drafts = self._draft_all(contacts, learnings)
        queued_count, blocked_count = self._queue_drafts(drafts, run_id)

        total = len(contacts)
        summary = (
            f"outreach_agent: processed {total} contacts — "
            f"{queued_count} queued for approval, {blocked_count} blocked"
        )
        if errors:
            summary += f", {len(errors)} error(s)"
        self._finish_run(run_id, "completed", summary, {"queued": queued_count, "blocked": blocked_count, "total": total})
        logger.info(summary)
        return {"summary": summary, "queued_count": queued_count, "blocked_count": blocked_count}

    def _fetch(self, limit: int, errors: list) -> list[dict]:
        try:
            return self._fetch_ready_contacts(limit=limit)
        except Exception as e:
            errors.append(f"fetch_ready_contacts: {e}")
            return []

    def _draft_all(self, contacts: list[dict], learnings: list[str]) -> list[dict]:
        drafts = []
        for contact in contacts:
            contact_id = contact["id"]

            try:
                allowed = self._check_compliance(contact_id)
            except Exception as e:
                drafts.append({"contact_id": contact_id, "blocked_reason": f"compliance check error: {e}"})
                continue

            if not allowed:
                drafts.append({"contact_id": contact_id, "blocked_reason": "opt-out or erasure flag set"})
                continue

            try:
                interactions = self._fetch_interactions(contact_id)
            except Exception:
                interactions = []

            website_content = ""
            website = contact.get("website", "")
            if website:
                try:
                    website_content = self._fetch_page(website)
                except Exception:
                    pass

            language = contact.get("preferred_language") or self._mission.language_default
            system, user = draft_email_prompt(
                self._mission, contact, language,
                interactions=interactions,
                website_content=website_content,
                learnings=learnings,
            )
            try:
                response = self._llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
                result = parse_json_response(response.content)
                drafts.append({
                    "contact_id": contact_id,
                    "subject": result.get("subject", ""),
                    "body": result.get("body", ""),
                })
            except Exception as e:
                drafts.append({"contact_id": contact_id, "blocked_reason": f"draft error: {e}"})

        return drafts

    def _queue_drafts(self, drafts: list[dict], run_id: int) -> tuple[int, int]:
        queued = 0
        blocked = 0
        for draft in drafts:
            if draft.get("blocked_reason"):
                blocked += 1
                continue
            try:
                self._queue_for_approval(
                    contact_id=draft["contact_id"],
                    run_id=run_id,
                    subject=draft["subject"],
                    body=draft["body"],
                )
                queued += 1
            except Exception:
                blocked += 1
        return queued, blocked


def create_outreach_agent(
    llm: LanguageModel,
    fetch_ready_contacts: ReadyContactFetcher,
    fetch_interactions: InteractionFetcher,
    fetch_page: PageFetcher,
    check_compliance: ComplianceChecker,
    queue_for_approval: ApprovalQueuer,
    start_run: RunStarter,
    finish_run: RunFinisher,
    mission: AgentMission,
) -> _OutreachAgent:
    """
    Build and return an outreach agent.

    Fetches cold contacts, checks GDPR compliance, drafts personalized
    first-contact emails via LLM, and queues each for human approval.

    Usage:
        agent = create_outreach_agent(llm=..., fetch_ready_contacts=..., ...)
        result = agent.invoke({"limit": 20})
        print(result["summary"])
    """
    return _OutreachAgent(
        llm=llm,
        fetch_ready_contacts=fetch_ready_contacts,
        fetch_interactions=fetch_interactions,
        fetch_page=fetch_page,
        check_compliance=check_compliance,
        queue_for_approval=queue_for_approval,
        start_run=start_run,
        finish_run=finish_run,
        mission=mission,
    )
