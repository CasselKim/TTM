"""Discord UI Buttons"""

from typing import Any, TYPE_CHECKING

import discord

if TYPE_CHECKING:
    pass


class BalanceButton(discord.ui.Button[Any]):
    """잔고 조회 버튼"""

    def __init__(self) -> None:
        super().__init__(
            label="잔고", style=discord.ButtonStyle.primary, emoji="💰", row=0
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        """버튼 클릭 처리"""
        await interaction.response.defer(ephemeral=True)

        # TODO: DiscordUIUseCase를 통해 잔고 조회 처리
        embed = discord.Embed(
            title="💰 잔고 조회",
            description="잔고 조회 기능을 구현 중입니다.",
            color=0x00FF00,
        )

        await interaction.followup.send(embed=embed, ephemeral=True)


class DCAStatusButton(discord.ui.Button[Any]):
    """DCA 상태 조회 버튼"""

    def __init__(self) -> None:
        super().__init__(
            label="DCA 상태", style=discord.ButtonStyle.secondary, emoji="📊", row=0
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        """버튼 클릭 처리"""
        await interaction.response.defer(ephemeral=True)

        # TODO: DiscordUIUseCase를 통해 DCA 상태 조회 처리
        embed = discord.Embed(
            title="📊 DCA 상태",
            description="DCA 상태 조회 기능을 구현 중입니다.",
            color=0x0099FF,
        )

        await interaction.followup.send(embed=embed, ephemeral=True)


class ProfitButton(discord.ui.Button[Any]):
    """수익률 조회 버튼"""

    def __init__(self) -> None:
        super().__init__(
            label="수익률", style=discord.ButtonStyle.secondary, emoji="📈", row=0
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        """버튼 클릭 처리"""
        await interaction.response.defer(ephemeral=True)

        # TODO: DiscordUIUseCase를 통해 수익률 조회 처리
        embed = discord.Embed(
            title="📈 수익률",
            description="수익률 조회 기능을 구현 중입니다.",
            color=0xFF9900,
        )

        await interaction.followup.send(embed=embed, ephemeral=True)


class TradeExecuteButton(discord.ui.Button[Any]):
    """매매 실행 버튼"""

    def __init__(self) -> None:
        super().__init__(
            label="매매 실행", style=discord.ButtonStyle.success, emoji="▶️", row=1
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        """버튼 클릭 처리"""
        from .modals import TradeModal

        modal = TradeModal()
        await interaction.response.send_modal(modal)


class TradeStopButton(discord.ui.Button[Any]):
    """매매 중단 버튼"""

    def __init__(self) -> None:
        super().__init__(
            label="매매 중단", style=discord.ButtonStyle.danger, emoji="⏹️", row=1
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        """버튼 클릭 처리"""
        from .views import ConfirmationView

        embed = discord.Embed(
            title="⚠️ 매매 중단 확인",
            description="정말로 자동매매를 중단하시겠습니까?\n\n"
            "현재 진행 중인 매매는 중단되고,\n"
            "예약된 매수 주문들이 취소됩니다.",
            color=0xFF0000,
        )

        view = ConfirmationView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
