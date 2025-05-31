import asyncio
import logging
from datetime import datetime
from typing import Any

import discord
from discord.ext import commands

from app.domain.constants import DiscordConstants

logger = logging.getLogger(__name__)


class DiscordAdapter:
    """Discord Bot 어댑터"""

    def __init__(
        self,
        bot_token: str,
        channel_id: int,
        command_prefix: str = DiscordConstants.DEFAULT_COMMAND_PREFIX,
    ):
        """
        Discord Bot 어댑터 초기화

        Args:
            bot_token: Discord Bot 토큰
            channel_id: 메시지를 전송할 채널 ID
            command_prefix: 명령어 접두사
        """
        self.bot_token = bot_token
        self.channel_id = channel_id
        self.bot: commands.Bot
        self.channel: discord.TextChannel | None = None
        self._ready = asyncio.Event()

        # 봇 인텐트 설정
        intents = discord.Intents.default()
        intents.message_content = (
            True  # Privileged Intent - Developer Portal에서 활성화 필요
        )
        intents.guilds = True
        intents.guild_messages = True  # 메시지 이벤트 수신 (내용은 제외)

        # 봇 생성
        self.bot = commands.Bot(command_prefix=command_prefix, intents=intents)

        # 이벤트 핸들러 등록
        self._setup_events()

    def _setup_events(self) -> None:
        """봇 이벤트 핸들러 설정"""

        @self.bot.event
        async def on_ready() -> None:
            logger.info(f"Discord 봇이 로그인했습니다: {self.bot.user}")

            # 채널 가져오기
            channel = self.bot.get_channel(self.channel_id)
            if not channel or not isinstance(channel, discord.TextChannel):
                logger.error(f"채널 ID {self.channel_id}를 찾을 수 없습니다.")
            else:
                self.channel = channel
                logger.info(f"채널 연결됨: {self.channel.name}")

            self._ready.set()

        @self.bot.event
        async def on_command_error(
            ctx: commands.Context[Any], error: commands.CommandError
        ) -> None:
            """명령어 에러 처리"""
            if isinstance(error, commands.CommandNotFound):
                await ctx.send("알 수 없는 명령어입니다.")
            else:
                logger.error(f"명령어 처리 중 오류: {error}")

    async def start(self) -> None:
        """봇 시작 (백그라운드에서 실행)"""
        try:
            await self.bot.start(self.bot_token)
        except Exception as e:
            logger.error(f"Discord 봇 시작 실패: {e}")
            raise

    async def close(self) -> None:
        """봇 종료"""
        await self.bot.close()

    async def wait_until_ready(self) -> None:
        """봇이 준비될 때까지 대기"""
        await self._ready.wait()

    async def send_embed(self, embed: discord.Embed) -> bool:
        """Discord Embed 메시지 전송"""
        if not self.channel:
            logger.error("채널이 연결되지 않았습니다.")
            return False

        try:
            await self.channel.send(embed=embed)
        except Exception as e:
            logger.error(f"Discord 메시지 전송 실패: {e}")
            return False
        else:
            return True

    async def send_message(self, content: str) -> bool:
        """텍스트 메시지 전송"""
        if not self.channel:
            logger.error("채널이 연결되지 않았습니다.")
            return False

        try:
            await self.channel.send(content)
        except Exception as e:
            logger.error(f"Discord 메시지 전송 실패: {e}")
            return False
        else:
            return True

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
        """
        거래 체결 알림 전송

        Args:
            market: 마켓 코드 (예: KRW-BTC)
            side: 거래 방향 (BUY/SELL)
            price: 체결 가격
            volume: 체결 수량
            total_price: 총 거래 금액
            fee: 수수료
            executed_at: 체결 시간

        Returns:
            전송 성공 여부
        """
        # 색상 설정
        color = (
            DiscordConstants.COLOR_SUCCESS
            if side == "BUY"
            else DiscordConstants.COLOR_ERROR
        )

        # 이모지 설정
        emoji = "📈" if side == "BUY" else "📉"
        action = "매수" if side == "BUY" else "매도"

        # Discord Embed 생성
        embed = discord.Embed(
            title=f"{emoji} {market} {action} 체결",
            description=f"**{market}** 거래가 체결되었습니다.",
            color=color,
            timestamp=executed_at,
        )

        embed.add_field(name="체결 가격", value=f"{price:,.0f} KRW", inline=True)
        embed.add_field(
            name="체결 수량", value=f"{volume:.8f}".rstrip("0").rstrip("."), inline=True
        )
        embed.add_field(
            name="총 거래 금액", value=f"{total_price:,.0f} KRW", inline=True
        )
        embed.add_field(
            name="수수료",
            value=f"{fee:.8f}".rstrip("0").rstrip(".") + " KRW",
            inline=True,
        )
        embed.add_field(name="거래 유형", value=action, inline=True)
        embed.add_field(
            name="체결 시간",
            value=executed_at.strftime("%Y-%m-%d %H:%M:%S"),
            inline=True,
        )

        return await self.send_embed(embed)

    async def send_error_notification(
        self,
        error_type: str,
        error_message: str,
        details: str | None = None,
    ) -> bool:
        """
        에러 알림 전송

        Args:
            error_type: 에러 유형
            error_message: 에러 메시지
            details: 추가 상세 정보

        Returns:
            전송 성공 여부
        """
        # Discord Embed 생성
        embed = discord.Embed(
            title=f"⚠️ 에러 발생: {error_type}",
            description=error_message,
            color=DiscordConstants.COLOR_ERROR,
            timestamp=datetime.now(),
        )

        if details:
            embed.add_field(name="상세 정보", value=details, inline=False)

        return await self.send_embed(embed)

    async def send_info_notification(
        self,
        title: str,
        message: str,
        fields: list[tuple[str, str, bool]] | None = None,
    ) -> bool:
        """
        정보 알림 전송

        Args:
            title: 제목
            message: 메시지
            fields: 필드 리스트 [(name, value, inline), ...]

        Returns:
            전송 성공 여부
        """
        # Discord Embed 생성
        embed = discord.Embed(
            title=f"i {title}",
            description=message,
            color=DiscordConstants.COLOR_INFO,
            timestamp=datetime.now(),
        )

        if fields:
            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)

        return await self.send_embed(embed)

    def add_command(self, func: commands.Command[Any, ..., Any]) -> None:
        """봇에 커맨드 추가"""
        self.bot.add_command(func)
