"""Discord UI Components (Embeds, Buttons, Modals, Views)"""

import logging
from typing import TYPE_CHECKING, Any
from decimal import Decimal

import discord

from common.utils.timezone import now_kst

if TYPE_CHECKING:
    from app.application.usecase.discord_ui_usecase import DiscordUIUseCase

logger = logging.getLogger(__name__)


def is_embed_valid(embed: discord.Embed | None) -> bool:
    """embed가 유효한지 검증"""
    if embed is None:
        logger.warning("embed가 None입니다")
        return False

    # title, description, fields 중 하나라도 있으면 유효
    has_title = bool(embed.title and embed.title.strip())
    has_description = bool(embed.description and embed.description.strip())
    has_fields = bool(embed.fields and len(embed.fields) > 0)

    logger.debug(
        f"embed 검증 결과: title='{embed.title}' (valid: {has_title}), "
        f"description='{embed.description}' (valid: {has_description}), "
        f"fields_count={len(embed.fields) if embed.fields else 0} (valid: {has_fields})"
    )

    is_valid = has_title or has_description or has_fields
    if not is_valid:
        logger.warning(
            f"embed가 유효하지 않습니다. "
            f"title: '{embed.title}', description: '{embed.description}', "
            f"fields: {len(embed.fields) if embed.fields else 0}개"
        )

    return is_valid


def create_fallback_embed(error_type: str) -> discord.Embed:
    """embed 생성 실패 시 사용할 기본 embed"""
    return discord.Embed(
        title="❌ 데이터 조회 실패",
        description=f"{error_type} 데이터를 불러올 수 없습니다.\n잠시 후 다시 시도해주세요.",
        color=0xFF0000,
        timestamp=now_kst(),
    )


