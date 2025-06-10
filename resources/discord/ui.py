"""Discord UI Components (Embeds, Buttons, Modals, Views)"""

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

import discord

if TYPE_CHECKING:
    from app.application.usecase.discord_ui_usecase import DiscordUIUseCase

logger = logging.getLogger(__name__)

# --- Helper Functions ---


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
        timestamp=datetime.now(),
    )


# --- Embeds ---


def create_balance_embed(balance_data: dict[str, Any]) -> discord.Embed:
    """잔고 조회 Embed 생성"""
    embed = discord.Embed(
        title="💰 잔고 조회", color=0x00FF00, timestamp=datetime.now()
    )
    total_value = balance_data.get("total_value", 0)
    embed.add_field(name="📊 총 평가액", value=f"₩ {total_value:,.0f}", inline=True)
    available_cash = balance_data.get("available_cash", 0)
    embed.add_field(name="💵 가용 현금", value=f"₩ {available_cash:,.0f}", inline=True)
    holdings = balance_data.get("holdings", [])
    if holdings:
        holdings_text = ""
        for holding in holdings[:10]:
            symbol = holding.get("symbol", "")
            quantity = holding.get("quantity", 0)
            value = holding.get("value", 0)
            profit_loss = holding.get("profit_loss", 0)
            profit_rate = holding.get("profit_rate", 0)
            profit_emoji = "📈" if profit_loss >= 0 else "📉"
            holdings_text += (
                f"{profit_emoji} **{symbol}**\n"
                f"수량: {quantity:,.8f}\n"
                f"평가액: ₩ {value:,.0f}\n"
                f"손익: {profit_loss:+,.0f} ({profit_rate:+.2f}%)\n\n"
            )
        if len(holdings_text) > 1024:
            holdings_text = holdings_text[:1021] + "..."
        embed.add_field(
            name="🪙 보유 종목",
            value=holdings_text or "보유 종목이 없습니다.",
            inline=False,
        )
    embed.set_footer(text="TTM Bot • 실시간 데이터")
    return embed


def create_dca_status_embed(dca_data: dict[str, Any]) -> discord.Embed:
    """DCA 상태 조회 Embed 생성"""
    embed = discord.Embed(title="📊 DCA 상태", color=0x0099FF, timestamp=datetime.now())
    current_count = dca_data.get("current_count", 0)
    total_count = dca_data.get("total_count", 0)
    progress_rate = (current_count / total_count * 100) if total_count > 0 else 0
    progress_bar = "█" * int(progress_rate / 10) + "░" * (10 - int(progress_rate / 10))
    embed.add_field(
        name="📈 진행률",
        value=f"{progress_bar} {progress_rate:.1f}%\n({current_count}/{total_count}회)",
        inline=False,
    )
    next_buy_time = dca_data.get("next_buy_time")
    if next_buy_time:
        embed.add_field(
            name="⏰ 다음 매수",
            value=f"<t:{int(next_buy_time.timestamp())}:R>",
            inline=True,
        )
    avg_price = dca_data.get("average_price", 0)
    current_price = dca_data.get("current_price", 0)
    embed.add_field(name="💰 평균 매입가", value=f"₩ {avg_price:,.0f}", inline=True)
    embed.add_field(name="📊 현재가", value=f"₩ {current_price:,.0f}", inline=True)
    profit_rate = dca_data.get("profit_rate", 0)
    profit_emoji = "📈" if profit_rate >= 0 else "📉"
    profit_color = "🟢" if profit_rate >= 0 else "🔴"
    embed.add_field(
        name=f"{profit_emoji} 현재 수익률",
        value=f"{profit_color} {profit_rate:+.2f}%",
        inline=True,
    )
    total_invested = dca_data.get("total_invested", 0)
    embed.add_field(
        name="💸 누적 투자액", value=f"₩ {total_invested:,.0f}", inline=True
    )
    recent_trades = dca_data.get("recent_trades", [])
    if recent_trades:
        trades_text = ""
        for trade in recent_trades[:5]:
            trade_time = trade.get("time", "")
            trade_price = trade.get("price", 0)
            trade_amount = trade.get("amount", 0)
            trades_text += (
                f"• {trade_time}: ₩ {trade_price:,.0f} ({trade_amount:,.0f}원)\n"
            )
        embed.add_field(
            name="📝 최근 체결 내역",
            value=trades_text or "체결 내역이 없습니다.",
            inline=False,
        )
    embed.set_footer(text="TTM Bot • 실시간 데이터")
    return embed


