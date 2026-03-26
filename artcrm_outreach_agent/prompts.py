import json
from .protocols import AgentMission

OPT_OUT_LINE = {
    "de": "Wenn Sie keine weiteren Nachrichten wünschen, antworten Sie bitte mit 'Abmelden'.",
    "en": "If you'd prefer not to receive further messages, please reply with 'Unsubscribe'.",
    "fr": "Si vous ne souhaitez plus recevoir de messages, répondez 'Désabonner'.",
    "cs": "Pokud si nepřejete dostávat další zprávy, odpovězte prosím 'Odhlásit'.",
    "nl": "Als u geen verdere berichten wenst te ontvangen, antwoord dan met 'Afmelden'.",
    "es": "Si prefiere no recibir más mensajes, responda con 'Cancelar suscripción'.",
    "it": "Se non desidera ricevere ulteriori messaggi, risponda con 'Annulla iscrizione'.",
}


def draft_email_prompt(
    mission: AgentMission,
    contact: dict,
    language: str,
    interactions: list[dict],
    website_content: str,
) -> tuple[str, str]:
    opt_out = OPT_OUT_LINE.get(language, OPT_OUT_LINE["en"])

    system = (
        f"You are {mission.identity}.\n"
        f"Outreach style: {mission.outreach_style}\n\n"
        f"You are about to write a first-contact email to a potential venue. "
        f"Before writing, read everything provided — the contact details, research notes, "
        f"scout reasoning, previous interactions, and the venue's website content. "
        f"Use specific details from this research to make the email feel personal and genuine. "
        f"A generic email will be ignored. A specific, warm, artist-direct email might open a door."
    )

    # Build context sections
    contact_section = json.dumps(contact, ensure_ascii=False, indent=2)

    interaction_section = ""
    if interactions:
        lines = []
        for i in interactions:
            lines.append(
                f"  {i.get('interaction_date', '?')} | {i.get('direction', '?')} | "
                f"{i.get('method', '?')} | {i.get('summary', '')} | outcome: {i.get('outcome', '?')}"
            )
        interaction_section = "Previous interactions with this contact:\n" + "\n".join(lines)
    else:
        interaction_section = "Previous interactions: none — this is the first contact."

    website_section = ""
    if website_content:
        website_section = (
            f"Website content (read this carefully — use specific details in the email):\n"
            f"{website_content[:3000]}"
        )
    else:
        website_section = "Website content: not available — rely on the notes and contact details."

    user = (
        f"Write a first-contact email to {contact.get('name')} "
        f"({contact.get('type', 'venue')} in {contact.get('city')}).\n"
        f"Write entirely in language: {language}\n\n"
        f"--- CONTACT DETAILS & RESEARCH NOTES ---\n"
        f"{contact_section}\n\n"
        f"--- {interaction_section} ---\n\n"
        f"--- {website_section} ---\n\n"
        f"The email must:\n"
        f"- Reference something specific about this venue (from the notes or website) — "
        f"show you actually know who they are\n"
        f"- Introduce Christopher briefly and naturally\n"
        f"- Express genuine interest in their specific space and program\n"
        f"- Propose one concrete next step (visit, call, or sending portfolio)\n"
        f"- Be short — 4 to 6 sentences in the body, no fluff\n"
        f'- End with this opt-out line (verbatim): "{opt_out}"\n\n'
        f"Return a JSON object with:\n"
        f"- subject: email subject line\n"
        f"- body: full plain-text email body\n\n"
        f"Return ONLY the JSON object, no other text."
    )
    return system, user
