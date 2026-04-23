from dataclasses import dataclass
from langchain_core.messages import AIMessage
from artcrm_outreach_agent import create_outreach_agent


@dataclass(frozen=True)
class DummyMission:
    goal: str = "Find art venues"
    identity: str = "Test Artist"
    targets: str = "galleries, cafes"
    fit_criteria: str = "contemporary art friendly"
    outreach_style: str = "personal"
    language_default: str = "de"
    website: str = "https://example.com"


class FakeLLM:
    def __init__(self, responses: list[str]):
        self._responses = list(responses)
        self._index = 0

    def invoke(self, messages):
        response = self._responses[self._index % len(self._responses)]
        self._index += 1
        return AIMessage(content=response)


SAMPLE_CONTACT = {
    "id": 1, "name": "Galerie Nord", "city": "Munich",
    "type": "gallery", "preferred_language": "de",
    "website": "https://galerie-nord.de",
}

DRAFT_RESPONSE = '{"subject": "Anfrage zur Ausstellung", "body": "Sehr geehrte Damen und Herren..."}'


def make_tools(contacts=None, compliance_result=True):
    queued = []
    runs = {}

    def fetch_ready_contacts(limit=20):
        return [SAMPLE_CONTACT] if contacts is None else contacts

    def fetch_interactions(contact_id):
        return []

    def fetch_page(url):
        return "Gallery showing contemporary regional artists."

    def check_compliance(contact_id):
        return compliance_result

    def queue_for_approval(contact_id, run_id, subject, body):
        queued.append({"contact_id": contact_id, "subject": subject, "body": body})
        return len(queued)

    def start_run(agent_name, input_data):
        run_id = len(runs) + 1
        runs[run_id] = {"status": "running"}
        return run_id

    def finish_run(run_id, status, summary, output_data):
        runs[run_id]["status"] = status

    return fetch_ready_contacts, fetch_interactions, fetch_page, check_compliance, queue_for_approval, start_run, finish_run, queued, runs


def make_agent(contacts=None, compliance_result=True, llm_responses=None):
    fetch, fetch_ix, fetch_pg, check, queue, start_run, finish_run, queued, runs = make_tools(contacts, compliance_result)
    llm = FakeLLM(llm_responses or [DRAFT_RESPONSE])
    agent = create_outreach_agent(
        llm=llm,
        fetch_ready_contacts=fetch,
        fetch_interactions=fetch_ix,
        fetch_page=fetch_pg,
        check_compliance=check,
        queue_for_approval=queue,
        start_run=start_run,
        finish_run=finish_run,
        mission=DummyMission(),
    )
    return agent, queued, runs


def test_queues_compliant_contact():
    agent, queued, _ = make_agent()
    result = agent.invoke({"limit": 20})

    assert result["queued_count"] == 1
    assert result["blocked_count"] == 0
    assert queued[0]["subject"] == "Anfrage zur Ausstellung"


def test_blocks_opted_out_contact():
    agent, queued, _ = make_agent(compliance_result=False)
    result = agent.invoke({"limit": 20})

    assert result["queued_count"] == 0
    assert result["blocked_count"] == 1
    assert queued == []


def test_handles_draft_parse_error():
    agent, queued, _ = make_agent(llm_responses=["not valid json"])
    result = agent.invoke({"limit": 20})

    assert result["queued_count"] == 0
    assert result["blocked_count"] == 1
    assert queued == []


def test_handles_empty_contacts():
    agent, queued, _ = make_agent(contacts=[])
    result = agent.invoke({"limit": 20})

    assert result["queued_count"] == 0
    assert result["blocked_count"] == 0
    assert "0 contacts" in result["summary"]


def test_multiple_contacts_mixed_compliance():
    contacts = [
        {**SAMPLE_CONTACT, "id": 1},
        {**SAMPLE_CONTACT, "id": 2},
        {**SAMPLE_CONTACT, "id": 3},
    ]
    compliance = {1: True, 2: False, 3: True}

    fetch, fetch_ix, fetch_pg, _, queue, start_run, finish_run, queued, runs = make_tools(contacts=contacts)

    def check_compliance(contact_id):
        return compliance[contact_id]

    llm = FakeLLM([DRAFT_RESPONSE])
    agent = create_outreach_agent(
        llm=llm,
        fetch_ready_contacts=fetch,
        fetch_interactions=fetch_ix,
        fetch_page=fetch_pg,
        check_compliance=check_compliance,
        queue_for_approval=queue,
        start_run=start_run,
        finish_run=finish_run,
        mission=DummyMission(),
    )
    result = agent.invoke({"limit": 20})

    assert result["queued_count"] == 2
    assert result["blocked_count"] == 1
