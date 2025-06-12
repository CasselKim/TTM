"""Discord UI Components (Embeds, Buttons, Modals, Views)"""

import logging
from typing import TYPE_CHECKING, Any

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
    """매매 실행 모달"""

    def __init__(self, ui_usecase: "DiscordUIUseCase") -> None:
        super().__init__(title="📈 자동매매 실행")
        self.ui_usecase = ui_usecase

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

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            symbol_value = self.symbol.value.upper().strip()
            amount_value = int(self.amount.value.replace(",", ""))
            count_value = int(self.total_count.value)
            interval_value = int(self.interval_hours.value)

            if not symbol_value:
                raise ValueError("코인 심볼을 입력해주세요.")
            if amount_value <= 0:
                raise ValueError("매수 금액은 0보다 커야 합니다.")
            if count_value <= 0:
                raise ValueError("총 횟수는 0보다 커야 합니다.")
            if interval_value <= 0:
                raise ValueError("매수 간격은 0보다 커야 합니다.")

            user_id = str(interaction.user.id)
            trade_data = await self.ui_usecase.execute_trade(
                user_id=user_id,
                symbol=symbol_value,
                amount=amount_value,
                total_count=count_value,
                interval_hours=interval_value,
            )

            embed = await self.ui_usecase.create_trade_complete_embed(trade_data)
            view = TradeCompleteView(self.ui_usecase)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        except ValueError as e:
            embed = discord.Embed(
                title="❌ 입력 오류",
                description=f"입력값을 확인해주세요:\n{str(e)}",
                color=0xFF0000,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
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
                title="❌ 선택 오류",
                description="중단할 DCA를 먼저 선택해주세요.",
                color=0xFF0000,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # 선택된 DCA 정보 찾기
        selected_dca = next(
            (dca for dca in self.dca_list if dca["market"] == self.selected_market),
            None,
        )
        if not selected_dca:
            embed = discord.Embed(
                title="❌ 오류",
                description="선택된 DCA 정보를 찾을 수 없습니다.",
                color=0xFF0000,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # 중단 옵션 선택 화면으로 이동
        embed = discord.Embed(
            title="⚠️ DCA 중단 옵션 선택",
            description=f"**{selected_dca['symbol']}** DCA를 어떻게 중단하시겠습니까?\n\n"
            f"**현재 상태:**\n"
            f"• 진행: {selected_dca['current_round']}/{selected_dca['max_rounds']}회\n"
            f"• 총 투자: {selected_dca['total_investment']:,.0f}원\n"
            f"• 수익률: {selected_dca['profit_rate']:.2f}%\n\n"
            f"**옵션:**\n"
            f"🛑 **중단만 하기**: DCA만 중단하고 코인은 보관\n"
            f"💸 **강제매도**: DCA 중단 후 보유 코인 전량 매도",
            color=0xFF8C00,
        )

        view = DcaStopOptionsView(self.ui_usecase, self.selected_market, selected_dca)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="취소", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        embed = discord.Embed(
            title="❌ 취소됨",
            description="DCA 중단이 취소되었습니다.",
            color=0x808080,
        )
        await interaction.response.edit_message(embed=embed, view=None)


class DcaSelectDropdown(discord.ui.Select[DcaSelectionView]):
    """DCA 선택 드롭다운"""

    def __init__(self, dca_list: list[dict[str, Any]]) -> None:
        options = []
        for dca in dca_list:
            options.append(
                discord.SelectOption(
                    label=dca["display_name"],
                    description=dca["description"],
                    value=dca["market"],
                    emoji="📈",
                )
            )

        super().__init__(
            placeholder="중단할 DCA를 선택하세요...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.view:
            self.view.selected_market = self.values[0]

        # 선택 완료 메시지
        selected_option = next(
            (opt for opt in self.options if opt.value == self.values[0]), None
        )
        if selected_option:
            embed = discord.Embed(
                title="✅ DCA 선택됨",
                description=f"**{selected_option.label}**이(가) 선택되었습니다.\n\n"
                f"{selected_option.description}\n\n"
                f"아래 버튼을 클릭하여 중단 진행하세요.",
                color=0x00FF00,
            )
            await interaction.response.edit_message(embed=embed, view=self.view)


class DcaStopOptionsView(discord.ui.View):
    """DCA 중단 옵션 선택 View"""

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
        await interaction.response.defer()

        # DCA 중단 실행 (강제매도 X)
        result = await self.ui_usecase.stop_selected_dca(
            user_id=str(interaction.user.id), market=self.market, force_sell=False
        )

        # 결과 표시
        view = DcaStopResultView(result)
        embed = view.create_result_embed()
        if interaction.message:
            await interaction.followup.edit_message(
                message_id=interaction.message.id, embed=embed, view=view
            )

    @discord.ui.button(label="강제매도", style=discord.ButtonStyle.danger, emoji="💸")
    async def force_sell(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        await interaction.response.defer()

        # DCA 중단 + 강제매도 실행
        result = await self.ui_usecase.stop_selected_dca(
            user_id=str(interaction.user.id), market=self.market, force_sell=True
        )

        # 결과 표시
        view = DcaStopResultView(result)
        embed = view.create_result_embed()
        if interaction.message:
            await interaction.followup.edit_message(
                message_id=interaction.message.id, embed=embed, view=view
            )

    @discord.ui.button(label="취소", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        embed = discord.Embed(
            title="❌ 취소됨",
            description="DCA 중단이 취소되었습니다.",
            color=0x808080,
        )
        await interaction.response.edit_message(embed=embed, view=None)


class DcaStopResultView(discord.ui.View):
    """DCA 중단 결과 View"""

    def __init__(self, result: dict[str, Any]) -> None:
        super().__init__(timeout=None)
        self.result = result

    def create_result_embed(self) -> discord.Embed:
        """결과 Embed 생성"""
        if self.result.get("success", False):
            title = f"✅ DCA {self.result['action_type']} 완료"
            color = 0x00FF00
            description = (
                f"**{self.result['symbol']}** DCA가 성공적으로 {self.result['action_type']}되었습니다.\n\n"
                f"**완료된 매수:** {self.result['completed_count']}/{self.result['total_count']}회\n"
                f"**총 투자금액:** {self.result['total_invested']:,.0f}원\n"
                f"**최종 수익률:** {self.result['final_profit_rate']:.2f}%\n\n"
                f"**메시지:** {self.result['message']}"
            )
        else:
            title = f"❌ DCA {self.result['action_type']} 실패"
            color = 0xFF0000
            description = (
                f"**{self.result['symbol']}** DCA {self.result['action_type']} 중 오류가 발생했습니다.\n\n"
                f"**오류 메시지:** {self.result['message']}"
            )

        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=now_kst(),
        )

        return embed


class BalanceButton(discord.ui.Button[Any]):
    """잔고 조회 버튼"""

    def __init__(self, ui_usecase: "DiscordUIUseCase") -> None:
        super().__init__(
            label="잔고", style=discord.ButtonStyle.primary, emoji="💰", row=0
        )
        self.ui_usecase = ui_usecase

    async def callback(self, interaction: discord.Interaction) -> None:
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


class DCAStatusButton(discord.ui.Button[Any]):
    """DCA 상태 조회 버튼"""

    def __init__(self, ui_usecase: "DiscordUIUseCase") -> None:
        super().__init__(
            label="DCA 상태", style=discord.ButtonStyle.secondary, emoji="📊", row=0
        )
        self.ui_usecase = ui_usecase

    async def callback(self, interaction: discord.Interaction) -> None:
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


class ProfitButton(discord.ui.Button[Any]):
    """수익률 조회 버튼"""

    def __init__(self, ui_usecase: "DiscordUIUseCase") -> None:
        super().__init__(
            label="수익률", style=discord.ButtonStyle.secondary, emoji="📈", row=0
        )
        self.ui_usecase = ui_usecase

    async def callback(self, interaction: discord.Interaction) -> None:
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


class TradeExecuteButton(discord.ui.Button[Any]):
    """매매 실행 버튼"""

    def __init__(self, ui_usecase: "DiscordUIUseCase") -> None:
        super().__init__(
            label="매매 실행", style=discord.ButtonStyle.success, emoji="▶️", row=1
        )
        self.ui_usecase = ui_usecase

    async def callback(self, interaction: discord.Interaction) -> None:
        modal = TradeModal(self.ui_usecase)
        await interaction.response.send_modal(modal)


class TradeStopButton(discord.ui.Button[Any]):
    """매매 중단 버튼"""

    def __init__(self, ui_usecase: "DiscordUIUseCase") -> None:
        super().__init__(
            label="매매 중단", style=discord.ButtonStyle.danger, emoji="⏹️", row=1
        )
        self.ui_usecase = ui_usecase

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        try:
            # 진행중인 DCA 목록 조회
            user_id = str(interaction.user.id)
            dca_list = await self.ui_usecase.get_active_dca_list(user_id)

            if not dca_list:
                # 진행중인 DCA가 없는 경우
                embed = discord.Embed(
                    title="ℹ️ 진행중인 DCA 없음",
                    description="현재 진행중인 DCA가 없습니다.\n\n"
                    "새로운 DCA를 시작하려면 **매매 실행** 버튼을 클릭하세요.",
                    color=0x808080,
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # DCA 선택 화면 표시
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


class MainMenuView(discord.ui.View):
    """메인 메뉴 Persistent View"""

    def __init__(self, ui_usecase: "DiscordUIUseCase") -> None:
        super().__init__(timeout=None)
        self.ui_usecase = ui_usecase
        self.add_item(BalanceButton(ui_usecase))
        self.add_item(DCAStatusButton(ui_usecase))
        self.add_item(ProfitButton(ui_usecase))
        self.add_item(TradeExecuteButton(ui_usecase))
        self.add_item(TradeStopButton(ui_usecase))
