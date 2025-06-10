"""Discord Slash and Text Commands"""

import asyncio
import logging
import os
from decimal import Decimal
from typing import Any, Callable, Coroutine

import discord
from discord import app_commands
from discord.ext import commands

from app.application.dto.order_dto import OrderError
from app.application.usecase.account_usecase import AccountUseCase
from app.application.usecase.discord_ui_usecase import DiscordUIUseCase
from app.application.usecase.infinite_buying_usecase import InfiniteBuyingUsecase
from app.application.usecase.order_usecase import OrderUseCase
from app.application.usecase.ticker_usecase import TickerUseCase
from app.domain.constants import DiscordConstants
from app.domain.types import MarketName
from resources.discord.bot import DiscordBot
from resources.discord.ui import MainMenuView

logger = logging.getLogger(__name__)


# --- Slash Commands ---


class SlashCommands(commands.Cog):
    """Slash Commands 처리 클래스"""

    def __init__(self, bot: commands.Bot, ui_usecase: DiscordUIUseCase) -> None:
        self.bot = bot
        self.ui_usecase = ui_usecase

    @app_commands.command(name="menu", description="자동매매 봇 메인 메뉴를 표시합니다")
    async def menu_command(self, interaction: discord.Interaction) -> None:
        """메인 메뉴 Slash Command"""
        try:
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

        embed.add_field(
            name="🔗 유용한 링크",
            value=(
                "[공식 문서](https://example.com/docs)\n"
                "[GitHub](https://github.com/example/ttm)\n"
                "[지원 서버](https://discord.gg/example)"
            ),
            inline=False,
        )

        embed.set_footer(text="TTM Bot • 문의사항은 관리자에게 연락하세요")

        await interaction.response.send_message(embed=embed, ephemeral=True)


# --- Text Commands ---

ADMIN_USER_IDS = {
    int(uid.strip())
    for uid in os.getenv("DISCORD_ADMIN_USER_IDS", "").split(",")
    if uid
}
MAX_TRADE_AMOUNT_KRW = 1_000_000
MAX_TRADE_VOLUME_BTC = 0.01
MIN_INITIAL_BUY_AMOUNT = 5000
MIN_PRICE_DROP_THRESHOLD = -0.5


def _is_admin(user_id: int) -> bool:
    return user_id in ADMIN_USER_IDS


def _format_korean_amount(amount: float) -> str:
    if amount >= 1_0000_0000:
        return f"{amount / 1_0000_0000:,.2f}억"
    if amount >= 1_0000:
        return f"{amount / 1_0000:,.0f}만"
    return f"{amount:,.0f}"


def _format_currency_amount(amount: float, currency: str) -> str:
    if currency == "KRW":
        return f"{amount:,.0f} KRW"
    return f"{Decimal(str(amount)):.8f}".rstrip("0").rstrip(".") + f" {currency}"


def _format_percentage(value: float) -> str:
    return f"{value:+.2f}%"


async def _execute_trade_confirmation(
    ctx: commands.Context[Any],
    embed: discord.Embed,
    confirmation_callback: Callable[[], Coroutine[Any, Any, None]],
) -> None:
    message = await ctx.send(embed=embed)
    await message.add_reaction(DiscordConstants.EMOJI_CONFIRM)
    await message.add_reaction(DiscordConstants.EMOJI_CANCEL)

    def check(reaction: discord.Reaction, user: discord.User) -> bool:
        return (
            user == ctx.author
            and str(reaction.emoji)
            in [DiscordConstants.EMOJI_CONFIRM, DiscordConstants.EMOJI_CANCEL]
            and reaction.message.id == message.id
        )

    try:
        reaction, _ = await ctx.bot.wait_for(
            "reaction_add",
            timeout=DiscordConstants.TRADE_CONFIRMATION_TIMEOUT_SECONDS,
            check=check,
        )
        if str(reaction.emoji) == DiscordConstants.EMOJI_CONFIRM:
            await confirmation_callback()
        else:
            await ctx.send(f"{DiscordConstants.EMOJI_CANCEL} 주문이 취소되었습니다.")
    except asyncio.TimeoutError:
        await ctx.send(
            f"{DiscordConstants.EMOJI_TIMEOUT} 시간 초과로 주문이 취소되었습니다."
        )


def _create_buy_commands(order_usecase: OrderUseCase) -> list[Any]:
    @commands.command(name="매수", aliases=["buy"])
    async def buy_command(
        ctx: commands.Context[Any],
        market: MarketName,
        amount: str,
        price: str | None = None,
    ) -> None:
        if not _is_admin(ctx.author.id):
            await ctx.send(
                f"{DiscordConstants.EMOJI_ERROR} 거래 명령은 관리자만 사용할 수 있습니다."
            )
            return

        try:
            amount_decimal = Decimal(amount)
            price_decimal = Decimal(price) if price else None

            if price_decimal:
                if not (0 < amount_decimal <= MAX_TRADE_VOLUME_BTC):
                    await ctx.send(
                        f"{DiscordConstants.EMOJI_ERROR} BTC 거래량은 0 ~ {MAX_TRADE_VOLUME_BTC} 사이여야 합니다."
                    )
                    return
            else:
                if not (
                    MIN_INITIAL_BUY_AMOUNT <= amount_decimal <= MAX_TRADE_AMOUNT_KRW
                ):
                    await ctx.send(
                        f"{DiscordConstants.EMOJI_ERROR} 주문 금액은 {MIN_INITIAL_BUY_AMOUNT:,} ~ {MAX_TRADE_AMOUNT_KRW:,} KRW 사이여야 합니다."
                    )
                    return
                result = await order_usecase.buy_market(market, amount_decimal)
                if isinstance(result, OrderError):
                    await ctx.send(f"매수 주문 실패: {result.error_message}")
                else:
                    await ctx.send(f"매수 주문 성공: {result.order_uuid}")
        except Exception as e:
            await ctx.send(f"{DiscordConstants.EMOJI_ERROR} 오류 발생: {e}")

    return [buy_command]


