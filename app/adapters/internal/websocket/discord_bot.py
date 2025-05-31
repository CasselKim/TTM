"""Discord Bot 커맨드 정의"""

import os
from decimal import Decimal
from typing import Any

import discord
from discord.ext import commands

from app.adapters.external.discord.adapter import DiscordAdapter
from app.application.dto.order_dto import OrderError
from app.application.usecase.account_usecase import AccountUseCase
from app.application.usecase.order_usecase import OrderUseCase
from app.application.usecase.ticker_usecase import TickerUseCase
from app.domain.constants import DiscordConstants

# 관리자 사용자 ID (환경 변수에서 가져옴)
ADMIN_USER_IDS = set()
if admin_ids := os.getenv("DISCORD_ADMIN_USER_IDS"):
    ADMIN_USER_IDS = {int(uid.strip()) for uid in admin_ids.split(",")}

# 거래 제한 상수
MAX_TRADE_AMOUNT_KRW = 1_000_000  # 최대 거래 금액: 100만원
MAX_TRADE_VOLUME_BTC = 0.01  # 최대 BTC 거래량: 0.01 BTC


def _is_admin(user_id: int) -> bool:
    """관리자 권한 검증"""
    return user_id in ADMIN_USER_IDS


def _create_trade_confirmation_embed(
    action: str, market: str, amount_or_volume: str, price: str | None = None
) -> discord.Embed:
    """거래 확인용 Embed 생성"""
    embed = discord.Embed(
        title=f"🔒 {action} 주문 확인",
        description=f"**{market}** {action} 주문을 실행하시겠습니까?",
        color=DiscordConstants.COLOR_WARNING,
    )

    if price:
        # 지정가 주문인 경우
        price_formatted = f"{float(price):,.0f} KRW"

        # 마켓에서 통화 추출하여 적절한 포맷 적용
        if "KRW" in amount_or_volume:
            # 시장가 매수인 경우 (금액)
            clean_amount = amount_or_volume.replace(" KRW", "").replace(",", "")
            amount_formatted = f"{float(clean_amount):,.0f} KRW"
        else:
            # 수량인 경우 (암호화폐)
            target_currency = market.split("-")[1] if "-" in market else "BTC"
            amount_formatted = _format_currency_amount(
                float(amount_or_volume), target_currency
            )

        embed.add_field(name="주문 유형", value="지정가", inline=True)
        embed.add_field(name="가격", value=price_formatted, inline=True)
        embed.add_field(name="수량", value=amount_formatted, inline=True)
    else:
        # 시장가 주문인 경우
        if "KRW" in amount_or_volume:
            clean_amount = amount_or_volume.replace(" KRW", "").replace(",", "")
            amount_formatted = f"{float(clean_amount):,.0f} KRW"
        else:
            target_currency = market.split("-")[1] if "-" in market else "BTC"
            amount_formatted = _format_currency_amount(
                float(amount_or_volume), target_currency
            )

        embed.add_field(name="주문 유형", value="시장가", inline=True)
        embed.add_field(name="금액/수량", value=amount_formatted, inline=True)

    embed.add_field(
        name=f"{DiscordConstants.EMOJI_WARNING} 주의사항",
        value=f"{DiscordConstants.EMOJI_CONFIRM} 또는 {DiscordConstants.EMOJI_CANCEL} 이모지로 응답해주세요.\n{int(DiscordConstants.TRADE_CONFIRMATION_TIMEOUT_SECONDS)}초 내에 응답하지 않으면 취소됩니다.",
        inline=False,
    )

    return embed


