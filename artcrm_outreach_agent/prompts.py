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
) -> tuple[str, str]:
    opt_out = OPT_OUT_LINE.get(language, OPT_OUT_LINE["en"])
    system = (
        f"You are {mission.identity}.\n"
        f"Outreach style: {mission.outreach_style}"
    )
    user = (
        f"Write a first-contact email to {contact.get('name')} "
        f"({contact.get('type', 'venue')} in {contact.get('city')}).\n"
        f"Write entirely in language code: {language}\n\n"
        f"Contact details:\n{json.dumps(contact, ensure_ascii=False, indent=2)}\n\n"
        f"The email should:\n"
        f"- Be personal and specific to this venue\n"
        f"- Introduce you briefly\n"
        f"- Express genuine interest in their space\n"
        f"- Propose a concrete next step (visit, call, or sending portfolio)\n"
        f'- End with this opt-out line (verbatim): "{opt_out}"\n\n'
        f"Return a JSON object with:\n"
        f"- subject: email subject line\n"
        f"- body: full plain-text email body\n\n"
        f"Return ONLY the JSON object, no other text."
    )
    return system, user
