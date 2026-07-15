from copy import deepcopy

EVENT = {
    "id": "evt_bengaluru_001",
    "source": "gmail",
    "life_event": "Travel.Booked",
    "title": "Trip to Bengaluru detected",
    "occurred_at": "2026-07-15T09:30:00+05:30",
    "facts": {
        "airline": "IndiGo",
        "flight_number": "6E-123",
        "pnr": "••••X9",
        "departure": "Mumbai",
        "destination": "Bengaluru",
        "departure_time": "2026-07-19T08:10:00+05:30",
    },
    "trust_level": "external",
    "confidence": 0.97,
}

PLAN = {
    "id": "plan_bengaluru_001",
    "event_id": EVENT["id"],
    "objective": "Prepare Bengaluru trip",
    "mode": "safe_actions",
    "services": ["Gmail", "Calendar", "Drive", "Weather", "Telegram"],
    "actions": [
        {
            "id": "act_ticket",
            "label": "Ticket saved to Travel/2026/Bengaluru",
            "risk": "green",
            "status": "verified",
            "why": "The travel standing order saves travel documents.",
        },
        {
            "id": "act_calendar",
            "label": "Calendar and airport reminders created",
            "risk": "green",
            "status": "verified",
            "why": "Safe travel preparation is permitted automatically.",
        },
        {
            "id": "act_weather",
            "label": "Bengaluru weather checked; packing list generated",
            "risk": "green",
            "status": "verified",
            "why": "Weather supports the requested packing checklist.",
        },
        {
            "id": "act_family",
            "label": "Family itinerary update",
            "risk": "yellow",
            "status": "awaiting_approval",
            "why": "Sending an external message needs your approval.",
        },
    ],
    "timeline": [
        "09:30 Flight email detected",
        "09:30 Trip details extracted",
        "09:31 Calendar event created",
        "09:31 Ticket saved",
        "09:31 Weather checked",
        "09:32 Family message awaiting approval",
    ],
}

STANDING_ORDERS = [
    {
        "id": "rule_travel",
        "name": "Travel Autopilot",
        "instruction": "Whenever I book travel, prepare my itinerary and remind me about documents.",
        "enabled": True,
        "autonomy_level": 2,
    }
]
AUTONOMY = {
    "level": 2,
    "domains": {
        "calendar": "automatic",
        "files": "automatic",
        "drafting": "automatic",
        "messaging": "ask every time",
        "finance": "never automatic",
    },
}


def snapshot() -> dict:
    return {
        "event": deepcopy(EVENT),
        "plan": deepcopy(PLAN),
        "standing_orders": deepcopy(STANDING_ORDERS),
        "autonomy": deepcopy(AUTONOMY),
    }