def _create_buy_commands(order_usecase: OrderUseCase) -> list[Any]:
    """매수 커맨드들 생성"""

    @commands.command(name="매수", aliases=["buy"])
    async def buy_command(
        ctx: commands.Context[Any], market: str, amount: str, price: str | None = None
    ) -> None:
        """
        암호화폐 매수 주문을 실행합니다.

        사용법:
        !매수 [마켓] [금액] - 시장가 매수
        !매수 [마켓] [수량] [가격] - 지정가 매수

        예시:
        !매수 KRW-BTC 100000 - 10만원어치 BTC 시장가 매수
        !매수 KRW-BTC 0.001 95000000 - 0.001 BTC를 9500만원에 지정가 매수
        """
        # 관리자 권한 확인
        if not _is_admin(ctx.author.id):
            await ctx.send(
                f"{DiscordConstants.EMOJI_ERROR} 거래 명령은 관리자만 사용할 수 있습니다."
            )
            return

        try:
            market = market.upper()

            if price is None:
                # 시장가 매수
                amount_decimal = Decimal(amount)

                # 금액 제한 확인
                if amount_decimal > DiscordConstants.MAX_TRADE_AMOUNT_KRW:
                    await ctx.send(
                        f"{DiscordConstants.EMOJI_ERROR} 최대 거래 금액은 {DiscordConstants.MAX_TRADE_AMOUNT_KRW:,}원입니다."
                    )
                    return

                # 확인 단계
                embed = _create_trade_confirmation_embed(
                    "매수", market, f"{amount_decimal:,.0f} KRW"
                )
                message = await ctx.send(embed=embed)
                await message.add_reaction(DiscordConstants.EMOJI_CONFIRM)
                await message.add_reaction(DiscordConstants.EMOJI_CANCEL)

                def check(reaction: discord.Reaction, user: discord.User) -> bool:
                    return (
                        user == ctx.author
                        and str(reaction.emoji)
                        in [
                            DiscordConstants.EMOJI_CONFIRM,
                            DiscordConstants.EMOJI_CANCEL,
                        ]
                        and reaction.message.id == message.id
                    )

                try:
                    reaction, _ = await ctx.bot.wait_for(
                        "reaction_add",
                        timeout=DiscordConstants.TRADE_CONFIRMATION_TIMEOUT_SECONDS,
                        check=check,
                    )

                    if str(reaction.emoji) == DiscordConstants.EMOJI_CONFIRM:
                        await ctx.send(
                            f"{DiscordConstants.EMOJI_PROCESSING} 시장가 매수 주문을 실행중입니다..."
                        )
                        result = await order_usecase.buy_market(market, amount_decimal)

                        if not isinstance(result, OrderError):
                            await ctx.send(
                                f"{DiscordConstants.EMOJI_SUCCESS} 시장가 매수 주문이 성공적으로 실행되었습니다!\n주문 UUID: `{result.order_uuid}`"
                            )
                        else:
                            await ctx.send(
                                f"{DiscordConstants.EMOJI_ERROR} 매수 주문 실패: {result.error_message}"
                            )
                    else:
                        await ctx.send(
                            f"{DiscordConstants.EMOJI_CANCEL} 매수 주문이 취소되었습니다."
                        )

                except Exception:
                    await ctx.send(
                        f"{DiscordConstants.EMOJI_TIMEOUT} 시간 초과로 매수 주문이 취소되었습니다."
                    )

            else:
                # 지정가 매수
                volume_decimal = Decimal(amount)
                price_decimal = Decimal(price)

                # BTC 거래량 제한 확인 (예시)
                if (
                    market == "KRW-BTC"
                    and volume_decimal > DiscordConstants.MAX_TRADE_VOLUME_BTC
                ):
                    await ctx.send(
                        f"{DiscordConstants.EMOJI_ERROR} 최대 BTC 거래량은 {DiscordConstants.MAX_TRADE_VOLUME_BTC}개입니다."
                    )
                    return

                # 총 거래 금액 확인
                total_amount = volume_decimal * price_decimal
                if total_amount > DiscordConstants.MAX_TRADE_AMOUNT_KRW:
                    await ctx.send(
                        f"{DiscordConstants.EMOJI_ERROR} 총 거래 금액이 최대 한도({DiscordConstants.MAX_TRADE_AMOUNT_KRW:,}원)를 초과합니다."
                    )
                    return

                # 확인 단계
                embed = _create_trade_confirmation_embed(
                    "매수", market, str(volume_decimal), str(price_decimal)
                )
                message = await ctx.send(embed=embed)
                await message.add_reaction(DiscordConstants.EMOJI_CONFIRM)
                await message.add_reaction(DiscordConstants.EMOJI_CANCEL)

                def check(reaction: discord.Reaction, user: discord.User) -> bool:
                    return (
                        user == ctx.author
                        and str(reaction.emoji)
                        in [
                            DiscordConstants.EMOJI_CONFIRM,
                            DiscordConstants.EMOJI_CANCEL,
                        ]
                        and reaction.message.id == message.id
                    )

                try:
                    reaction, _ = await ctx.bot.wait_for(
                        "reaction_add",
                        timeout=DiscordConstants.TRADE_CONFIRMATION_TIMEOUT_SECONDS,
                        check=check,
                    )

                    if str(reaction.emoji) == DiscordConstants.EMOJI_CONFIRM:
                        await ctx.send(
                            f"{DiscordConstants.EMOJI_PROCESSING} 지정가 매수 주문을 실행중입니다..."
                        )
                        limit_result = await order_usecase.buy_limit(
                            market, volume_decimal, price_decimal
                        )

                        if not isinstance(limit_result, OrderError):
                            await ctx.send(
                                f"{DiscordConstants.EMOJI_SUCCESS} 지정가 매수 주문이 성공적으로 실행되었습니다!\n주문 UUID: `{limit_result.order_uuid}`"
                            )
                        else:
                            await ctx.send(
                                f"{DiscordConstants.EMOJI_ERROR} 매수 주문 실패: {limit_result.error_message}"
                            )
                    else:
                        await ctx.send(
                            f"{DiscordConstants.EMOJI_CANCEL} 매수 주문이 취소되었습니다."
                        )

                except Exception:
                    await ctx.send(
                        f"{DiscordConstants.EMOJI_TIMEOUT} 시간 초과로 매수 주문이 취소되었습니다."
                    )

        except ValueError:
            await ctx.send(
                f"{DiscordConstants.EMOJI_ERROR} 올바른 숫자 형식을 입력해주세요."
            )
        except Exception as e:
            await ctx.send(f"{DiscordConstants.EMOJI_ERROR} 오류가 발생했습니다: {e!s}")

    @commands.command(name="매도", aliases=["sell"])
    async def sell_command(
        ctx: commands.Context[Any], market: str, volume: str, price: str | None = None
    ) -> None:
        """
        암호화폐 매도 주문을 실행합니다.

        사용법:
        !매도 [마켓] [수량] - 시장가 매도
        !매도 [마켓] [수량] [가격] - 지정가 매도

        예시:
        !매도 KRW-BTC 0.001 - 0.001 BTC 시장가 매도
        !매도 KRW-BTC 0.001 95000000 - 0.001 BTC를 9500만원에 지정가 매도
        """
        # 관리자 권한 확인
        if not _is_admin(ctx.author.id):
            await ctx.send(
                f"{DiscordConstants.EMOJI_ERROR} 거래 명령은 관리자만 사용할 수 있습니다."
            )
            return

        try:
            market = market.upper()
            volume_decimal = Decimal(volume)

            # BTC 거래량 제한 확인 (예시)
            if (
                market == "KRW-BTC"
                and volume_decimal > DiscordConstants.MAX_TRADE_VOLUME_BTC
            ):
                await ctx.send(
                    f"{DiscordConstants.EMOJI_ERROR} 최대 BTC 거래량은 {DiscordConstants.MAX_TRADE_VOLUME_BTC}개입니다."
                )
                return

            if price is None:
                # 시장가 매도
                embed = _create_trade_confirmation_embed(
                    "매도", market, str(volume_decimal)
                )
                message = await ctx.send(embed=embed)
                await message.add_reaction(DiscordConstants.EMOJI_CONFIRM)
                await message.add_reaction(DiscordConstants.EMOJI_CANCEL)

                def check(reaction: discord.Reaction, user: discord.User) -> bool:
                    return (
                        user == ctx.author
                        and str(reaction.emoji)
                        in [
                            DiscordConstants.EMOJI_CONFIRM,
                            DiscordConstants.EMOJI_CANCEL,
                        ]
                        and reaction.message.id == message.id
                    )

                try:
                    reaction, _ = await ctx.bot.wait_for(
                        "reaction_add",
                        timeout=DiscordConstants.TRADE_CONFIRMATION_TIMEOUT_SECONDS,
                        check=check,
                    )

                    if str(reaction.emoji) == DiscordConstants.EMOJI_CONFIRM:
                        await ctx.send(
                            f"{DiscordConstants.EMOJI_PROCESSING} 시장가 매도 주문을 실행중입니다..."
                        )
                        result = await order_usecase.sell_market(market, volume_decimal)

                        if not isinstance(result, OrderError):
                            await ctx.send(
                                f"{DiscordConstants.EMOJI_SUCCESS} 시장가 매도 주문이 성공적으로 실행되었습니다!\n주문 UUID: `{result.order_uuid}`"
                            )
                        else:
                            await ctx.send(
                                f"{DiscordConstants.EMOJI_ERROR} 매도 주문 실패: {result.error_message}"
                            )
                    else:
                        await ctx.send(
                            f"{DiscordConstants.EMOJI_CANCEL} 매도 주문이 취소되었습니다."
                        )

                except Exception:
                    await ctx.send(
                        f"{DiscordConstants.EMOJI_TIMEOUT} 시간 초과로 매도 주문이 취소되었습니다."
                    )

            else:
                # 지정가 매도
                price_decimal = Decimal(price)

                # 확인 단계
                embed = _create_trade_confirmation_embed(
                    "매도", market, str(volume_decimal), str(price_decimal)
                )
                message = await ctx.send(embed=embed)
                await message.add_reaction(DiscordConstants.EMOJI_CONFIRM)
                await message.add_reaction(DiscordConstants.EMOJI_CANCEL)

                def check(reaction: discord.Reaction, user: discord.User) -> bool:
                    return (
                        user == ctx.author
                        and str(reaction.emoji)
                        in [
                            DiscordConstants.EMOJI_CONFIRM,
                            DiscordConstants.EMOJI_CANCEL,
                        ]
                        and reaction.message.id == message.id
                    )

                try:
                    reaction, _ = await ctx.bot.wait_for(
                        "reaction_add",
                        timeout=DiscordConstants.TRADE_CONFIRMATION_TIMEOUT_SECONDS,
                        check=check,
                    )

                    if str(reaction.emoji) == DiscordConstants.EMOJI_CONFIRM:
                        await ctx.send(
                            f"{DiscordConstants.EMOJI_PROCESSING} 지정가 매도 주문을 실행중입니다..."
                        )
                        limit_result = await order_usecase.sell_limit(
                            market, volume_decimal, price_decimal
                        )

                        if not isinstance(limit_result, OrderError):
                            await ctx.send(
                                f"{DiscordConstants.EMOJI_SUCCESS} 지정가 매도 주문이 성공적으로 실행되었습니다!\n주문 UUID: `{limit_result.order_uuid}`"
                            )
                        else:
                            await ctx.send(
                                f"{DiscordConstants.EMOJI_ERROR} 매도 주문 실패: {limit_result.error_message}"
                            )
                    else:
                        await ctx.send(
                            f"{DiscordConstants.EMOJI_CANCEL} 매도 주문이 취소되었습니다."
                        )

                except Exception:
                    await ctx.send(
                        f"{DiscordConstants.EMOJI_TIMEOUT} 시간 초과로 매도 주문이 취소되었습니다."
                    )

        except ValueError:
            await ctx.send(
                f"{DiscordConstants.EMOJI_ERROR} 올바른 숫자 형식을 입력해주세요."
            )
        except Exception as e:
            await ctx.send(f"{DiscordConstants.EMOJI_ERROR} 오류가 발생했습니다: {e!s}")

    return [buy_command, sell_command]


