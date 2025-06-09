import asyncio
import logging
import traceback
from datetime import datetime
from typing import TYPE_CHECKING

from resources.discord.models import Embed, EmbedField
from resources.discord.bot import DiscordBot

if TYPE_CHECKING:
    from resources.discord.bot import DiscordBot


# --- DiscordLoggingHandler (Error Logs) ---


class DiscordLoggingHandler(logging.Handler):
    """Discord로 에러 로그를 전송하는 로깅 핸들러"""

    def __init__(self, discord_bot: "DiscordBot", level: int = logging.ERROR):
        super().__init__(level)
        self.discord_bot = discord_bot

    def emit(self, record: logging.LogRecord) -> None:
        try:
            if asyncio.get_running_loop().is_running():
                asyncio.create_task(self._send_to_discord(record))
        except RuntimeError:
            pass
        except Exception:
            self.handleError(record)

    async def _send_to_discord(self, record: logging.LogRecord) -> None:
        try:
            await self.discord_bot.wait_until_ready()

            details = None
            if record.exc_info:
                details = "".join(traceback.format_exception(*record.exc_info))

            embed = Embed(
                title=f"⚠️ {record.levelname}: {record.name}",
                description=record.getMessage(),
                color=0xFF0000,
                timestamp=datetime.fromtimestamp(record.created),
            )
            if details:
                truncated_details = (
                    details[:1000] + "..." if len(details) > 1024 else details
                )
                embed.fields.append(
                    EmbedField(
                        name="Traceback",
                        value=f"```p\n{truncated_details}\n```",
                        inline=False,
                    )
                )

            await self.discord_bot.send_embed(embed, channel_type="alert")
        except Exception:
            print("--- Discord Log Send Failed ---")
            traceback.print_exc()
            print("--- End of Log ---")


# --- DiscordDebugLoggingHandler (Debug Logs) ---

LEVEL_MAP = {
    logging.DEBUG: ("🐛", 0x7289DA),
    logging.INFO: ("ℹ️", 0x5865F2),
    logging.WARNING: ("⚠️", 0xFEE75C),
    logging.ERROR: ("❌", 0xED4245),
    logging.CRITICAL: ("🚨", 0x8B0000),
}


class DiscordDebugLoggingHandler(logging.Handler):
    """Discord로 디버그 로그를 전송하는 로깅 핸들러"""

    def __init__(self, discord_bot: "DiscordBot", level: int = logging.DEBUG):
        super().__init__(level)
        self.discord_bot = discord_bot

    def emit(self, record: logging.LogRecord) -> None:
        try:
            if asyncio.get_running_loop().is_running():
                asyncio.create_task(self._send_to_discord(record))
        except RuntimeError:
            pass
        except Exception:
            self.handleError(record)

    async def _send_to_discord(self, record: logging.LogRecord) -> None:
        try:
            await self.discord_bot.wait_until_ready()

            emoji, color = LEVEL_MAP.get(record.levelno, ("📝", 0x99AAB5))

            description = record.getMessage()
            if record.name != "root":
                description = f"**[{record.name}]** {description}"

            embed = Embed(
                title=f"{emoji} {record.levelname}",
                description=description,
                color=color,
                timestamp=datetime.fromtimestamp(record.created),
            )

            details = None
            if record.exc_info:
                details = "".join(traceback.format_exception(*record.exc_info))

            if details:
                truncated_details = (
                    details[:1000] + "..." if len(details) > 1024 else details
                )
                embed.fields.append(
                    EmbedField(
                        name="Traceback",
                        value=f"```py\n{truncated_details}\n```",
                        inline=False,
                    )
                )

            await self.discord_bot.send_embed(embed, channel_type="log")
        except Exception:
            print("--- Discord Debug Log Send Failed ---")
            traceback.print_exc()
            print("--- End of Log ---")
