"""Discord Bot 커맨드 정의"""

import os
from decimal import Decimal
from typing import Any

import discord
from discord.ext import commands

from app.adapters.external.discord.adapter import DiscordAdapter
from app.adapters.internal.websocket.image_generator import (
    CryptoData,
    create_balance_image,
    create_infinite_buying_image,
)
from app.application.dto.order_dto import OrderError
from app.application.usecase.account_usecase import AccountUseCase
from app.application.usecase.infinite_buying_usecase import InfiniteBuyingUsecase
from app.application.usecase.order_usecase import OrderUseCase
from app.application.usecase.ticker_usecase import TickerUseCase
from app.domain.constants import DiscordConstants
from app.domain.types import (
    InfiniteBuyingStatus,
    MarketName,
)


# 관리자 사용자 ID (환경 변수에서 가져옴)
ADMIN_USER_IDS = set()
if admin_ids := os.getenv("DISCORD_ADMIN_USER_IDS"):
    ADMIN_USER_IDS = {int(uid.strip()) for uid in admin_ids.split(",")}

# 거래 제한 상수
MAX_TRADE_AMOUNT_KRW = 1_000_000  # 최대 거래 금액: 100만원
MAX_TRADE_VOLUME_BTC = 0.01  # 최대 BTC 거래량: 0.01 BTC

# 무한매수법 상수
MIN_INITIAL_BUY_AMOUNT = 5000  # 최소 초기 매수 금액
MIN_PRICE_DROP_THRESHOLD = -0.5  # 최소 하락 기준 (-50%)


def _is_admin(user_id: int) -> bool:
    """관리자 권한 검증"""
    return user_id in ADMIN_USER_IDS


def _create_trade_confirmation_embed(
    action: str, market: MarketName, amount_or_volume: str, price: str | None = None
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


async def _execute_market_buy(
    ctx: commands.Context[Any],
    order_usecase: OrderUseCase,
    market: MarketName,
    amount_decimal: Decimal,
) -> None:
    """시장가 매수 실행"""
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
                f"{DiscordConstants.EMOJI_PROCESSING} 시장가 매수 주문을 "
                "실행중입니다..."
            )
            result = await order_usecase.buy_market(market, amount_decimal)

            if not isinstance(result, OrderError):
                await ctx.send(
                    f"{DiscordConstants.EMOJI_SUCCESS} 시장가 매수 주문이 "
                    f"성공적으로 실행되었습니다!\n주문 UUID: `{result.order_uuid}`"
                )
            else:
                await ctx.send(
                    f"{DiscordConstants.EMOJI_ERROR} 매수 주문 실패: "
                    f"{result.error_message}"
                )
        else:
            await ctx.send(
                f"{DiscordConstants.EMOJI_CANCEL} 매수 주문이 취소되었습니다."
            )

    except Exception:
        await ctx.send(
            f"{DiscordConstants.EMOJI_TIMEOUT} 시간 초과로 매수 주문이 취소되었습니다."
        )


async def _execute_limit_buy(
    ctx: commands.Context[Any],
    order_usecase: OrderUseCase,
    market: MarketName,
    volume_decimal: Decimal,
    price_decimal: Decimal,
) -> None:
    """지정가 매수 실행"""
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
                f"{DiscordConstants.EMOJI_PROCESSING} 지정가 매수 주문을 "
                "실행중입니다..."
            )
            limit_result = await order_usecase.buy_limit(
                market, volume_decimal, price_decimal
            )

            if not isinstance(limit_result, OrderError):
                await ctx.send(
                    f"{DiscordConstants.EMOJI_SUCCESS} 지정가 매수 주문이 "
                    f"성공적으로 실행되었습니다!\n주문 UUID: `{limit_result.order_uuid}`"
                )
            else:
                await ctx.send(
                    f"{DiscordConstants.EMOJI_ERROR} 매수 주문 실패: "
                    f"{limit_result.error_message}"
                )
        else:
            await ctx.send(
                f"{DiscordConstants.EMOJI_CANCEL} 매수 주문이 취소되었습니다."
            )

    except Exception:
        await ctx.send(
            f"{DiscordConstants.EMOJI_TIMEOUT} 시간 초과로 매수 주문이 취소되었습니다."
        )