class TradeCompleteView(discord.ui.View):
    """매매 완료 후 버튼 View"""

    def __init__(self, ui_usecase: "DiscordUIUseCase") -> None:
        super().__init__(timeout=300)
        self.ui_usecase = ui_usecase

    @discord.ui.button(
        label="DCA 상태 보기", style=discord.ButtonStyle.primary, emoji="📊"
    )
    async def view_dca_status(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
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


class TradeModal(discord.ui.Modal):
    """매매 실행 모달 (필수값만 입력)"""

    def __init__(self, ui_usecase: "DiscordUIUseCase") -> None:
        super().__init__(title="📈 자동매매 실행")
        self.ui_usecase = ui_usecase
        self.advanced_data = None  # Advanced 옵션 값 저장용

    symbol: discord.ui.TextInput[Any] = discord.ui.TextInput(
        label="코인 심볼",
        placeholder="예: BTC, ETH, DOGE",
        max_length=10,
        style=discord.TextStyle.short,
    )
    amount: discord.ui.TextInput[Any] = discord.ui.TextInput(
        label="매수 금액 (KRW)",
        placeholder="예: 100000 (10만원)",
        max_length=15,
        style=discord.TextStyle.short,
    )
    total_count: discord.ui.TextInput[Any] = discord.ui.TextInput(
        label="총 매수 횟수",
        placeholder="예: 10",
        max_length=3,
        style=discord.TextStyle.short,
    )
    interval_hours: discord.ui.TextInput[Any] = discord.ui.TextInput(
        label="매수 간격 (시간)",
        placeholder="예: 24 (24시간마다)",
        max_length=3,
        style=discord.TextStyle.short,
    )
    add_buy_multiplier: discord.ui.TextInput[Any] = discord.ui.TextInput(
        label="추가 매수 배수",
        placeholder="예: 1.5",
        max_length=5,
        style=discord.TextStyle.short,
        default="1.5",
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        # advanced 옵션 입력 여부를 묻는 버튼 View를 띄운다
        from discord.ui import View, Button

        class AdvancedOptionView(View):
            def __init__(self, modal: TradeModal, values: dict[str, Any]):
                super().__init__(timeout=60)
                self.modal = modal
                self.values = values

            @discord.ui.button(
                label="고급 옵션 입력", style=discord.ButtonStyle.primary
            )
            async def advanced(
                self, interaction: discord.Interaction, button: Button[Any]
            ) -> None:
                self.stop()
                await interaction.response.send_modal(
                    AdvancedTradeModal(self.modal.ui_usecase, self.values)
                )

            @discord.ui.button(
                label="기본값으로 진행", style=discord.ButtonStyle.secondary
            )
            async def skip(
                self, interaction: discord.Interaction, button: Button[Any]
            ) -> None:
                self.stop()
                # 기본값으로 trade 실행
                await execute_trade_with_advanced(
                    interaction, self.values, None, self.modal.ui_usecase
                )

        # 필수값 파싱
        try:
            symbol_value = self.symbol.value.upper().strip()
            amount_value = int(self.amount.value.replace(",", ""))
            count_value = int(self.total_count.value)
            interval_value = int(self.interval_hours.value)
            multiplier_value = Decimal(self.add_buy_multiplier.value)

            if not symbol_value:
                raise ValueError("코인 심볼을 입력해주세요.")
            if amount_value <= 0:
                raise ValueError("매수 금액은 0보다 커야 합니다.")
            if count_value <= 0:
                raise ValueError("총 횟수는 0보다 커야 합니다.")
            if interval_value <= 0:
                raise ValueError("매수 간격은 0보다 커야 합니다.")
            if multiplier_value <= 0:
                raise ValueError("추가 매수 배수는 0보다 커야 합니다.")
        except Exception as e:
            embed = discord.Embed(
                title="❌ 입력 오류",
                description=f"입력값을 확인해주세요:\n{str(e)}",
                color=0xFF0000,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        values = {
            "symbol": symbol_value,
            "amount": amount_value,
            "total_count": count_value,
            "interval_hours": interval_value,
            "add_buy_multiplier": multiplier_value,
        }
        view = AdvancedOptionView(self, values)
        embed = discord.Embed(
            title="고급 옵션 입력",
            description="고급 옵션(목표 수익률, 추가 매수 트리거 하락률, 강제 손절률)을 입력하시겠습니까?\n\n'고급 옵션 입력'을 선택하면 추가 입력창이 열립니다.\n'기본값으로 진행'을 선택하면 기본값(목표수익률 10%, 하락률 -2.5%, 손절률 -25%)으로 진행됩니다.",
            color=0x00BFFF,
        )
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)


def get_advanced_defaults() -> dict[str, Decimal]:
    return {
        "target_profit_rate": Decimal("0.10"),
        "price_drop_threshold": Decimal("-0.025"),
        "force_stop_loss_rate": Decimal("-0.25"),
    }


class AdvancedTradeModal(discord.ui.Modal):
    """고급 옵션 입력 모달"""

    def __init__(
        self, ui_usecase: "DiscordUIUseCase", base_values: dict[str, Any]
    ) -> None:
        super().__init__(title="⚙️ 고급 옵션 입력")
        self.ui_usecase = ui_usecase
        self.base_values = base_values

    target_profit_rate: discord.ui.TextInput[Any] = discord.ui.TextInput(
        label="목표 수익률 (%)",
        placeholder="예: 10 (10%)",
        max_length=6,
        style=discord.TextStyle.short,
        default="10",
    )
    price_drop_threshold: discord.ui.TextInput[Any] = discord.ui.TextInput(
        label="추가 매수 트리거 하락률 (%)",
        placeholder="예: -2.5 (-2.5%)",
        max_length=6,
        style=discord.TextStyle.short,
        default="-2.5",
    )
    force_stop_loss_rate: discord.ui.TextInput[Any] = discord.ui.TextInput(
        label="강제 손절률 (%)",
        placeholder="예: -25 (-25%)",
        max_length=6,
        style=discord.TextStyle.short,
        default="-25",
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            target_profit_value = Decimal(self.target_profit_rate.value) / Decimal(
                "100"
            )
            price_drop_value = Decimal(self.price_drop_threshold.value) / Decimal("100")
            force_stop_loss_value = Decimal(self.force_stop_loss_rate.value) / Decimal(
                "100"
            )

            if target_profit_value <= 0:
                raise ValueError("목표 수익률은 0보다 커야 합니다.")
            if price_drop_value >= 0:
                raise ValueError("추가 매수 하락률은 0보다 작아야 합니다.")
            if force_stop_loss_value >= 0:
                raise ValueError("강제 손절률은 0보다 작아야 합니다.")
        except Exception as e:
            embed = discord.Embed(
                title="❌ 입력 오류",
                description=f"입력값을 확인해주세요:\n{str(e)}",
                color=0xFF0000,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        advanced = {
            "target_profit_rate": target_profit_value,
            "price_drop_threshold": price_drop_value,
            "force_stop_loss_rate": force_stop_loss_value,
        }
        await execute_trade_with_advanced(
            interaction, self.base_values, advanced, self.ui_usecase
        )


async def execute_trade_with_advanced(
    interaction: discord.Interaction,
    base_values: dict[str, Any],
    advanced: dict[str, Decimal] | None,
    ui_usecase: "DiscordUIUseCase",
) -> None:
    try:
        user_id = str(interaction.user.id)
        if advanced is None:
            advanced = get_advanced_defaults()
        trade_data = await ui_usecase.execute_trade(
            user_id=user_id,
            symbol=base_values["symbol"],
            amount=base_values["amount"],
            total_count=base_values["total_count"],
            interval_hours=base_values["interval_hours"],
            add_buy_multiplier=base_values["add_buy_multiplier"],
            target_profit_rate=advanced["target_profit_rate"],
            price_drop_threshold=advanced["price_drop_threshold"],
            force_stop_loss_rate=advanced["force_stop_loss_rate"],
        )
        embed = await ui_usecase.create_trade_complete_embed(trade_data)
        view = TradeCompleteView(ui_usecase)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    except Exception as e:
        logger.exception(
            f"매매 실행 중 오류 발생 (user_id: {interaction.user.id}): {e}"
        )
        embed = discord.Embed(
            title="❌ 오류 발생",
            description="매매 실행 중 오류가 발생했습니다.\n잠시 후 다시 시도해주세요.",
            color=0xFF0000,
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


class ConfirmationView(discord.ui.View):
    """확인 Dialog View"""

    def __init__(
        self, *, timeout: float = 60.0, ui_usecase: "DiscordUIUseCase"
    ) -> None:
        super().__init__(timeout=timeout)
        self.confirmed: bool = False
        self.cancelled: bool = False
        self.message: discord.Message | None = None
        self.ui_usecase = ui_usecase

    @discord.ui.button(label="중단 확정", style=discord.ButtonStyle.danger, emoji="⛔")
    async def confirm_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        self.confirmed = True
        self.stop()
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        self.message = interaction.message
        await interaction.response.edit_message(
            content="⛔ 자동매매가 중단되었습니다.", view=self
        )
        await self.ui_usecase.stop_trade(str(interaction.user.id))

    @discord.ui.button(label="취소", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        self.cancelled = True
        self.stop()
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        self.message = interaction.message
        await interaction.response.edit_message(
            content="❌ 중단이 취소되었습니다.", view=self
        )

    async def on_timeout(self) -> None:
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        if self.message:
            try:
                await self.message.edit(
                    content="⏰ 시간이 초과되어 취소되었습니다.", view=self
                )
            except discord.NotFound:
                pass


class DcaSelectionView(discord.ui.View):
    """DCA 선택 View"""

    def __init__(
        self, ui_usecase: "DiscordUIUseCase", dca_list: list[dict[str, Any]]
    ) -> None:
        super().__init__(timeout=300)
        self.ui_usecase = ui_usecase
        self.dca_list = dca_list
        self.selected_market: str | None = None

        # 드롭다운 추가
        if dca_list:
            self.add_item(DcaSelectDropdown(dca_list))

    @discord.ui.button(
        label="선택된 DCA 중단", style=discord.ButtonStyle.danger, emoji="⏹️"
    )
    async def proceed_to_stop_options(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        if not self.selected_market:
            embed = discord.Embed(
                title="⚠️ 선택 필요",
                description="중단할 DCA를 먼저 선택해주세요.",
                color=0xFFA500,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # 선택된 DCA 정보 찾기
        selected_dca = None
        for dca in self.dca_list:
            if dca["market"] == self.selected_market:
                selected_dca = dca
                break

        if not selected_dca:
            embed = discord.Embed(
                title="❌ 오류",
                description="선택된 DCA 정보를 찾을 수 없습니다.",
                color=0xFF0000,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # DCA 중단 옵션 화면으로 이동

        embed = discord.Embed(
            title=f"⏹️ {self.selected_market} DCA 중단 방식 선택",
            description=f"**진행 정보:**\n"
            f"• 매수 완료: {selected_dca.get('executed_count', 0)}회 "
            f"/ {selected_dca.get('total_count', 0)}회\n"
            f"• 보유 수량: {selected_dca.get('total_volume', 0):.8f}개\n"
            f"• 매수 총액: {selected_dca.get('total_krw', 0):,.0f} KRW\n\n"
            "**중단 방식을 선택하세요:**",
            color=0xFF8C00,
        )

        view = DcaStopOptionsView(self.ui_usecase, self.selected_market, selected_dca)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="취소", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        embed = discord.Embed(
            title="❌ 취소됨",
            description="DCA 중단이 취소되었습니다.",
            color=0x808080,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class DcaSelectDropdown(discord.ui.Select[DcaSelectionView]):
    """DCA 선택 드롭다운"""

    def __init__(self, dca_list: list[dict[str, Any]]) -> None:
        options = []
        for dca in dca_list:
            market = dca["market"]
            executed = dca.get("executed_count", 0)
            total = dca.get("total_count", 0)
            volume = dca.get("total_volume", 0)

            options.append(
                discord.SelectOption(
                    label=f"{market} DCA",
                    description=f"진행: {executed}/{total}회, 보유: {volume:.4f}개",
                    value=market,
                )
            )

        super().__init__(placeholder="중단할 DCA를 선택하세요...", options=options)

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.view:
            self.view.selected_market = self.values[0]

        embed = discord.Embed(
            title="✅ DCA 선택됨",
            description=f"**{self.values[0]} DCA**가 선택되었습니다.\n\n"
            "**선택된 DCA 중단** 버튼을 클릭하여 계속 진행하세요.",
            color=0x00FF00,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class DcaStopOptionsView(discord.ui.View):
    """DCA 중단 옵션 View"""

    def __init__(
        self, ui_usecase: "DiscordUIUseCase", market: str, dca_info: dict[str, Any]
    ) -> None:
        super().__init__(timeout=300)
        self.ui_usecase = ui_usecase
        self.market = market
        self.dca_info = dca_info

    @discord.ui.button(
        label="중단만 하기", style=discord.ButtonStyle.primary, emoji="🛑"
    )
    async def stop_only(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            user_id = str(interaction.user.id)
            result = await self.ui_usecase.stop_selected_dca(
                user_id, self.market, force_sell=False
            )

            embed = discord.Embed(
                title="🛑 DCA 중단 완료",
                description=f"**{self.market} DCA**가 성공적으로 중단되었습니다.\n\n"
                f"보유하신 코인은 그대로 지갑에 남아있습니다.",
                color=0x00AA00,
            )

            view = DcaStopResultView(result)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        except Exception as e:
            logger.exception(f"DCA 중단 처리 중 오류: {e}")
            embed = discord.Embed(
                title="❌ 중단 실패",
                description="DCA 중단 중 오류가 발생했습니다.\n잠시 후 다시 시도해주세요.",
                color=0xFF0000,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label="강제매도", style=discord.ButtonStyle.danger, emoji="💸")
    async def force_sell(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            user_id = str(interaction.user.id)
            result = await self.ui_usecase.stop_selected_dca(
                user_id, self.market, force_sell=True
            )

            embed = discord.Embed(
                title="💸 DCA 중단 및 매도 완료",
                description=f"**{self.market} DCA**가 중단되고 보유 코인이 전량 매도되었습니다.",
                color=0xFF6600,
            )

            view = DcaStopResultView(result)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        except Exception as e:
            logger.exception(f"DCA 중단 및 매도 처리 중 오류: {e}")
            embed = discord.Embed(
                title="❌ 처리 실패",
                description="DCA 중단 및 매도 중 오류가 발생했습니다.\n잠시 후 다시 시도해주세요.",
                color=0xFF0000,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label="취소", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        embed = discord.Embed(
            title="❌ 취소됨",
            description="DCA 중단이 취소되었습니다.",
            color=0x808080,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class DcaStopResultView(discord.ui.View):
    """DCA 중단 결과 View"""

    def __init__(self, result: dict[str, Any]) -> None:
        super().__init__(timeout=300)
        self.result = result

    def create_result_embed(self) -> discord.Embed:
        """결과 embed 생성"""
        embed = discord.Embed(
            title="📊 DCA 중단 결과",
            color=0x0099FF,
            timestamp=now_kst(),
        )

        if "sell_info" in self.result:
            sell_info = self.result["sell_info"]
            embed.add_field(
                name="💰 매도 정보",
                value=f"매도량: {sell_info.get('volume', 0):.8f}\n"
                f"매도가: {sell_info.get('price', 0):,.0f} KRW\n"
                f"수수료: {sell_info.get('fee', 0):,.0f} KRW\n"
                f"실수령액: {sell_info.get('net_amount', 0):,.0f} KRW",
                inline=False,
            )

        embed.add_field(
            name="📈 최종 수익률",
            value=f"{self.result.get('final_profit_rate', 0):.2f}%",
            inline=True,
        )

        embed.add_field(
            name="💵 총 손익",
            value=f"{self.result.get('total_profit', 0):,.0f} KRW",
            inline=True,
        )

        return embed
