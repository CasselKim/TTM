from datetime import datetime
import asyncio
import logging

import discord

from app.domain.constants import DiscordConstants
from app.domain.repositories.notification import NotificationRepository
from common.discord.bot import DiscordBot
from common.discord.models import Embed, EmbedField
from common.utils.timezone import now_kst, to_kst


def _truncate_field_value(
    value: str,
    max_length: int = DiscordConstants.EMBED_FIELD_MAX_LENGTH,
) -> str:
    """Discord embed 필드 값을 최대 길이로 제한"""
    if len(value) <= max_length:
        return value
    return value[: max_length - 3] + "..."


class DiscordNotificationAdapter(NotificationRepository):
    """Discord 알림 어댑터 (아웃바운드 포트)"""

    def __init__(self, bot: "DiscordBot"):
        self.bot = bot

    async def _safe_send_embed(self, embed: Embed, channel: str) -> bool:
        """Embed 전송 시 예외를 처리하고 성공 여부를 반환"""
        try:
            return await self.bot.send_embed(embed, channel)
        except Exception:
            logging.exception("Discord %s 채널 embed 전송 실패", channel)
            return False

    async def _safe_send_dm(self, admin_id: int, embed: discord.Embed) -> bool:
        """관리자에게 DM 전송 (예외 처리 포함)"""
        try:
            user = self.bot.get_user(admin_id) or await self.bot.fetch_user(admin_id)
            if user is None:
                logging.warning("Discord 관리자 ID %s 를 찾을 수 없습니다.", admin_id)
                return False
            await user.send(embed=embed)
            return True
        except Exception:
            logging.exception("Discord 관리자(%s) DM 전송 실패", admin_id)
            return False

    async def _notify_admins(self, embed: discord.Embed) -> bool:
        """관리자들에게 DM으로 알림을 전송하고, 전체 성공 여부 반환"""
        if not DiscordConstants.ADMIN_USER_IDS:
            return True

        # 병렬 전송으로 성능 최적화
        results = await asyncio.gather(
            *[
                self._safe_send_dm(admin_id, embed)
                for admin_id in DiscordConstants.ADMIN_USER_IDS
            ],
            return_exceptions=False,
        )
        return all(results)

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

        executed_kst = to_kst(executed_at)

        embed = Embed(
            title=f"{emoji} {market} {action} 체결",
            description=f"**{market}** 거래가 체결되었습니다.",
            color=color,
            timestamp=executed_kst,
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
                    value=executed_kst.strftime("%Y-%m-%d %H:%M:%S"),
                    inline=True,
                ),
            ],
        )

        # 히스토리 채널 전송
        history_success = await self._safe_send_embed(embed, "history")

        # 관리자 DM 전송
        discord_embed = discord.Embed.from_dict(embed.to_discord_dict())
        dm_success = await self._notify_admins(discord_embed)

        return history_success and dm_success

    async def send_error_notification(
        self, error_type: str, error_message: str, details: str | None = None
    ) -> bool:
        """에러 알림 전송"""
        embed = Embed(
            title=f"⚠️ 에러 발생: {error_type}",
            description=error_message,
            color=DiscordConstants.COLOR_ERROR,
            timestamp=now_kst(),
        )
        if details:
            embed.fields.append(
                EmbedField(
                    name="상세 정보", value=_truncate_field_value(details), inline=False
                )
            )
        return await self._safe_send_embed(embed, "alert")

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
            timestamp=now_kst(),
            fields=[
                EmbedField(name=name, value=_truncate_field_value(value), inline=inline)
                for name, value, inline in fields or []
            ],
        )
        return await self._safe_send_embed(embed, "history")
