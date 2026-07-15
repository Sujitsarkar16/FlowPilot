"""Deterministic, sanitized internal document templates."""

import json
from collections.abc import Iterable, Mapping

from app.services.content_safety import sanitize_untrusted_content

MAX_DOCUMENT_CHARS = 20_000


class DocumentTemplateError(ValueError):
    """Raised when a document request cannot be rendered safely."""


class DocumentTemplateService:
    """Render fixed templates from event entities; no model call is needed."""

    _aliases = {
        "client_requirement_summary": "client_requirements_summary",
        "requirements_summary": "client_requirements_summary",
        "proposal": "proposal_draft",
        "invoice": "invoice_template",
    }
    _supported = frozenset(
        {"itinerary", "packing_checklist", "client_requirements_summary", "proposal_draft", "invoice_template"}
    )

    def render(
        self,
        document_type: str,
        *,
        event: object | None = None,
        entities: Iterable[object] = (),
        content: str | None = None,
    ) -> str:
        kind = self._aliases.get(document_type, document_type)
        if kind not in self._supported:
            raise DocumentTemplateError("Unsupported document type")
        values = self._values(event, entities)
        rendered = self._template(kind, values)
        if content:
            notes = sanitize_untrusted_content(content, max_chars=MAX_DOCUMENT_CHARS).text
            if notes:
                rendered = f"{rendered}\n\n## Notes\n{notes}"
        return rendered[:MAX_DOCUMENT_CHARS]

    def _values(self, event: object | None, entities: Iterable[object]) -> dict[str, str]:
        source = list(self._entities(event)) + list(entities)
        values: dict[str, list[str]] = {}
        for entity in source:
            kind, value, sensitive = self._entity(entity)
            if not kind or sensitive:
                continue
            text = self._text(value)
            if text:
                values.setdefault(kind, []).append(text)
        summary = self._text(self._attribute(event, "summary")) or "Details to be confirmed"
        flattened = {kind: "; ".join(sorted(items)) for kind, items in values.items()}
        return {"summary": summary, **flattened}

    def _template(self, kind: str, values: Mapping[str, str]) -> str:
        destination = values.get("destination", "Destination to be confirmed")
        dates = values.get("date", values.get("travel_dates", "Dates to be confirmed"))
        client = values.get("client", values.get("client_name", "Client"))
        requirements = values.get("requirements", "Requirements to be confirmed")
        templates = {
            "itinerary": f"# Itinerary: {destination}\n\n- Dates: {dates}\n- Summary: {values['summary']}\n\n## Schedule\n- Confirm transport, lodging, and local arrangements.",
            "packing_checklist": f"# Packing checklist: {destination}\n\n- [ ] Travel documents\n- [ ] Clothing for {dates}\n- [ ] Medication and personal essentials\n- [ ] Chargers and adapters",
            "client_requirements_summary": f"# Client requirements summary\n\n## Client\n{client}\n\n## Requirements\n{requirements}\n\n## Summary\n{values['summary']}",
            "proposal_draft": f"# Proposal: {client}\n\n## Scope\n{requirements}\n\n## Summary\n{values['summary']}\n\n## Next steps\n- Confirm scope, timeline, and pricing.",
            "invoice_template": f"# Invoice template: {client}\n\n| Item | Description | Amount |\n| --- | --- | --- |\n| 1 | {requirements} | TBD |\n\nSummary: {values['summary']}",
        }
        return templates[kind]

    @staticmethod
    def _entities(event: object | None) -> Iterable[object]:
        entities = DocumentTemplateService._attribute(event, "entities")
        return (
            entities
            if isinstance(entities, Iterable) and not isinstance(entities, str | bytes | Mapping)
            else ()
        )

    @staticmethod
    def _entity(entity: object) -> tuple[str, object, bool]:
        kind = DocumentTemplateService._attribute(entity, "kind")
        value = DocumentTemplateService._attribute(entity, "value")
        sensitive = DocumentTemplateService._attribute(entity, "is_sensitive")
        return (kind.casefold() if isinstance(kind, str) else "", value, sensitive is True)

    @staticmethod
    def _attribute(value: object | None, name: str) -> object | None:
        return value.get(name) if isinstance(value, Mapping) else getattr(value, name, None)

    @staticmethod
    def _text(value: object | None) -> str:
        if isinstance(value, Mapping):
            preferred = next((value[key] for key in ("name", "value", "date", "text") if key in value), value)
            value = preferred if isinstance(preferred, str) else json.dumps(preferred, sort_keys=True)
        return sanitize_untrusted_content(str(value), max_chars=2_000).text if value else ""