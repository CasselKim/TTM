"""Discord adapter module"""

from typing import Union

from app.adapters.secondary.discord.adapter import DiscordAdapter
from app.adapters.secondary.discord.models import Embed, EmbedField, WebhookMessage

# Discord 어댑터 타입 별칭
DiscordBotAdapter = DiscordAdapter

__all__ = [
    "DiscordAdapter",
    "DiscordBotAdapter",
    "Embed",
    "EmbedField",
    "WebhookMessage",
]

# backward compatibility
DiscordBotAdapterType = DiscordAdapter
