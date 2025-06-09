"""Discord Embed 생성 유틸리티"""

from datetime import datetime
from typing import Any

import discord


def create_balance_embed(balance_data: dict[str, Any]) -> discord.Embed:
    """잔고 조회 Embed 생성"""
    embed = discord.Embed(
        title="💰 잔고 조회", color=0x00FF00, timestamp=datetime.now()
    )

    # 총 평가액
    total_value = balance_data.get("total_value", 0)
    embed.add_field(name="📊 총 평가액", value=f"₩ {total_value:,.0f}", inline=True)

    # 가용 현금
    available_cash = balance_data.get("available_cash", 0)
    embed.add_field(name="💵 가용 현금", value=f"₩ {available_cash:,.0f}", inline=True)

    # 보유 종목별 정보
    holdings = balance_data.get("holdings", [])
    if holdings:
        holdings_text = ""
        for holding in holdings[:10]:  # 최대 10개만 표시
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

    # 진행률
    current_count = dca_data.get("current_count", 0)
    total_count = dca_data.get("total_count", 0)
    progress_rate = (current_count / total_count * 100) if total_count > 0 else 0

    progress_bar = "█" * int(progress_rate / 10) + "░" * (10 - int(progress_rate / 10))

    embed.add_field(
        name="📈 진행률",
        value=f"{progress_bar} {progress_rate:.1f}%\n({current_count}/{total_count}회)",
        inline=False,
    )

    # 다음 매수 시간
    next_buy_time = dca_data.get("next_buy_time")
    if next_buy_time:
        embed.add_field(
            name="⏰ 다음 매수",
            value=f"<t:{int(next_buy_time.timestamp())}:R>",
            inline=True,
        )

    # 평균 매입가
    avg_price = dca_data.get("average_price", 0)
    current_price = dca_data.get("current_price", 0)
    # symbol = dca_data.get("symbol", "")  # TODO: 필요시 사용

    embed.add_field(name="💰 평균 매입가", value=f"₩ {avg_price:,.0f}", inline=True)

    embed.add_field(name="📊 현재가", value=f"₩ {current_price:,.0f}", inline=True)

    # 수익률
    profit_rate = dca_data.get("profit_rate", 0)
    profit_emoji = "📈" if profit_rate >= 0 else "📉"
    profit_color = "🟢" if profit_rate >= 0 else "🔴"

    embed.add_field(
        name=f"{profit_emoji} 현재 수익률",
        value=f"{profit_color} {profit_rate:+.2f}%",
        inline=True,
    )

    # 누적 투자액
    total_invested = dca_data.get("total_invested", 0)
    embed.add_field(
        name="💸 누적 투자액", value=f"₩ {total_invested:,.0f}", inline=True
    )

    # 최근 체결 내역
    recent_trades = dca_data.get("recent_trades", [])
    if recent_trades:
        trades_text = ""
        for trade in recent_trades[:5]:  # 최대 5개
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

    # 누적 손익
    total_profit = profit_data.get("total_profit", 0)
    total_profit_rate = profit_data.get("total_profit_rate", 0)

    profit_emoji = "📈" if total_profit >= 0 else "📉"
    profit_color = "🟢" if total_profit >= 0 else "🔴"

    embed.add_field(
        name=f"{profit_emoji} 누적 손익",
        value=f"{profit_color} ₩ {total_profit:+,.0f} ({total_profit_rate:+.2f}%)",
        inline=False,
    )

    # 기간별 수익률
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

    # Top Gainers
    top_gainers = profit_data.get("top_gainers", [])
    if top_gainers:
        gainers_text = ""
        for gainer in top_gainers[:3]:  # 상위 3개
            symbol = gainer.get("symbol", "")
            rate = gainer.get("rate", 0)
            gainers_text += f"📈 {symbol}: +{rate:.2f}%\n"

        embed.add_field(
            name="🏆 Top Gainers", value=gainers_text or "데이터 없음", inline=True
        )

    # Top Losers
    top_losers = profit_data.get("top_losers", [])
    if top_losers:
        losers_text = ""
        for loser in top_losers[:3]:  # 상위 3개
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

    # 진행 현황
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
