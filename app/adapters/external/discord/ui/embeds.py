import logging
from typing import Any

import discord

from common.utils.timezone import now_kst

logger = logging.getLogger(__name__)


def create_balance_embed(balance_data: dict[str, Any]) -> discord.Embed:
    """잔고 조회 Embed 생성"""
    embed = discord.Embed(title="💰 잔고 조회", color=0x00FF00, timestamp=now_kst())
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


def create_dca_status_embed(dca_list: list[dict[str, Any]]) -> discord.Embed:
    """DCA 상태 조회 Embed 생성"""
    embed = discord.Embed(title="📊 DCA 상태", color=0x0099FF, timestamp=now_kst())

    if not dca_list:
        embed.description = "진행중인 DCA가 없습니다."
        return embed

    for data in dca_list:
        current_count = data.get("current_count", 0)
        total_count = data.get("total_count", 0)
        progress_rate = (current_count / total_count * 100) if total_count > 0 else 0
        progress_bar = "█" * int(progress_rate / 10) + "░" * (
            10 - int(progress_rate / 10)
        )
        symbol = data.get("symbol", "")
        profit_rate = data.get("profit_rate", 0)
        profit_emoji = "📈" if profit_rate >= 0 else "📉"
        profit_color = "🟢" if profit_rate >= 0 else "🔴"
        field_value = (
            f"{progress_bar} {progress_rate:.1f}%\n"
            f"평균가: ₩ {data.get('average_price', 0):,.0f}\n"
            f"현재가: ₩ {data.get('current_price', 0):,.0f}\n"
            f"{profit_emoji} 수익률: {profit_color} {profit_rate:+.2f}%\n"
            f"누적 투자액: ₩ {data.get('total_invested', 0):,.0f}"
        )
        embed.add_field(name=f"🪙 {symbol}", value=field_value, inline=False)

    embed.set_footer(text="TTM Bot • 실시간 데이터")
    return embed


def create_profit_embed(profit_data: dict[str, Any]) -> discord.Embed:
    """수익률 조회 Embed 생성"""
    embed = discord.Embed(title="📈 수익률", color=0xFF9900, timestamp=now_kst())
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
        timestamp=now_kst(),
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
        timestamp=now_kst(),
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
