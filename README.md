# artcrm-outreach-agent

LangGraph agent that drafts first-contact emails for cold contacts and queues them for human approval. Nothing is sent until a human approves via the UI.

## What it does

Fetches contacts with `status=cold`, then for each:
1. GDPR compliance check — hard block if opt-out or erasure flag is set
2. Drafts a personalised first-contact email with the LLM in the contact's preferred language
3. Inserts the draft into the approval queue

The human sees the draft in the browser UI, can approve/edit/reject it, and the email is sent on approval.

## Usage

```python
from artcrm_outreach_agent import create_outreach_agent

agent = create_outreach_agent(
    llm=your_llm,
    fetch_ready_contacts=your_fetch_fn,
    check_compliance=your_compliance_fn,
    queue_for_approval=your_queue_fn,
    start_run=your_start_run_fn,
    finish_run=your_finish_run_fn,
    mission=your_mission,
)

result = agent.invoke({"limit": 20})
print(result["summary"])
# "outreach_agent: processed 8 contacts — 7 queued for approval, 1 blocked"
```

## Protocols

| Parameter | Protocol | Description |
|---|---|---|
| `llm` | `LanguageModel` | Any LangChain `BaseChatModel` |
| `fetch_ready_contacts` | `ReadyContactFetcher` | `(limit: int) -> list[dict]` |
| `check_compliance` | `ComplianceChecker` | `(contact_id: int) -> bool` |
| `queue_for_approval` | `ApprovalQueuer` | `(contact_id, run_id, subject, body) -> int` |
| `start_run` | `RunStarter` | `(agent_name, input_data) -> int` |
| `finish_run` | `RunFinisher` | `(run_id, status, summary, output_data) -> None` |
| `mission` | `AgentMission` | Any object with the six mission fields |

## Opt-out compliance

Opt-out lines are included in every email in 7 languages (de, en, fr, cs, nl, es, it), selected automatically from the contact's `preferred_language`. See [prompts.py](artcrm_outreach_agent/prompts.py).

## Testing

```bash
uv run pytest -v
```

## Support

If you find this useful, a small donation helps keep projects like this going:
[Donate via PayPal](https://paypal.me/christopherrehm001)
