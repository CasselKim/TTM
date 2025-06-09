from datetime import datetime

from app.domain.constants import DiscordConstants
from app.domain.repositories.notification import NotificationRepository
from resources.discord.models import Embed, EmbedField
from resources.discord.bot import DiscordBot


def _truncate_field_value(value: str, max_length: int = 1024) -> str:
    """Discord embed 필드 값을 최대 길이로 제한"""
    if len(value) <= max_length:
        return value
    return value[: max_length - 3] + "..."


class DiscordNotificationAdapter(NotificationRepository):
    """Discord 알림 어댑터 (아웃바운드 포트)"""

    def __init__(self, bot: "DiscordBot"):
        self.bot = bot

    async def send_trade_notification(
        self,
        market: str,
        side: str,
        price: float,
        volume: float,
        total_price: float,
        fee: float,
        executed_at: datetime,
    ) -> bool:
        """거래 체결 알림 전송"""
        color = (
            DiscordConstants.COLOR_SUCCESS
            if side == "BUY"
            else DiscordConstants.COLOR_ERROR
        )
        emoji = "📈" if side == "BUY" else "📉"
        action = "매수" if side == "BUY" else "매도"

        embed = Embed(
            title=f"{emoji} {market} {action} 체결",
            description=f"**{market}** 거래가 체결되었습니다.",
            color=color,
            timestamp=executed_at,
            fields=[
                EmbedField(name="체결 가격", value=f"{price:,.0f} KRW", inline=True),
                EmbedField(
                    name="체결 수량",
                    value=f"{volume:.8f}".rstrip("0").rstrip("."),
                    inline=True,
                ),
                EmbedField(
                    name="총 거래 금액", value=f"{total_price:,.0f} KRW", inline=True
                ),
                EmbedField(
                    name="수수료",
                    value=f"{fee:.8f}".rstrip("0").rstrip(".") + " KRW",
                    inline=True,
                ),
                EmbedField(name="거래 유형", value=action, inline=True),
                EmbedField(
                    name="체결 시간",
                    value=executed_at.strftime("%Y-%m-%d %H:%M:%S"),
                    inline=True,
                ),
            ],
        )
        return await self.bot.send_embed(embed, "history")

    async def send_error_notification(
        self, error_type: str, error_message: str, details: str | None = None
    ) -> bool:
        """에러 알림 전송"""
        embed = Embed(
            title=f"⚠️ 에러 발생: {error_type}",
            description=error_message,
            color=DiscordConstants.COLOR_ERROR,
            timestamp=datetime.now(),
        )
        if details:
            embed.fields.append(
                EmbedField(
                    name="상세 정보", value=_truncate_field_value(details), inline=False
                )
            )
        return await self.bot.send_embed(embed, "alert")

    async def send_info_notification(
        self,
        title: str,
        message: str,
        fields: list[tuple[str, str, bool]] | None = None,
    ) -> bool:
        """정보 알림 전송"""
        embed = Embed(
            title=f"ℹ️ {title}",
            description=message,
            color=DiscordConstants.COLOR_INFO,
            timestamp=datetime.now(),
            fields=[
                EmbedField(name=name, value=_truncate_field_value(value), inline=inline)
                for name, value, inline in fields or []
            ],
        )
        return await self.bot.send_embed(embed, "history")