def _create_order_commands(order_usecase: OrderUseCase) -> list[Any]:
    """주문 관리 커맨드들 생성"""

    @commands.command(name="주문조회", aliases=["order"])
    async def get_order_command(ctx: commands.Context[Any], uuid: str) -> None:
        """
        특정 주문 정보를 조회합니다.

        사용법: !주문조회 [주문UUID]
        예시: !주문조회 abc123-def456-ghi789
        """
        # 관리자 권한 확인
        if not _is_admin(ctx.author.id):
            await ctx.send(
                f"{DiscordConstants.EMOJI_ERROR} 주문 조회는 관리자만 사용할 수 있습니다."
            )
            return

        try:
            result = await order_usecase.get_order(uuid)

            if isinstance(result, dict) and result.get("success"):
                state_emoji = {
                    "wait": "⏳",
                    "watch": "👀",
                    "done": DiscordConstants.EMOJI_SUCCESS,
                    "cancel": DiscordConstants.EMOJI_ERROR,
                }.get(result["state"], "❓")

                side_text = "매수" if result["side"] == "bid" else "매도"
                ord_type_text = {
                    "limit": "지정가",
                    "price": "시장가 매수",
                    "market": "시장가 매도",
                }.get(result["ord_type"], result["ord_type"])

                message = f"{state_emoji} **주문 정보**\n\n"
                message += f"**UUID**: `{result['uuid']}`\n"
                message += f"**마켓**: {result['market']}\n"
                message += f"**주문 유형**: {side_text} ({ord_type_text})\n"
                message += f"**주문 상태**: {result['state']}\n"

                if result["price"]:
                    message += f"**주문 가격**: {float(result['price']):,.0f} KRW\n"
                if result["volume"]:
                    message += f"**주문 수량**: {result['volume']}\n"

                message += f"**미체결 수량**: {result['remaining_volume']}\n"
                message += f"**체결 수량**: {result['executed_volume']}\n"
                message += f"**주문 시간**: {result['created_at']}\n"

                await ctx.send(message)
            else:
                error_msg = (
                    result.error_message
                    if isinstance(result, OrderError)
                    else "알 수 없는 오류"
                )
                await ctx.send(
                    f"{DiscordConstants.EMOJI_ERROR} 주문 조회 실패: {error_msg}"
                )

        except Exception as e:
            await ctx.send(f"{DiscordConstants.EMOJI_ERROR} 오류가 발생했습니다: {e!s}")

    @commands.command(name="주문취소", aliases=["cancel"])
    async def cancel_order_command(ctx: commands.Context[Any], uuid: str) -> None:
        """
        주문을 취소합니다.

        사용법: !주문취소 [주문UUID]
        예시: !주문취소 abc123-def456-ghi789
        """
        # 관리자 권한 확인
        if not _is_admin(ctx.author.id):
            await ctx.send(
                f"{DiscordConstants.EMOJI_ERROR} 주문 취소는 관리자만 사용할 수 있습니다."
            )
            return

        try:
            # 확인 단계
            embed = discord.Embed(
                title="🗑️ 주문 취소 확인",
                description=f"주문 UUID `{uuid}`를 취소하시겠습니까?",
                color=DiscordConstants.COLOR_ERROR,
            )
            embed.add_field(
                name=f"{DiscordConstants.EMOJI_WARNING} 주의사항",
                value=f"{DiscordConstants.EMOJI_CONFIRM} 또는 {DiscordConstants.EMOJI_CANCEL} 이모지로 응답해주세요.\n{int(DiscordConstants.TRADE_CONFIRMATION_TIMEOUT_SECONDS)}초 내에 응답하지 않으면 취소됩니다.",
                inline=False,
            )

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
                    await ctx.send(
                        f"{DiscordConstants.EMOJI_PROCESSING} 주문을 취소하는 중입니다..."
                    )
                    result = await order_usecase.cancel_order(uuid)

                    if isinstance(result, dict) and result.get("success"):
                        await ctx.send(
                            f"{DiscordConstants.EMOJI_SUCCESS} 주문이 성공적으로 취소되었습니다!\n주문 UUID: `{result['uuid']}`"
                        )
                    else:
                        error_msg = (
                            result.error_message
                            if isinstance(result, OrderError)
                            else "알 수 없는 오류"
                        )
                        await ctx.send(
                            f"{DiscordConstants.EMOJI_ERROR} 주문 취소 실패: {error_msg}"
                        )
                else:
                    await ctx.send(
                        f"{DiscordConstants.EMOJI_CANCEL} 주문 취소가 취소되었습니다."
                    )

            except Exception:
                await ctx.send(
                    f"{DiscordConstants.EMOJI_TIMEOUT} 시간 초과로 주문 취소가 취소되었습니다."
                )

        except Exception as e:
            await ctx.send(f"{DiscordConstants.EMOJI_ERROR} 오류가 발생했습니다: {e!s}")

    return [get_order_command, cancel_order_command]


