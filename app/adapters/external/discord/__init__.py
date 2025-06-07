"""Discord Adapter"""

from app.adapters.external.discord.adapter import DiscordAdapter
from app.adapters.external.discord.debug_logging_handler import (
    DiscordDebugLoggingHandler,
)
from app.adapters.external.discord.logging_handler import DiscordLoggingHandler
from app.adapters.external.discord.models import Embed, EmbedField, WebhookMessage

# Discord 어댑터 타입 별칭
DiscordBotAdapter = DiscordAdapter

__all__ = [
    "DiscordAdapter",
    "DiscordBotAdapter",
    "DiscordLoggingHandler",
    "DiscordDebugLoggingHandler",
    "Embed",
    "EmbedField",
    "WebhookMessage",
]

# backward compatibility
DiscordBotAdapterType = DiscordAdapter