def _create_buy_commands(order_usecase: OrderUseCase) -> list[Any]:
    """매수 커맨드들 생성"""

    @commands.command(name="매수", aliases=["buy"])
    async def buy_command(
        ctx: commands.Context[Any],
        market: MarketName,
        amount: str,
        price: str | None = None,
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
                        f"{DiscordConstants.EMOJI_ERROR} 최대 거래 금액은 "
                        f"{DiscordConstants.MAX_TRADE_AMOUNT_KRW:,}원입니다."
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
                            f"{DiscordConstants.EMOJI_CANCEL} 매수 주문이 "
                            "취소되었습니다."
                        )

                except Exception:
                    await ctx.send(
                        f"{DiscordConstants.EMOJI_TIMEOUT} 시간 초과로 매수 주문이 "
                        "취소되었습니다."
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
                        f"{DiscordConstants.EMOJI_ERROR} 최대 BTC 거래량은 "
                        f"{DiscordConstants.MAX_TRADE_VOLUME_BTC}개입니다."
                    )
                    return

                # 총 거래 금액 확인
                total_amount = volume_decimal * price_decimal
                if total_amount > DiscordConstants.MAX_TRADE_AMOUNT_KRW:
                    await ctx.send(
                        f"{DiscordConstants.EMOJI_ERROR} 총 거래 금액이 최대 한도"
                        f"({DiscordConstants.MAX_TRADE_AMOUNT_KRW:,}원)를 초과합니다."
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
                            f"{DiscordConstants.EMOJI_PROCESSING} 지정가 매수 주문을 "
                            "실행중입니다..."
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
        ctx: commands.Context[Any],
        market: MarketName,
        volume: str,
        price: str | None = None,
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
                f"{DiscordConstants.EMOJI_ERROR} 거래 명령은 관리자만 "
                "사용할 수 있습니다."
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


def _format_korean_amount(amount: float) -> str:
    """큰 숫자를 한국식 단위(만, 억)로 간단하게 표시"""
    if amount >= 100_000_000:  # 1억 이상
        return f"{amount / 100_000_000:.1f}억".replace(".0억", "억")
    elif amount >= 10_000:  # 1만 이상
        return f"{amount / 10_000:.1f}만".replace(".0만", "만")
    else:
        return f"{amount:,.0f}"


def _format_currency_amount(amount: float, currency: str) -> str:
    """통화 타입에 따라 적절한 포맷으로 숫자를 표시"""
    if currency == "KRW":
        # KRW는 한국식 단위로 표시
        return _format_korean_amount(amount)
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


def _format_percentage(value: float) -> str:
    """수익률을 색깔 이모지와 함께 표시"""
    if value > 0:
        return f"🟢+{value:.2f}%"
    elif value < 0:
        return f"🔴{value:.2f}%"
    else:
        return "⚪0.00%"


def _create_balance_command(
    account_usecase: AccountUseCase, ticker_usecase: TickerUseCase
) -> Any:
    """잔고 조회 커맨드 생성"""

    @commands.command(name="잔고", aliases=["balance", "계좌"])
    async def check_balance(ctx: commands.Context[Any]) -> None:
        """계좌 잔고를 조회합니다.
        사용법: !잔고
        """
        try:
            result = await account_usecase.get_balance()

            if result.balances:
                # 잔액이 있는 통화만 필터링
                non_zero_balances = [
                    balance
                    for balance in result.balances
                    if float(balance.balance) > 0 or float(balance.locked) > 0
                ]

                if not non_zero_balances:
                    await ctx.send("💰 **계좌 잔고**\n\n보유 중인 자산이 없습니다.")
                    return

                # KRW를 맨 위로, 나머지는 통화명 순으로 정렬
                def sort_key(balance: Any) -> tuple[int, str]:
                    currency = balance.currency
                    if currency == "KRW":
                        return (0, currency)  # KRW가 가장 위로
                    else:
                        return (1, currency)  # 나머지는 알파벳 순

                sorted_balances = sorted(non_zero_balances, key=sort_key)

                # 메시지 시작
                message = "💰 **계좌 잔고**\n\n"

                # KRW 섹션
                krw_balances = [b for b in sorted_balances if b.currency == "KRW"]
                crypto_balances = [b for b in sorted_balances if b.currency != "KRW"]

                total_krw_amount = 0.0

                if krw_balances:
                    message += "```\n"
                    message += "💵 KRW (원화)\n"
                    message += "─" * 40 + "\n"
                    message += f"{'항목':<12} {'금액':<15}\n"
                    message += "─" * 40 + "\n"

                    for balance in krw_balances:
                        balance_val = float(balance.balance)
                        locked_val = float(balance.locked)
                        total = balance_val + locked_val
                        total_krw_amount += total

                        message += f"{'사용가능':<12} {_format_korean_amount(balance_val):<15}\n"
                        if locked_val > 0:
                            message += f"{'거래중':<12} {_format_korean_amount(locked_val):<15}\n"
                        message += (
                            f"{'총 보유':<12} {_format_korean_amount(total):<15}\n"
                        )

                    message += "```\n"

                # 암호화폐 섹션
                crypto_data: list[CryptoData] = []
                total_crypto_value = 0.0
                total_crypto_investment = 0.0

                if crypto_balances:
                    for balance in crypto_balances:
                        currency = balance.currency
                        total_volume = float(balance.balance) + float(balance.locked)
                        avg_buy_price = float(balance.avg_buy_price)

                        if total_volume <= 0:
                            continue

                        # 현재가 조회
                        market_code = f"KRW-{currency}"
                        try:
                            ticker = await ticker_usecase.get_ticker_price(market_code)
                            current_price = float(ticker.trade_price) if ticker else 0
                        except Exception:
                            current_price = 0

                        # 평가금액 계산
                        current_value = (
                            total_volume * current_price if current_price > 0 else 0
                        )

                        # 투자금액 계산 (평균매수가 × 수량)
                        investment_amount = (
                            total_volume * avg_buy_price if avg_buy_price > 0 else 0
                        )

                        # 수익률 계산
                        profit_rate = (
                            ((current_price - avg_buy_price) / avg_buy_price * 100)
                            if avg_buy_price > 0 and current_price > 0
                            else 0
                        )

                        # 수익/손실 금액
                        profit_loss = current_value - investment_amount

                        crypto_info: CryptoData = {
                            "currency": currency,
                            "volume": total_volume,
                            "current_price": current_price,
                            "current_value": current_value,
                            "avg_buy_price": avg_buy_price,
                            "investment_amount": investment_amount,
                            "profit_rate": profit_rate,
                            "profit_loss": profit_loss,
                        }
                        crypto_data.append(crypto_info)

                        total_crypto_value += current_value
                        total_crypto_investment += investment_amount

                    if crypto_data:
                        if krw_balances:  # KRW가 있으면 구분선 추가
                            message += "━" * 50 + "\n\n"

                        message += "```\n"
                        message += "🪙 암호화폐\n"
                        message += "─" * 85 + "\n"
                        message += f"{'통화':<6} {'수량':<12} {'현재가':<10} {'평가금액':<10} {'평균단가':<10} {'수익률':<12} {'손익':<10}\n"
                        message += "─" * 85 + "\n"

                        for crypto in crypto_data:
                            currency_str = crypto["currency"][:5]  # 통화명 제한
                            volume_str = _format_currency_amount(
                                crypto["volume"], crypto["currency"]
                            )[:11]
                            current_price_str = (
                                _format_korean_amount(crypto["current_price"])[:9]
                                if crypto["current_price"] > 0
                                else "-"
                            )
                            current_value_str = (
                                _format_korean_amount(crypto["current_value"])[:9]
                                if crypto["current_value"] > 0
                                else "-"
                            )
                            avg_price_str = (
                                _format_korean_amount(crypto["avg_buy_price"])[:9]
                                if crypto["avg_buy_price"] > 0
                                else "-"
                            )

                            # 수익률 표시 (이모지 포함하여 짧게)
                            if crypto["profit_rate"] > 0:
                                profit_rate_str = f"🟢+{crypto['profit_rate']:.1f}%"
                            elif crypto["profit_rate"] < 0:
                                profit_rate_str = f"🔴{crypto['profit_rate']:.1f}%"
                            else:
                                profit_rate_str = "⚪0.0%"

                            profit_loss_str = _format_korean_amount(
                                abs(crypto["profit_loss"])
                            )[:9]
                            if crypto["profit_loss"] > 0:
                                profit_loss_str = f"+{profit_loss_str}"
                            elif crypto["profit_loss"] < 0:
                                profit_loss_str = f"-{profit_loss_str}"

                            message += f"{currency_str:<6} {volume_str:<12} {current_price_str:<10} {current_value_str:<10} {avg_price_str:<10} {profit_rate_str:<12} {profit_loss_str:<10}\n"

                        message += "```\n"

                # 총 포트폴리오 요약
                total_portfolio_value = total_krw_amount + total_crypto_value
                total_portfolio_investment = total_krw_amount + total_crypto_investment

                # 총 수익률 계산 (KRW는 투자원금으로 가정)
                if total_portfolio_investment > 0:
                    total_profit_rate = (
                        (total_portfolio_value - total_portfolio_investment)
                        / total_portfolio_investment
                        * 100
                    )
                    total_profit_loss = (
                        total_portfolio_value - total_portfolio_investment
                    )
                else:
                    total_profit_rate = 0
                    total_profit_loss = 0

                # 이미지 생성
                try:
                    image_bytes = create_balance_image(
                        krw_amount=total_krw_amount,
                        crypto_data=crypto_data,
                        total_portfolio_value=total_portfolio_value,
                        total_portfolio_investment=total_portfolio_investment,
                        total_profit_rate=total_profit_rate,
                        total_profit_loss=total_profit_loss,
                    )

                    # Discord 파일 객체 생성
                    file = discord.File(fp=image_bytes, filename="balance.png")

                    # 이미지와 함께 간단한 메시지 전송
                    await ctx.send("💰 **계좌 잔고**", file=file)

                except Exception as img_error:
                    # 이미지 생성 실패시 기존 텍스트 방식으로 폴백
                    message += "\n💎 **포트폴리오 요약**\n"
                    message += f"• **총 평가금액**: {_format_korean_amount(total_portfolio_value)}원 "
                    message += f"(KRW: {_format_korean_amount(total_krw_amount)}원 + 암호화폐: {_format_korean_amount(total_crypto_value)}원)\n"

                    if total_crypto_investment > 0:
                        message += f"• **총 투자금액**: {_format_korean_amount(total_portfolio_investment)}원\n"

                        # 총 수익률 표시
                        if total_profit_rate > 0:
                            message += f"• **총 수익률**: 🟢+{total_profit_rate:.2f}% (+{_format_korean_amount(total_profit_loss)}원) 📈"
                        elif total_profit_rate < 0:
                            message += f"• **총 수익률**: 🔴{total_profit_rate:.2f}% (-{_format_korean_amount(abs(total_profit_loss))}원) 📉"
                        else:
                            message += "• **총 수익률**: ⚪0.00% (±0원) ➡️"

                    await ctx.send(f"{message}\n\n⚠️ 이미지 생성 실패: {img_error}")
            else:
                await ctx.send("❌ 계좌 정보를 가져올 수 없습니다.")

        except Exception as e:
            await ctx.send(f"❌ 오류가 발생했습니다: {e!s}")

    return check_balance


def _create_price_command(ticker_usecase: TickerUseCase) -> Any:
    """시세 조회 커맨드 생성"""

    @commands.command(name="시세", aliases=["price", "가격"])
    async def check_price(
        ctx: commands.Context[Any], market: MarketName = "KRW-BTC"
    ) -> None:
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
                message += f"**현재가**: {_format_korean_amount(float(ticker.trade_price))}원\n"
                message += f"**전일 대비**: {change_color} {_format_korean_amount(abs(float(ticker.signed_change_price)))}원 ({int(change_rate):+}%)\n"
                message += (
                    f"**고가**: {_format_korean_amount(float(ticker.high_price))}원\n"
                )
                message += (
                    f"**저가**: {_format_korean_amount(float(ticker.low_price))}원\n"
                )
                message += f"**거래량**: {_format_korean_amount(float(ticker.acc_trade_volume_24h))}\n"
                message += f"**거래대금**: {_format_korean_amount(float(ticker.acc_trade_price_24h))}원"

                await ctx.send(message)
            else:
                await ctx.send(f"❌ {market} 시세 정보를 가져올 수 없습니다.")

        except Exception as e:
            await ctx.send(f"❌ 오류가 발생했습니다: {e!s}")

    return check_price


def _create_infinite_buying_commands(
    infinite_buying_usecase: InfiniteBuyingUsecase,
) -> list[Any]:
    """무한매수법 커맨드들 생성"""

    @commands.command(name="무한매수시작", aliases=["infinite_start", "무한시작"])
    async def start_infinite_buying_command(
        ctx: commands.Context[Any],
        market: MarketName,
        initial_amount: str,
        target_profit: str = "10",
        drop_threshold: str = "5",
        max_rounds: str = "10",
    ) -> None:
        """
        무한매수법을 시작합니다.

        사용법:
        !무한매수시작 [마켓] [초기금액] [목표수익률] [하락기준] [최대회차]

        예시:
        !무한매수시작 KRW-BTC 100000 - 10만원으로 BTC 무한매수법 시작
        !무한매수시작 KRW-BTC 100000 15 3 15 - 목표수익률 15%, 하락기준 3%, 최대 15회차
        """
        # 관리자 권한 확인
        if not _is_admin(ctx.author.id):
            await ctx.send(
                f"{DiscordConstants.EMOJI_ERROR} 무한매수법은 관리자만 "
                "사용할 수 있습니다."
            )
            return

        try:
            market = market.upper()
            initial_buy_amount = Decimal(initial_amount)
            target_profit_rate = Decimal(target_profit) / Decimal("100")  # % to decimal
            price_drop_threshold = -Decimal(drop_threshold) / Decimal(
                "100"
            )  # % to negative decimal
            max_buy_rounds = int(max_rounds)

            # 파라미터 검증
            if initial_buy_amount < MIN_INITIAL_BUY_AMOUNT:
                await ctx.send(
                    f"{DiscordConstants.EMOJI_ERROR} 최소 초기 매수 금액은 {MIN_INITIAL_BUY_AMOUNT:,}원입니다."
                )
                return

            if initial_buy_amount > MAX_TRADE_AMOUNT_KRW:
                await ctx.send(
                    f"{DiscordConstants.EMOJI_ERROR} 최대 초기 매수 금액은 {MAX_TRADE_AMOUNT_KRW:,}원입니다."
                )
                return

            if target_profit_rate <= 0 or target_profit_rate > 1:
                await ctx.send(
                    f"{DiscordConstants.EMOJI_ERROR} 목표 수익률은 0보다 크고 100% 이하여야 합니다."
                )
                return

            if (
                price_drop_threshold >= 0
                or price_drop_threshold < MIN_PRICE_DROP_THRESHOLD
            ):
                await ctx.send(
                    f"{DiscordConstants.EMOJI_ERROR} 하락 기준은 0보다 작고 {abs(MIN_PRICE_DROP_THRESHOLD):.0%} 이상이어야 합니다."
                )
                return

            # 확인 메시지
            embed = discord.Embed(
                title="🔄 무한매수법 시작 확인",
                description=f"**{market}** 무한매수법을 시작하시겠습니까?",
                color=DiscordConstants.COLOR_WARNING,
            )

            embed.add_field(
                name="초기 매수 금액",
                value=f"{initial_buy_amount:,.0f} 원",
                inline=True,
            )
            embed.add_field(
                name="목표 수익률", value=f"{target_profit_rate:.1%}", inline=True
            )
            embed.add_field(
                name="추가 매수 기준",
                value=f"{abs(price_drop_threshold):.1%} 하락",
                inline=True,
            )
            embed.add_field(
                name="최대 매수 회차", value=f"{max_buy_rounds}회", inline=True
            )
            embed.add_field(name="거래 모드", value="실거래", inline=True)

            embed.add_field(
                name=f"{DiscordConstants.EMOJI_WARNING} 주의사항",
                value=f"{DiscordConstants.EMOJI_CONFIRM} 또는 {DiscordConstants.EMOJI_CANCEL} 이모지로 응답해주세요.\n10초 내에 응답하지 않으면 취소됩니다.",
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
                    "reaction_add", timeout=10.0, check=check
                )

                if str(reaction.emoji) == DiscordConstants.EMOJI_CONFIRM:
                    await ctx.send(
                        f"{DiscordConstants.EMOJI_PROCESSING} 무한매수법을 시작하는 중..."
                    )

                    try:
                        result = await infinite_buying_usecase.start_infinite_buying(
                            market=market,
                            initial_buy_amount=initial_buy_amount,
                            target_profit_rate=target_profit_rate,
                            price_drop_threshold=price_drop_threshold,
                            max_buy_rounds=max_buy_rounds,
                        )

                        if result.success:
                            await ctx.send(
                                f"{DiscordConstants.EMOJI_SUCCESS} {result.message}\n"
                                f"사이클 ID: `{result.current_state.cycle_id if result.current_state else 'N/A'}`"
                            )
                        else:
                            await ctx.send(
                                f"{DiscordConstants.EMOJI_ERROR} {result.message}"
                            )

                    except RuntimeError as e:
                        await ctx.send(
                            f"{DiscordConstants.EMOJI_ERROR} 설정 저장 실패: {e!s}"
                        )
                    except ConnectionError as e:
                        await ctx.send(
                            f"{DiscordConstants.EMOJI_ERROR} 네트워크 연결 오류: {e!s}"
                        )
                    except Exception as e:
                        await ctx.send(
                            f"{DiscordConstants.EMOJI_ERROR} 시스템 오류가 발생했습니다: {e!s}"
                        )

                else:
                    await ctx.send(
                        f"{DiscordConstants.EMOJI_CANCEL} 무한매수법 시작이 취소되었습니다."
                    )

            except Exception:
                await ctx.send(
                    f"{DiscordConstants.EMOJI_TIMEOUT} 시간 초과로 무한매수법 시작이 취소되었습니다."
                )

        except ValueError as e:
            await ctx.send(f"{DiscordConstants.EMOJI_ERROR} 잘못된 입력값입니다: {e!s}")
        except Exception as e:
            await ctx.send(f"{DiscordConstants.EMOJI_ERROR} 오류가 발생했습니다: {e!s}")

    @commands.command(name="무한매수조회", aliases=["infinite_status", "무한조회"])
    async def check_infinite_buying_status_command(
        ctx: commands.Context[Any], market: MarketName | None = None
    ) -> None:
        """
        무한매수법 상태를 조회합니다.

        사용법:
        !무한매수조회 - 전체 상태 조회
        !무한매수조회 [마켓] - 특정 마켓 상태 조회

        예시:
        !무한매수조회 KRW-BTC
        """
        try:
            if market:
                market = market.upper()
                # 특정 마켓 상태 조회
                market_status = (
                    await infinite_buying_usecase.get_infinite_buying_market_status(
                        market
                    )
                )

                if market_status.status == InfiniteBuyingStatus.INACTIVE:
                    await ctx.send(f"📴 **{market}** 무한매수법이 실행 중이 아닙니다.")
                    return

                # 이미지 생성 시도
                try:
                    image_bytes = create_infinite_buying_image(market_status)
                    file = discord.File(
                        fp=image_bytes, filename="infinite_buying_status.png"
                    )
                    await ctx.send(f"🔄 **{market} 무한매수법 상태**", file=file)

                except Exception as img_error:
                    # 이미지 생성 실패시 기존 Embed 방식으로 폴백
                    embed = discord.Embed(
                        title=f"🔄 {market} 무한매수법 상태",
                        color=DiscordConstants.COLOR_INFO,
                    )

                    embed.add_field(name="상태", value=market_status.phase, inline=True)
                    embed.add_field(
                        name="현재 회차",
                        value=f"{market_status.current_round}회",
                        inline=True,
                    )
                    embed.add_field(
                        name="사이클 ID",
                        value=market_status.cycle_id or "N/A",
                        inline=True,
                    )

                    embed.add_field(
                        name="총 투자액",
                        value=f"{_format_korean_amount(float(market_status.total_investment))}원",
                        inline=True,
                    )
                    embed.add_field(
                        name="평균 단가",
                        value=f"{_format_korean_amount(float(market_status.average_price))}원",
                        inline=True,
                    )
                    embed.add_field(
                        name="목표 가격",
                        value=f"{_format_korean_amount(float(market_status.target_sell_price))}원",
                        inline=True,
                    )

                    # 수익률 정보 추가 (현재가 정보가 있는 경우)
                    if (
                        market_status.current_price
                        and market_status.current_profit_rate is not None
                    ):
                        embed.add_field(
                            name="현재가",
                            value=f"{_format_korean_amount(float(market_status.current_price))}원",
                            inline=True,
                        )
                        embed.add_field(
                            name="현재 평가금액",
                            value=f"{_format_korean_amount(float(market_status.current_value))}원"
                            if market_status.current_value
                            else "-",
                            inline=True,
                        )

                        # 수익률 표시
                        profit_rate = float(market_status.current_profit_rate) * 100
                        if profit_rate > 0:
                            profit_display = f"🟢+{profit_rate:.2f}%"
                        elif profit_rate < 0:
                            profit_display = f"🔴{profit_rate:.2f}%"
                        else:
                            profit_display = "⚪0.00%"

                        embed.add_field(
                            name="현재 수익률",
                            value=profit_display,
                            inline=True,
                        )

                        # 손익 금액
                        if market_status.profit_loss_amount is not None:
                            profit_loss = float(market_status.profit_loss_amount)
                            if profit_loss > 0:
                                profit_loss_display = (
                                    f"🟢+{_format_korean_amount(profit_loss)}원"
                                )
                            elif profit_loss < 0:
                                profit_loss_display = (
                                    f"🔴-{_format_korean_amount(abs(profit_loss))}원"
                                )
                            else:
                                profit_loss_display = "⚪±0원"

                            embed.add_field(
                                name="손익 금액",
                                value=profit_loss_display,
                                inline=True,
                            )

                    # 매수 히스토리
                    if market_status.buying_rounds:
                        history_text = ""
                        for round_info in market_status.buying_rounds[
                            -5:
                        ]:  # 최근 5개만 표시
                            buy_price_str = _format_korean_amount(
                                float(round_info.buy_price)
                            )
                            buy_amount_str = _format_korean_amount(
                                float(round_info.buy_amount)
                            )
                            history_text += f"{round_info.round_number}회: {buy_price_str}원 ({buy_amount_str}원)\n"

                        embed.add_field(
                            name="최근 매수 히스토리",
                            value=history_text if history_text else "없음",
                            inline=False,
                        )

                    embed.add_field(
                        name="⚠️ 알림",
                        value=f"이미지 생성 실패: {img_error}",
                        inline=False,
                    )

                    await ctx.send(embed=embed)
            else:
                # 전체 상태 조회
                overall_status = (
                    await infinite_buying_usecase.get_infinite_buying_overall_status()
                )

                if overall_status.total_active_markets == 0:
                    await ctx.send("📴 현재 실행 중인 무한매수법이 없습니다.")
                    return

                message = "🔄 **무한매수법 전체 상태**\n\n"
                message += f"**활성 시장**: {overall_status.total_active_markets}개\n"
                message += (
                    f"**시장 목록**: {', '.join(overall_status.active_markets)}\n\n"
                )
                message += "자세한 정보를 보려면 `!무한매수조회 [마켓]`을 사용하세요."

                await ctx.send(message)

        except ConnectionError as e:
            await ctx.send(f"{DiscordConstants.EMOJI_ERROR} 네트워크 연결 오류: {e!s}")
        except Exception as e:
            await ctx.send(f"{DiscordConstants.EMOJI_ERROR} 오류가 발생했습니다: {e!s}")

    @commands.command(name="무한매수종료", aliases=["infinite_stop", "무한종료"])
    async def stop_infinite_buying_command(
        ctx: commands.Context[Any], market: MarketName, force_sell: str = "false"
    ) -> None:
        """
        무한매수법을 종료합니다.

        사용법:
        !무한매수종료 [마켓] [강제매도]

        예시:
        !무한매수종료 KRW-BTC - 정상 종료
        !무한매수종료 KRW-BTC true - 강제 매도 후 종료
        """
        # 관리자 권한 확인
        if not _is_admin(ctx.author.id):
            await ctx.send(
                f"{DiscordConstants.EMOJI_ERROR} 무한매수법 종료는 관리자만 사용할 수 있습니다."
            )
            return

        try:
            market = market.upper()
            force_sell_flag = force_sell.lower() in ["true", "1", "yes", "강제"]

            # 현재 상태 확인
            if not await infinite_buying_usecase.is_market_active(market):
                await ctx.send(f"📴 **{market}** 무한매수법이 실행 중이 아닙니다.")
                return

            # 확인 메시지
            action_text = "강제 종료 (전량 매도)" if force_sell_flag else "정상 종료"
            embed = discord.Embed(
                title="⚠️ 무한매수법 종료 확인",
                description=f"**{market}** 무한매수법을 {action_text}하시겠습니까?",
                color=DiscordConstants.COLOR_WARNING,
            )

            if force_sell_flag:
                embed.add_field(
                    name="⚠️ 강제 매도 주의사항",
                    value="현재 보유한 모든 수량을 즉시 시장가로 매도합니다.\n손실이 발생할 수 있습니다.",
                    inline=False,
                )

            embed.add_field(
                name=f"{DiscordConstants.EMOJI_WARNING} 주의사항",
                value=f"{DiscordConstants.EMOJI_CONFIRM} 또는 {DiscordConstants.EMOJI_CANCEL} 이모지로 응답해주세요.\n10초 내에 응답하지 않으면 취소됩니다.",
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
                    "reaction_add", timeout=10.0, check=check
                )

                if str(reaction.emoji) == DiscordConstants.EMOJI_CONFIRM:
                    await ctx.send(
                        f"{DiscordConstants.EMOJI_PROCESSING} 무한매수법을 종료하는 중..."
                    )

                    try:
                        result = await infinite_buying_usecase.stop_infinite_buying(
                            market=market, force_sell=force_sell_flag
                        )

                        if result.success:
                            await ctx.send(
                                f"{DiscordConstants.EMOJI_SUCCESS} {result.message}"
                            )
                        else:
                            await ctx.send(
                                f"{DiscordConstants.EMOJI_ERROR} {result.message}"
                            )

                    except ConnectionError as e:
                        await ctx.send(
                            f"{DiscordConstants.EMOJI_ERROR} 네트워크 연결 오류: {e!s}"
                        )
                    except Exception as e:
                        await ctx.send(
                            f"{DiscordConstants.EMOJI_ERROR} 시스템 오류가 발생했습니다: {e!s}"
                        )

                else:
                    await ctx.send(
                        f"{DiscordConstants.EMOJI_CANCEL} 무한매수법 종료가 취소되었습니다."
                    )

            except Exception:
                await ctx.send(
                    f"{DiscordConstants.EMOJI_TIMEOUT} 시간 초과로 무한매수법 종료가 취소되었습니다."
                )

        except Exception as e:
            await ctx.send(f"{DiscordConstants.EMOJI_ERROR} 오류가 발생했습니다: {e!s}")

    return [
        start_infinite_buying_command,
        check_infinite_buying_status_command,
        stop_infinite_buying_command,
    ]


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

            message += "**🔄 무한매수법 명령어 (관리자 전용)**\n"
            message += "**!무한매수시작 [마켓] [초기금액]** - 무한매수법 시작\n"
            message += "**!무한매수조회 [마켓]** - 무한매수법 상태 조회\n"
            message += "**!무한매수종료 [마켓] [강제매도]** - 무한매수법 종료\n"
            message += "  예시: `!무한매수시작 KRW-BTC 100000`\n"
            message += "  예시: `!무한매수종료 KRW-BTC true` (강제매도)\n\n"

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
    infinite_buying_usecase: InfiniteBuyingUsecase | None = None,
) -> None:
    """Discord Bot에 커맨드를 등록합니다."""
    # 기존 커맨드들
    balance_command = _create_balance_command(account_usecase, ticker_usecase)
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

    # 무한매수법 커맨드들 등록
    if infinite_buying_usecase:
        infinite_buying_commands = _create_infinite_buying_commands(
            infinite_buying_usecase
        )
        for command in infinite_buying_commands:
            bot_adapter.add_command(command)