def _format_currency_amount(amount: float, currency: str) -> str:
    """통화 타입에 따라 적절한 포맷으로 숫자를 표시"""
    if currency == "KRW":
        # KRW는 정수로 표시 (소수점 불필요)
        return f"{int(amount):,}"
    else:
        # 암호화폐는 8자리 소수점까지 표시하되, 불필요한 0 제거
        formatted = f"{amount:.8f}".rstrip("0").rstrip(".")
        # 천 단위 구분자 추가 (정수 부분에만)
        parts = formatted.split(".")
        decimal_parts_count = 2  # integer_part, decimal_part
        if len(parts) == decimal_parts_count:
            integer_part = f"{int(parts[0]):,}"
            return f"{integer_part}.{parts[1]}"
        else:
            return f"{int(amount):,}"


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
                        currency = balance.currency

                        message += f"\n**{currency}**\n"
                        message += f"  • 사용 가능: {_format_currency_amount(balance_val, currency)}\n"
                        message += f"  • 거래 중: {_format_currency_amount(locked_val, currency)}\n"
                        message += (
                            f"  • 총 보유: {_format_currency_amount(total, currency)}\n"
                        )

                        avg_buy_price = float(balance.avg_buy_price)
                        if avg_buy_price > 0:
                            message += f"  • 평균 매수가: {_format_currency_amount(avg_buy_price, 'KRW')} KRW\n"

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
                message += f"**전일 대비**: {change_color} {float(ticker.signed_change_price):+,.0f} ({int(change_rate):+}%)\n"
                message += f"**고가**: {float(ticker.high_price):,.0f} KRW\n"
                message += f"**저가**: {float(ticker.low_price):,.0f} KRW\n"
                message += f"**거래량**: {int(float(ticker.acc_trade_volume_24h))}\n"
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

        # 기본 명령어
        message += "**📊 조회 명령어**\n"
        message += "**!잔고** - 계좌 잔고를 조회합니다\n"
        message += "**!시세 [마켓코드]** - 암호화폐 시세를 조회합니다\n"
        message += "  예시: `!시세 KRW-BTC`, `!시세 KRW-ETH`\n\n"

        # 거래 명령어 (관리자만)
        if _is_admin(ctx.author.id):
            message += "**💰 거래 명령어 (관리자 전용)**\n"
            message += "**!매수 [마켓] [금액]** - 시장가 매수\n"
            message += "**!매수 [마켓] [수량] [가격]** - 지정가 매수\n"
            message += "**!매도 [마켓] [수량]** - 시장가 매도\n"
            message += "**!매도 [마켓] [수량] [가격]** - 지정가 매도\n"
            message += "**!주문조회 [UUID]** - 주문 정보 조회\n"
            message += "**!주문취소 [UUID]** - 주문 취소\n\n"

            message += "**⚠️ 거래 제한사항**\n"
            message += (
                f"• 최대 거래 금액: {DiscordConstants.MAX_TRADE_AMOUNT_KRW:,}원\n"
            )
            message += (
                f"• 최대 BTC 거래량: {DiscordConstants.MAX_TRADE_VOLUME_BTC} BTC\n"
            )
            message += "• 모든 거래는 확인 단계를 거칩니다\n\n"

        message += "**!도움말** - 이 도움말을 표시합니다\n"

        await ctx.send(message)

    return help_command


def setup_bot_commands(
    bot_adapter: DiscordAdapter,
    account_usecase: AccountUseCase,
    ticker_usecase: TickerUseCase,
    order_usecase: OrderUseCase,
) -> None:
    """Discord Bot에 커맨드를 등록합니다."""
    # 기존 커맨드들
    balance_command = _create_balance_command(account_usecase)
    price_command = _create_price_command(ticker_usecase)
    help_command = _create_help_command()

    # 새로운 거래 커맨드들
    trade_commands = _create_buy_commands(order_usecase)
    order_commands = _create_order_commands(order_usecase)

    # 봇에 커맨드 등록
    bot_adapter.add_command(balance_command)
    bot_adapter.add_command(price_command)
    bot_adapter.add_command(help_command)

    # 거래 커맨드들 등록
    for command in trade_commands:
        bot_adapter.add_command(command)

    # 주문 관리 커맨드들 등록
    for command in order_commands:
        bot_adapter.add_command(command)
