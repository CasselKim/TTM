import logging
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

from app.application.usecase.account_usecase import AccountUseCase
from app.application.usecase.dca_usecase import DcaUsecase
from app.application.usecase.discord_ui_usecase import DiscordUIUseCase
from app.application.usecase.order_usecase import OrderUseCase
from app.application.usecase.ticker_usecase import TickerUseCase

logger = logging.getLogger(__name__)


class DiscordCommandAdapter(commands.Cog):
    """Discord 명령어 어댑터"""

    def __init__(
        self,
        bot: Any,
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
        self.logger = logger

    @app_commands.command(name="menu", description="자동매매 봇 메인 메뉴를 표시합니다")
    async def menu_command(self, interaction: discord.Interaction) -> None:
        """메인 메뉴 Slash Command"""
        try:
            from resources.discord.ui import MainMenuView

            embed = discord.Embed(
                title="🤖 TTM 자동매매 봇",
                description=(
                    "**자동매매 봇에 오신 것을 환영합니다!**\n\n"
                    "아래 버튼들을 클릭하여 다양한 기능을 이용하세요:\n\n"
                    "💰 **잔고**: 현재 보유 자산 현황 확인\n"
                    "📊 **DCA 상태**: 자동매매 진행 상황 확인\n"
                    "📈 **수익률**: 투자 수익률 분석\n"
                    "▶️ **매매 실행**: 새로운 자동매매 시작\n"
                    "⏹️ **매매 중단**: 진행 중인 자동매매 중단\n\n"
                    "모든 개인 정보는 본인만 볼 수 있도록 보호됩니다."
                ),
                color=0x0099FF,
            )

            embed.set_thumbnail(
                url="https://via.placeholder.com/150x150/0099ff/ffffff?text=TTM"
            )
            embed.set_footer(
                text="TTM Bot v1.0 • 안전한 자동매매 솔루션",
                icon_url="https://via.placeholder.com/32x32/0099ff/ffffff?text=T",
            )

            view = MainMenuView(self.ui_usecase)
            await interaction.response.send_message(embed=embed, view=view)

            logger.info(
                f"메인 메뉴가 {interaction.user.display_name}({interaction.user.id})에 의해 호출됨"
            )

        except Exception as e:
            logger.exception(f"메인 메뉴 명령어 처리 중 오류: {e}")

            error_embed = discord.Embed(
                title="❌ 오류 발생",
                description="메인 메뉴를 불러오는 중 오류가 발생했습니다.\n"
                "잠시 후 다시 시도해주세요.",
                color=0xFF0000,
            )

            if interaction.response.is_done():
                await interaction.followup.send(embed=error_embed, ephemeral=True)
            else:
                await interaction.response.send_message(
                    embed=error_embed, ephemeral=True
                )

    @app_commands.command(name="ping", description="봇의 응답 속도를 확인합니다")
    async def ping_command(self, interaction: discord.Interaction) -> None:
        """Ping 명령어"""
        latency = round(self.bot.latency * 1000)

        embed = discord.Embed(
            title="🏓 Pong!", description=f"응답 속도: {latency}ms", color=0x00FF00
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="help", description="봇 사용법을 확인합니다")
    async def help_command(self, interaction: discord.Interaction) -> None:
        """도움말 명령어"""
        embed = discord.Embed(
            title="📚 TTM Bot 사용법",
            description=(
                "**주요 명령어:**\n"
                "• `/menu` - 메인 메뉴 표시\n"
                "• `/ping` - 봇 응답 속도 확인\n"
                "• `/help` - 이 도움말 표시\n\n"
                "**메인 기능:**\n"
                "• **잔고 조회**: 현재 보유 자산과 수익률 확인\n"
                "• **DCA 상태**: 자동매매 진행 상황과 다음 매수 시간\n"
                "• **수익률 분석**: 기간별 수익률과 상위/하위 종목\n"
                "• **매매 실행**: 새로운 자동매매 설정 및 시작\n"
                "• **매매 중단**: 진행 중인 자동매매 안전하게 중단\n\n"
                "**보안:**\n"
                "• 모든 개인 정보는 에페메랄 메시지로 보호\n"
                "• 본인만 볼 수 있는 개인화된 응답\n"
                "• 안전한 거래 확인 절차"
            ),
            color=0x0099FF,
        )

        embed.set_footer(text="TTM Bot • 문의사항은 관리자에게 연락하세요")

        await interaction.response.send_message(embed=embed, ephemeral=True)
