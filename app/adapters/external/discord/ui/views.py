"""Discord UI Views"""

from typing import Any

import discord

# 동적 import로 순환 참조 방지


class MainMenuView(discord.ui.View):
    """메인 메뉴 Persistent View"""

    def __init__(self) -> None:
        super().__init__(timeout=None)

        # 동적 import로 순환 참조 방지
        from .buttons import (
            BalanceButton,
            DCAStatusButton,
            ProfitButton,
            TradeExecuteButton,
            TradeStopButton,
        )

        # 첫 번째 행: 잔고, DCA 상태, 수익률
        self.add_item(BalanceButton())
        self.add_item(DCAStatusButton())
        self.add_item(ProfitButton())

        # 두 번째 행: 매매 실행, 매매 중단
        self.add_item(TradeExecuteButton())
        self.add_item(TradeStopButton())


class ConfirmationView(discord.ui.View):
    """확인 Dialog View"""

    def __init__(self, *, timeout: float = 60.0) -> None:
        super().__init__(timeout=timeout)
        self.confirmed: bool = False
        self.cancelled: bool = False

    @discord.ui.button(label="중단 확정", style=discord.ButtonStyle.danger, emoji="⛔")
    async def confirm_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        """중단 확정 버튼"""
        self.confirmed = True
        self.stop()

        # 버튼 비활성화
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

        await interaction.response.edit_message(
            content="⛔ 자동매매가 중단되었습니다.", view=self
        )

    @discord.ui.button(label="취소", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        """취소 버튼"""
        self.cancelled = True
        self.stop()

        # 버튼 비활성화
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

        await interaction.response.edit_message(
            content="❌ 중단이 취소되었습니다.", view=self
        )

    async def on_timeout(self) -> None:
        """타임아웃 처리"""
        # 버튼 비활성화
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

        # 메시지가 있는 경우에만 편집 (discord.ui.View에는 message 속성이 있음)
        if hasattr(self, "message") and self.message:
            try:
                await self.message.edit(
                    content="⏰ 시간이 초과되어 취소되었습니다.", view=self
                )
            except discord.NotFound:
                pass  # 메시지가 삭제된 경우 무시