def create_profit_embed(profit_data: dict[str, Any]) -> discord.Embed:
    """수익률 조회 Embed 생성"""
    embed = discord.Embed(title="📈 수익률", color=0xFF9900, timestamp=datetime.now())
    total_profit = profit_data.get("total_profit", 0)
    total_profit_rate = profit_data.get("total_profit_rate", 0)
    profit_emoji = "📈" if total_profit >= 0 else "📉"
    profit_color = "🟢" if total_profit >= 0 else "🔴"
    embed.add_field(
        name=f"{profit_emoji} 누적 손익",
        value=f"{profit_color} ₩ {total_profit:+,.0f} ({total_profit_rate:+.2f}%)",
        inline=False,
    )
    periods = [("24h", "24시간"), ("7d", "7일"), ("30d", "30일"), ("ytd", "연초 대비")]
    for period_key, period_name in periods:
        period_data = profit_data.get(period_key, {})
        period_profit = period_data.get("profit", 0)
        period_rate = period_data.get("rate", 0)
        period_emoji = "📈" if period_profit >= 0 else "📉"
        period_color = "🟢" if period_profit >= 0 else "🔴"
        embed.add_field(
            name=f"{period_emoji} {period_name}",
            value=f"{period_color} {period_rate:+.2f}%\n(₩ {period_profit:+,.0f})",
            inline=True,
        )
    top_gainers = profit_data.get("top_gainers", [])
    if top_gainers:
        gainers_text = ""
        for gainer in top_gainers[:3]:
            symbol = gainer.get("symbol", "")
            rate = gainer.get("rate", 0)
            gainers_text += f"📈 {symbol}: +{rate:.2f}%\n"
        embed.add_field(
            name="🏆 Top Gainers", value=gainers_text or "데이터 없음", inline=True
        )
    top_losers = profit_data.get("top_losers", [])
    if top_losers:
        losers_text = ""
        for loser in top_losers[:3]:
            symbol = loser.get("symbol", "")
            rate = loser.get("rate", 0)
            losers_text += f"📉 {symbol}: {rate:.2f}%\n"
        embed.add_field(
            name="📉 Top Losers", value=losers_text or "데이터 없음", inline=True
        )
    embed.set_footer(text="TTM Bot • 실시간 데이터")
    return embed


def create_trade_complete_embed(trade_data: dict[str, Any]) -> discord.Embed:
    """매매 완료 Embed 생성"""
    embed = discord.Embed(
        title="✅ 매매 실행 완료",
        description="자동매매가 성공적으로 시작되었습니다!",
        color=0x00FF00,
        timestamp=datetime.now(),
    )
    symbol = trade_data.get("symbol", "")
    amount = trade_data.get("amount", 0)
    total_count = trade_data.get("total_count", 0)
    interval_hours = trade_data.get("interval_hours", 0)
    embed.add_field(name="🪙 코인", value=symbol, inline=True)
    embed.add_field(name="💰 매수 금액", value=f"₩ {amount:,.0f}", inline=True)
    embed.add_field(name="🔢 총 횟수", value=f"{total_count}회", inline=True)
    embed.add_field(name="⏰ 매수 간격", value=f"{interval_hours}시간", inline=True)
    embed.set_footer(text="TTM Bot • DCA 상태 버튼으로 진행 상황을 확인하세요")
    return embed


def create_trade_stop_embed(stop_data: dict[str, Any]) -> discord.Embed:
    """매매 중단 Embed 생성"""
    embed = discord.Embed(
        title="⛔ 자동매매 중단 완료",
        description="자동매매가 중단되었습니다.",
        color=0xFF0000,
        timestamp=datetime.now(),
    )
    completed_count = stop_data.get("completed_count", 0)
    total_count = stop_data.get("total_count", 0)
    total_invested = stop_data.get("total_invested", 0)
    final_profit_rate = stop_data.get("final_profit_rate", 0)
    embed.add_field(
        name="📊 진행 현황",
        value=f"{completed_count}/{total_count}회 완료",
        inline=True,
    )
    embed.add_field(name="💸 총 투자액", value=f"₩ {total_invested:,.0f}", inline=True)
    profit_emoji = "📈" if final_profit_rate >= 0 else "📉"
    profit_color = "🟢" if final_profit_rate >= 0 else "🔴"
    embed.add_field(
        name=f"{profit_emoji} 최종 수익률",
        value=f"{profit_color} {final_profit_rate:+.2f}%",
        inline=True,
    )
    embed.set_footer(text="TTM Bot • 동일 설정으로 재시작할 수 있습니다")
    return embed


# --- Views (and related Modals/Buttons) ---


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
            amount_value = float(self.amount.value.replace(",", ""))
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

            embed = await self.ui_usecase.create_profit_embed(user_id)
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
        embed = discord.Embed(
            title="⚠️ 매매 중단 확인",
            description="정말로 자동매매를 중단하시겠습니까?\n\n"
            "현재 진행 중인 매매는 중단되고,\n"
            "예약된 매수 주문들이 취소됩니다.",
            color=0xFF0000,
        )
        view = ConfirmationView(ui_usecase=self.ui_usecase)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


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