def _create_sell_commands(order_usecase: OrderUseCase) -> list[Any]:
    @commands.command(name="매도", aliases=["sell"])
    async def sell_command(
        ctx: commands.Context[Any],
        market: MarketName,
        volume: str,
        price: str | None = None,
    ) -> None:
        pass

    return [sell_command]


def _create_order_commands(order_usecase: OrderUseCase) -> list[Any]:
    @commands.command(name="주문조회", aliases=["order"])
    async def get_order_command(ctx: commands.Context[Any], uuid: str) -> None:
        pass

    @commands.command(name="주문취소", aliases=["cancel"])
    async def cancel_order_command(ctx: commands.Context[Any], uuid: str) -> None:
        pass

    return [get_order_command, cancel_order_command]


def _create_balance_command(
    account_usecase: AccountUseCase, ticker_usecase: TickerUseCase
) -> Any:
    @commands.command(name="잔고", aliases=["balance", "계좌"])
    async def check_balance(ctx: commands.Context[Any]) -> None:
        pass

    return check_balance


def _create_price_command(ticker_usecase: TickerUseCase) -> Any:
    @commands.command(name="시세", aliases=["price", "가격"])
    async def check_price(
        ctx: commands.Context[Any], market: MarketName = "KRW-BTC"
    ) -> None:
        pass

    return check_price


def _create_infinite_buying_commands(
    infinite_buying_usecase: InfiniteBuyingUsecase,
) -> list[Any]:
    @commands.command(name="무한매수시작", aliases=["infinite_start", "무한시작"])
    async def start_infinite_buying_command(
        ctx: commands.Context[Any], market: MarketName, max_rounds: str = "10"
    ) -> None:
        pass

    @commands.command(name="무한매수조회", aliases=["infinite_status", "무한조회"])
    async def check_infinite_buying_status_command(
        ctx: commands.Context[Any], market: MarketName | None = None
    ) -> None:
        pass

    @commands.command(name="무한매수종료", aliases=["infinite_stop", "무한종료"])
    async def stop_infinite_buying_command(
        ctx: commands.Context[Any], market: MarketName, force_sell: str = "false"
    ) -> None:
        pass

    return [
        start_infinite_buying_command,
        check_infinite_buying_status_command,
        stop_infinite_buying_command,
    ]


def _create_help_command() -> Any:
    @commands.command(name="도움말", aliases=["명령어"])
    async def help_command(ctx: commands.Context[Any]) -> None:
        """봇의 모든 명령어와 사용법을 안내합니다."""
        help_text = (
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
        )

        embed = discord.Embed(
            title="📚 TTM Bot 사용법",
            description=help_text,
            color=0x0099FF,
        )

        embed.add_field(
            name="🔗 유용한 링크",
            value=(
                "[공식 문서](https://example.com/docs)\n"
                "[GitHub](https://github.com/example/ttm)\n"
                "[지원 서버](https://discord.gg/example)"
            ),
            inline=False,
        )

        embed.set_footer(text="TTM Bot • 문의사항은 관리자에게 연락하세요")

        await ctx.send(embed=embed)

    return help_command


# --- Setup Function ---


async def setup_commands(
    bot: DiscordBot,
    account_usecase: AccountUseCase,
    ticker_usecase: TickerUseCase,
    order_usecase: OrderUseCase,
    infinite_buying_usecase: InfiniteBuyingUsecase,
    ui_usecase: DiscordUIUseCase,
) -> None:
    """봇에 모든 커맨드를 추가"""
    logger.info("봇에 모든 커맨드를 추가")

    # Slash Commands
    try:
        await bot.add_cog(SlashCommands(bot, ui_usecase))
        synced = await bot.tree.sync()
        logger.info(f"Slash Commands 동기화 완료: {len(synced)}개 명령어")
        for command in synced:
            logger.info(f"  - /{command.name}: {command.description}")
    except Exception as e:
        logger.exception(f"Slash Commands 설정 중 오류: {e}")
        raise

    # Text Commands
    command_creators = [
        *_create_buy_commands(order_usecase),
        *_create_sell_commands(order_usecase),
        *_create_order_commands(order_usecase),
        _create_balance_command(account_usecase, ticker_usecase),
        _create_price_command(ticker_usecase),
        *_create_infinite_buying_commands(infinite_buying_usecase),
        _create_help_command(),
    ]

    for command in command_creators:
        if isinstance(command, commands.Command):
            bot.add_command(command)

    logger.info("Text commands added.")
