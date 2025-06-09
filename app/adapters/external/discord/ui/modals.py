"""Discord UI Modals"""

from typing import Any

import discord


class TradeModal(discord.ui.Modal):
    """매매 실행 모달"""

    def __init__(self) -> None:
        super().__init__(title="📈 자동매매 실행")

    # 코인 심볼 입력
    symbol: discord.ui.TextInput[Any] = discord.ui.TextInput(
        label="코인 심볼",
        placeholder="예: BTC, ETH, DOGE",
        max_length=10,
        style=discord.TextStyle.short,
    )

    # 매수 금액 입력
    amount: discord.ui.TextInput[Any] = discord.ui.TextInput(
        label="매수 금액 (KRW)",
        placeholder="예: 100000 (10만원)",
        max_length=15,
        style=discord.TextStyle.short,
    )

    # 총 횟수 입력
    total_count: discord.ui.TextInput[Any] = discord.ui.TextInput(
        label="총 매수 횟수",
        placeholder="예: 10",
        max_length=3,
        style=discord.TextStyle.short,
    )

    # 매수 간격 입력
    interval_hours: discord.ui.TextInput[Any] = discord.ui.TextInput(
        label="매수 간격 (시간)",
        placeholder="예: 24 (24시간마다)",
        max_length=3,
        style=discord.TextStyle.short,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """모달 제출 처리"""
        await interaction.response.defer(ephemeral=True)

        # 입력값 검증
        try:
            symbol_value = self.symbol.value.upper().strip()
            amount_value = float(self.amount.value.replace(",", ""))
            count_value = int(self.total_count.value)
            interval_value = int(self.interval_hours.value)

            # 기본 검증
            if not symbol_value:
                raise ValueError("코인 심볼을 입력해주세요.")

            if amount_value <= 0:
                raise ValueError("매수 금액은 0보다 커야 합니다.")

            if count_value <= 0:
                raise ValueError("총 횟수는 0보다 커야 합니다.")

            if interval_value <= 0:
                raise ValueError("매수 간격은 0보다 커야 합니다.")

            # TODO: DiscordUIUseCase를 통해 매매 실행 처리

            # 성공 응답
            embed = discord.Embed(
                title="✅ 매매 실행 완료",
                description=f"자동매매가 시작되었습니다!\n\n"
                f"**코인**: {symbol_value}\n"
                f"**매수 금액**: {amount_value:,.0f} KRW\n"
                f"**총 횟수**: {count_value}회\n"
                f"**매수 간격**: {interval_value}시간",
                color=0x00FF00,
            )

            # DCA 상태 보기 버튼 추가
            view = TradeCompleteView()
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)

        except ValueError as e:
            # 입력값 오류 처리
            embed = discord.Embed(
                title="❌ 입력 오류",
                description=f"입력값을 확인해주세요:\n{str(e)}",
                color=0xFF0000,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception:
            # 기타 오류 처리
            embed = discord.Embed(
                title="❌ 오류 발생",
                description="매매 실행 중 오류가 발생했습니다.\n"
                "잠시 후 다시 시도해주세요.",
                color=0xFF0000,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    async def on_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        """모달 오류 처리"""
        embed = discord.Embed(
            title="❌ 시스템 오류",
            description="예기치 못한 오류가 발생했습니다.",
            color=0xFF0000,
        )

        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)


class TradeCompleteView(discord.ui.View):
    """매매 완료 후 버튼 View"""

    def __init__(self) -> None:
        super().__init__(timeout=300)  # 5분 타임아웃

    @discord.ui.button(
        label="DCA 상태 보기", style=discord.ButtonStyle.primary, emoji="📊"
    )
    async def view_dca_status(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        """DCA 상태 보기 버튼"""
        await interaction.response.defer(ephemeral=True)

        # TODO: DCA 상태 조회 기능 구현
        embed = discord.Embed(
            title="📊 DCA 상태",
            description="DCA 상태 조회 기능을 구현 중입니다.",
            color=0x0099FF,
        )

        await interaction.followup.send(embed=embed, ephemeral=True)
