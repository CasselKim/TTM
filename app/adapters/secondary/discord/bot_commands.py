"""Discord Bot 커맨드 정의"""

from typing import Any

from discord.ext import commands

from app.adapters.secondary.discord.adapter import DiscordAdapter
from app.application.usecase.account_usecase import AccountUseCase
from app.application.usecase.ticker_usecase import TickerUseCase


def _create_balance_command(account_usecase: AccountUseCase) -> Any:
    """잔고 조회 커맨드 생성"""

    @commands.command(name="잔고", aliases=["balance", "계좌"])
    async def check_balance(ctx: commands.Context[Any]) -> None:
        """계좌 잔고를 조회합니다.
        사용법: !잔고
        """
        try:
            result = await account_usecase.get_balance()

            if result.balances:
                message = "💰 **계좌 잔고**\n"

                for balance in result.balances:
                    balance_val = float(balance.balance)
                    locked_val = float(balance.locked)

                    if balance_val > 0 or locked_val > 0:
                        total = balance_val + locked_val
                        message += f"\n**{balance.currency}**\n"
                        message += f"  • 사용 가능: {balance_val:,.8f}\n"
                        message += f"  • 거래 중: {locked_val:,.8f}\n"
                        message += f"  • 총 보유: {total:,.8f}\n"

                        avg_buy_price = float(balance.avg_buy_price)
                        if avg_buy_price > 0:
                            message += f"  • 평균 매수가: {avg_buy_price:,.2f} KRW\n"

                message += (
                    f"\n💵 **총 평가 금액**: {float(result.total_balance_krw):,.0f} KRW"
                )
                await ctx.send(message)
            else:
                await ctx.send("❌ 계좌 정보를 가져올 수 없습니다.")

        except Exception as e:
            await ctx.send(f"❌ 오류가 발생했습니다: {e!s}")

    return check_balance


def _create_price_command(ticker_usecase: TickerUseCase) -> Any:
    """시세 조회 커맨드 생성"""

    @commands.command(name="시세", aliases=["price", "가격"])
    async def check_price(ctx: commands.Context[Any], market: str = "KRW-BTC") -> None:
        """암호화폐 시세를 조회합니다.
        사용법: !시세 [마켓코드]
        예시: !시세 KRW-BTC
        """
        try:
            # 마켓 코드 대문자로 변환
            market = market.upper()

            ticker = await ticker_usecase.get_ticker_price(market)

            if ticker:
                # 가격 변동률 계산
                change_rate = float(ticker.signed_change_rate) * 100
                change_emoji = "📈" if change_rate >= 0 else "📉"
                change_color = "🟢" if change_rate >= 0 else "🔴"

                message = f"{change_emoji} **{market} 시세 정보**\n\n"
                message += f"**현재가**: {float(ticker.trade_price):,.0f} KRW\n"
                message += f"**전일 대비**: {change_color} {float(ticker.signed_change_price):+,.0f} ({change_rate:+.2f}%)\n"
                message += f"**고가**: {float(ticker.high_price):,.0f} KRW\n"
                message += f"**저가**: {float(ticker.low_price):,.0f} KRW\n"
                message += f"**거래량**: {float(ticker.acc_trade_volume_24h):,.4f}\n"
                message += f"**거래대금**: {float(ticker.acc_trade_price_24h):,.0f} KRW"

                await ctx.send(message)
            else:
                await ctx.send(f"❌ {market} 시세 정보를 가져올 수 없습니다.")

        except Exception as e:
            await ctx.send(f"❌ 오류가 발생했습니다: {e!s}")

    return check_price


def _create_help_command() -> Any:
    """도움말 커맨드 생성"""

    @commands.command(name="도움말", aliases=["명령어"])
    async def help_command(ctx: commands.Context[Any]) -> None:
        """사용 가능한 명령어를 표시합니다."""
        message = "📚 **TTM Trading Bot 명령어**\n\n"
        message += "**!잔고** - 계좌 잔고를 조회합니다\n"
        message += "**!시세 [마켓코드]** - 암호화폐 시세를 조회합니다\n"
        message += "  예시: `!시세 KRW-BTC`, `!시세 KRW-ETH`\n"
        message += "**!도움말** - 이 도움말을 표시합니다\n"

        await ctx.send(message)

    return help_command


def setup_bot_commands(
    bot_adapter: DiscordAdapter,
    account_usecase: AccountUseCase,
    ticker_usecase: TickerUseCase,
) -> None:
    """Discord Bot에 커맨드를 등록합니다."""
    # 각 커맨드 생성
    balance_command = _create_balance_command(account_usecase)
    price_command = _create_price_command(ticker_usecase)
    help_command = _create_help_command()

    # 봇에 커맨드 등록
    bot_adapter.add_command(balance_command)
    bot_adapter.add_command(price_command)
    bot_adapter.add_command(help_command)
