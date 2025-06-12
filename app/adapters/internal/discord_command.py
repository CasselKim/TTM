import logging

import discord
from discord import app_commands
from discord.ext import commands

from app.application.usecase.account_usecase import AccountUseCase
from app.application.usecase.dca_usecase import DcaUsecase
from app.application.usecase.discord_ui_usecase import DiscordUIUseCase
from app.application.usecase.order_usecase import OrderUseCase
from app.application.usecase.ticker_usecase import TickerUseCase
from common.discord.bot import DiscordBot
from common.discord.ui import (
    TradeModal,
    DcaSelectionView,
    is_embed_valid,
    create_fallback_embed,
)

logger = logging.getLogger(__name__)


class DiscordCommandAdapter(commands.Cog):
    """Discord 명령어 어댑터"""

    def __init__(
        self,
        bot: DiscordBot,
        account_usecase: AccountUseCase,
        ticker_usecase: TickerUseCase,
        order_usecase: OrderUseCase,
        dca_usecase: DcaUsecase,
        ui_usecase: DiscordUIUseCase,
    ) -> None:
        super().__init__()
        self.bot = bot
        self.account_usecase = account_usecase
        self.ticker_usecase = ticker_usecase
        self.order_usecase = order_usecase
        self.dca_usecase = dca_usecase
        self.ui_usecase = ui_usecase

    @app_commands.command(
        name="balance", description="현재 보유 자산 현황을 확인합니다"
    )
    async def balance_command(self, interaction: discord.Interaction) -> None:
        """잔고 조회 Slash Command"""
        await interaction.response.defer(ephemeral=True)
        try:
            user_id = str(interaction.user.id)
            logger.info(f"잔고 조회 시작 (user_id: {user_id})")

            embed = await self.ui_usecase.create_balance_embed(user_id)
            logger.info(f"embed 생성 완료 (user_id: {user_id})")

            if not is_embed_valid(embed):
                logger.warning(f"유효하지 않은 잔고 embed 생성됨 (user_id: {user_id})")
                embed = create_fallback_embed("잔고")

            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(f"잔고 조회 응답 완료 (user_id: {user_id})")
        except Exception as e:
            logger.exception(
                f"잔고 조회 중 오류 발생 (user_id: {interaction.user.id}): {e}"
            )
            embed = discord.Embed(
                title="❌ 오류 발생",
                description="잔고 조회 중 오류가 발생했습니다.\n잠시 후 다시 시도해주세요.",
                color=0xFF0000,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(
        name="dca_status", description="자동매매 진행 상황을 확인합니다"
    )
    async def dca_status_command(self, interaction: discord.Interaction) -> None:
        """DCA 상태 조회 Slash Command"""
        await interaction.response.defer(ephemeral=True)
        try:
            user_id = str(interaction.user.id)
            logger.info(f"DCA 상태 조회 시작 (user_id: {user_id})")

            embed = await self.ui_usecase.create_dca_status_embed(user_id)
            logger.info(f"embed 생성 완료 (user_id: {user_id})")

            if not is_embed_valid(embed):
                logger.warning(
                    f"유효하지 않은 DCA 상태 embed 생성됨 (user_id: {user_id})"
                )
                embed = create_fallback_embed("DCA 상태")

            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(f"DCA 상태 조회 응답 완료 (user_id: {user_id})")
        except Exception as e:
            logger.exception(
                f"DCA 상태 조회 중 오류 발생 (user_id: {interaction.user.id}): {e}"
            )
            embed = discord.Embed(
                title="❌ 오류 발생",
                description="DCA 상태 조회 중 오류가 발생했습니다.\n잠시 후 다시 시도해주세요.",
                color=0xFF0000,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="profit", description="투자 수익률을 분석합니다")
    async def profit_command(self, interaction: discord.Interaction) -> None:
        """수익률 조회 Slash Command"""
        await interaction.response.defer(ephemeral=True)
        try:
            user_id = str(interaction.user.id)
            logger.info(f"수익률 조회 시작 (user_id: {user_id})")

            logger.debug(
                f"ui_usecase.create_profit_embed 호출 시작 (user_id: {user_id})"
            )
            embed = await self.ui_usecase.create_profit_embed(user_id)
            logger.debug(
                f"ui_usecase.create_profit_embed 호출 완료 (user_id: {user_id}), embed is None: {embed is None}"
            )

            logger.info(f"embed 생성 완료 (user_id: {user_id})")

            if not is_embed_valid(embed):
                logger.warning(
                    f"유효하지 않은 수익률 embed 생성됨 (user_id: {user_id})"
                )
                embed = create_fallback_embed("수익률")

            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(f"수익률 조회 응답 완료 (user_id: {user_id})")
        except Exception as e:
            logger.exception(
                f"수익률 조회 중 오류 발생 (user_id: {interaction.user.id}): {e}"
            )
            embed = discord.Embed(
                title="❌ 오류 발생",
                description="수익률 조회 중 오류가 발생했습니다.\n잠시 후 다시 시도해주세요.",
                color=0xFF0000,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(
        name="trade_start", description="새로운 자동매매를 시작합니다"
    )
    async def trade_execute_command(self, interaction: discord.Interaction) -> None:
        """매매 실행 Slash Command"""
        try:
            modal = TradeModal(self.ui_usecase)
            await interaction.response.send_modal(modal)
            logger.info(f"매매 실행 모달 표시 완료 (user_id: {interaction.user.id})")
        except Exception as e:
            logger.exception(
                f"매매 실행 모달 표시 중 오류 발생 (user_id: {interaction.user.id}): {e}"
            )
            embed = discord.Embed(
                title="❌ 오류 발생",
                description="매매 실행 화면을 불러오는 중 오류가 발생했습니다.\n잠시 후 다시 시도해주세요.",
                color=0xFF0000,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="trade_stop", description="진행 중인 자동매매를 중단합니다"
    )
    async def trade_stop_command(self, interaction: discord.Interaction) -> None:
        """매매 중단 Slash Command"""
        await interaction.response.defer(ephemeral=True)

        try:
            user_id = str(interaction.user.id)
            dca_list = await self.ui_usecase.get_active_dca_list(user_id)

            if not dca_list:
                embed = discord.Embed(
                    title="ℹ️ 진행중인 DCA 없음",
                    description="현재 진행중인 DCA가 없습니다.\n\n"
                    "새로운 DCA를 시작하려면 `/trade_start` 커맨드를 사용하세요.",
                    color=0x808080,
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            embed = discord.Embed(
                title="⏹️ DCA 중단 선택",
                description=f"**{len(dca_list)}개의 진행중인 DCA**가 있습니다.\n\n"
                "중단할 DCA를 선택해주세요:\n\n"
                "• 🛑 **중단만 하기**: DCA만 중단하고 코인은 보관\n"
                "• 💸 **강제매도**: DCA 중단 후 보유 코인 전량 매도",
                color=0xFF8C00,
            )

            view = DcaSelectionView(self.ui_usecase, dca_list)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            logger.info(
                f"DCA 중단 화면 표시 완료 (user_id: {user_id}, DCA 개수: {len(dca_list)})"
            )

        except Exception as e:
            logger.exception(
                f"DCA 중단 화면 표시 중 오류 (user_id: {interaction.user.id}): {e}"
            )
            embed = discord.Embed(
                title="❌ 오류 발생",
                description="DCA 목록을 불러오는 중 오류가 발생했습니다.\n잠시 후 다시 시도해주세요.",
                color=0xFF0000,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
