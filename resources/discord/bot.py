import logging
from typing import Any, TYPE_CHECKING

import discord
from discord.ext import commands
from discord.ext.commands import Bot

from resources.discord.models import Embed

if TYPE_CHECKING:
    from app.adapters.internal.discord_command import DiscordCommandAdapter

logger = logging.getLogger(__name__)


class DiscordBot(Bot):
    """Discord 봇 클라이언트"""

    def __init__(
        self,
        bot_token: str,
        channel_id: int,
        alert_channel_id: int,
        log_channel_id: int,
        command_prefix: str,
        **options: Any,
    ):
        """
        봇 클라이언트 초기화

        Args:
            bot_token: Discord Bot 토큰
            channel_id: 메시지를 전송할 채널 ID (히스토리 채널)
            alert_channel_id: 알림 전용 채널 ID (에러 알림 등)
            log_channel_id: 로그 전용 채널 ID (디버그 로그 등)
            command_prefix: 명령어 접두사
        """
        # 봇 인텐트 설정
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix=command_prefix, intents=intents, **options)

        self.bot_token = bot_token
        self.channel_id = channel_id
        self.alert_channel_id = alert_channel_id
        self.log_channel_id = log_channel_id

        # 채널들은 on_ready에서 초기화됨 (not null 보장)
        self.history_channel: discord.TextChannel
        self.alert_channel: discord.TextChannel
        self.log_channel: discord.TextChannel

        self._setup_events()

    def _setup_events(self) -> None:
        """봇 이벤트 핸들러 설정"""

        @self.event
        async def on_ready() -> None:
            logger.info(f"Discord 봇이 로그인했습니다: {self.user}")

            history_channel = self.get_channel(self.channel_id)
            if not isinstance(history_channel, discord.TextChannel):
                error_msg = f"히스토리 채널 ID {self.channel_id}를 찾을 수 없거나 텍스트 채널이 아닙니다."
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            self.history_channel = history_channel
            logger.info(f"히스토리 채널 연결됨: {self.history_channel.name}")

            alert_channel = self.get_channel(self.alert_channel_id)
            if not isinstance(alert_channel, discord.TextChannel):
                error_msg = f"알림 채널 ID {self.alert_channel_id}를 찾을 수 없거나 텍스트 채널이 아닙니다."
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            self.alert_channel = alert_channel
            logger.info(f"알림 채널 연결됨: {self.alert_channel.name}")

            log_channel = self.get_channel(self.log_channel_id)
            if not isinstance(log_channel, discord.TextChannel):
                error_msg = f"로그 채널 ID {self.log_channel_id}를 찾을 수 없거나 텍스트 채널이 아닙니다."
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            self.log_channel = log_channel
            logger.info(f"로그 채널 연결됨: {self.log_channel.name}")

        @self.event
        async def on_command_error(
            ctx: commands.Context[Any], error: commands.CommandError
        ) -> None:
            """명령어 에러 처리"""
            if isinstance(error, commands.CommandNotFound):
                await ctx.send("알 수 없는 명령어입니다.")
            else:
                logger.error(f"명령어 처리 중 오류: {error}")
                await ctx.send(f"오류가 발생했습니다: {error}")

    async def setup_commands(self, command_adapter: "DiscordCommandAdapter") -> None:
        """Discord Slash Commands 설정"""
        # Slash Commands (Cog) 추가
        await self.add_cog(command_adapter)
        synced = await self.tree.sync()
        logger.info(f"Slash Commands 동기화 완료: {len(synced)}개 명령어")
        for command in synced:
            logger.info(f"  - /{command.name}: {command.description}")

    async def start_bot(self) -> None:
        """봇 시작"""
        try:
            await self.start(self.bot_token)
        except Exception:
            logger.exception("Discord 봇 시작 중 치명적인 오류 발생")
            raise

    async def send_embed(self, embed: Embed, channel_type: str = "history") -> bool:
        """
        Discord Embed 메시지 전송

        Args:
            embed: 전송할 Embed 객체
            channel_type: 메시지를 보낼 채널 타입 ('history', 'alert', 'log')

        Returns:
            전송 성공 여부
        """
        channel_map = {
            "history": self.history_channel,
            "alert": self.alert_channel,
            "log": self.log_channel,
        }
        target_channel = channel_map.get(channel_type)

        if not target_channel:
            logger.error(f"알 수 없는 채널 타입: {channel_type}")
            return False

        try:
            discord_embed = discord.Embed.from_dict(embed.to_discord_dict())
            await target_channel.send(embed=discord_embed)
            return True
        except Exception:
            logger.exception(f"Discord Embed 메시지 전송 실패 (채널: {channel_type})")
            return False

    async def send_message(self, content: str, channel_type: str = "history") -> bool:
        """
        텍스트 메시지 전송

        Args:
            content: 전송할 메시지 내용
            channel_type: 메시지를 보낼 채널 타입 ('history', 'alert', 'log')

        Returns:
            전송 성공 여부
        """
        channel_map = {
            "history": self.history_channel,
            "alert": self.alert_channel,
            "log": self.log_channel,
        }
        target_channel = channel_map.get(channel_type)

        if not target_channel:
            logger.error(f"알 수 없는 채널 타입: {channel_type}")
            return False

        try:
            await target_channel.send(content)
            return True
        except Exception:
            logger.exception(f"Discord 텍스트 메시지 전송 실패 (채널: {channel_type})")
            return False
