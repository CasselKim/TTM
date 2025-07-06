import logging
from typing import Any

import discord
from datetime import datetime

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


def create_dca_status_embed_summary(dca_list: list[dict[str, Any]]) -> discord.Embed:
    """DCA 상태 요약 Embed 생성"""
    embed = discord.Embed(
        title="📊 DCA 상태 (요약)", color=0x0099FF, timestamp=now_kst()
    )

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

        # Smart DCA 상태 표시
        smart_dca_enabled = data.get("smart_dca_enabled", False)
        smart_dca_indicator = "🧠" if smart_dca_enabled else ""

        field_value = (
            f"{progress_bar} {progress_rate:.1f}%\n"
            f"평균가: ₩ {data.get('average_price', 0):,.0f}\n"
            f"현재가: ₩ {data.get('current_price', 0):,.0f}\n"
            f"{profit_emoji} 수익률: {profit_color} {profit_rate:+.2f}%\n"
            f"누적 투자액: ₩ {data.get('total_invested', 0):,.0f}"
        )
        embed.add_field(
            name=f"🪙 {symbol} {smart_dca_indicator}", value=field_value, inline=False
        )

    embed.set_footer(text="TTM Bot • 실시간 데이터")
    return embed


def format_trade_time_kor(dt: str | datetime) -> str:
    """YYYY-MM-DD(요일) HH:MM:SS 형식, millisecond 제거, 한글 요일 포함"""
    if isinstance(dt, str):
        try:
            dt_obj = datetime.fromisoformat(dt)
        except Exception:
            return dt  # str 반환
    else:
        dt_obj = dt
    dt_obj = dt_obj.replace(microsecond=0)
    weekday_kor = ["월", "화", "수", "목", "금", "토", "일"]
    w = weekday_kor[dt_obj.weekday()]
    return dt_obj.strftime(f"%Y-%m-%d({w}) %H:%M:%S")


def create_dca_status_embed_detail(
    dca_detail_list: list[dict[str, Any]],
) -> discord.Embed:
    """DCA 상태 상세 Embed 생성 (config, state, 수익률, 매수내역 등 모두 표시)"""
    embed = discord.Embed(
        title="📊 DCA 상태 (상세)", color=0x0055FF, timestamp=now_kst()
    )

    if not dca_detail_list:
        embed.description = "진행중인 DCA가 없습니다."
        return embed

    for data in dca_detail_list:
        symbol = data.get("symbol", "")
        config = data.get("config", {})
        state = data.get("state", {})
        market_status = data.get("market_status", {})
        recent_trades = data.get("recent_trades", [])
        # config 필드
        config_lines = [
            f"- 초기 매수 금액: {config.get('initial_buy_amount', '-'):,} KRW",
            f"- 추가 매수 배수: {config.get('add_buy_multiplier', '-')}"
            f"\n- 목표 수익률: {float(config.get('target_profit_rate', 0)) * 100:.2f}%",
            f"- 추가 매수 하락률: {float(config.get('price_drop_threshold', 0)) * 100:.2f}%",
            f"- 강제 손절률: {float(config.get('force_stop_loss_rate', 0)) * 100:.2f}%",
            f"- 최대 매수 회차: {config.get('max_buy_rounds', '-')}회",
            f"- 최대 투자 비율: {float(config.get('max_investment_ratio', 0)) * 100:.2f}%",
            f"- 최소 매수 간격: {config.get('min_buy_interval_minutes', '-')}분",
            f"- 최대 사이클 기간: {config.get('max_cycle_days', '-')}일",
            f"- 시간 기반 매수 간격: {config.get('time_based_buy_interval_hours', '-')}시간",
        ]

        # Smart DCA 설정 추가
        smart_dca_enabled = config.get("enable_smart_dca", False)
        if smart_dca_enabled:
            config_lines.extend(
                [
                    "- 🧠 Smart DCA: 활성화",
                    f"- Smart DCA ρ: {float(config.get('smart_dca_rho', 1.5)):.1f}",
                    f"- Smart DCA 최대 배수: {float(config.get('smart_dca_max_multiplier', 5.0)):.1f}x",
                    f"- Smart DCA 최소 배수: {float(config.get('smart_dca_min_multiplier', 0.1)):.1f}x",
                ]
            )
        else:
            config_lines.append("- 🧠 Smart DCA: 비활성화")
        # state 필드
        raw_state_lines = [
            f"- 마켓: {state.get('market', '-')} (ID: {state.get('cycle_id', '-')})",
            f"- 단계: {state.get('phase', '-')} / 상태: {market_status.get('status', '-')} ",
            f"- 현재 회차: {state.get('current_round', '-')}회",
            f"- 총 투자 금액: {state.get('total_investment', 0):,} KRW",
            f"- 평균 매수 단가: {state.get('average_price', 0):,.0f} KRW",
            f"- 사이클 시작 시각: {state.get('cycle_start_time', '-')}"
            if state.get("cycle_start_time")
            else None,
            f"- 목표 매도 가격: {state.get('target_sell_price', 0):,.0f} KRW",
        ]
        state_lines = [line for line in raw_state_lines if line is not None]  # type: list[str]
        # 수익률/평가
        profit_lines = [
            f"- 현재가: {market_status.get('current_price', 0):,.0f} KRW",
            f"- 평가 금액: {market_status.get('current_value', 0):,.0f} KRW",
            f"- 수익률: {market_status.get('current_profit_rate', 0):.2f}%",
            f"- 손익: {market_status.get('profit_loss_amount', 0):,.0f} KRW",
        ]
        # 최근 매수 내역
        trade_lines = []
        for t in recent_trades:
            trade_time = format_trade_time_kor(t.get("time", "-"))
            amount = int(t.get("amount", 0))
            price = int(t.get("price", 0))
            trade_lines.append(f"- {trade_time} {amount:,}W, {price:,}KRW")
        if not trade_lines:
            trade_lines = ["- 최근 매수 내역 없음"]
        # 전체 field
        field_value = (
            "__설정 정보__\n"
            + "\n".join(config_lines)
            + "\n\n__진행 상태__\n"
            + "\n".join(state_lines)
            + "\n\n__수익률/평가__\n"
            + "\n".join(profit_lines)
            + "\n\n__최근 매수 내역__\n"
            + "\n".join(trade_lines)
        )
        embed.add_field(name=f"🪙 {symbol} 상세", value=field_value, inline=False)

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
    enable_smart_dca = trade_data.get("enable_smart_dca", False)

    # Smart DCA 활성화 여부에 따라 제목과 설명 조정
    if enable_smart_dca:
        title = "✅ Smart DCA 실행 완료"
        description = "🧠 Smart DCA 자동매매가 성공적으로 시작되었습니다!"
    else:
        title = "✅ 매매 실행 완료"
        description = "자동매매가 성공적으로 시작되었습니다!"

    embed = discord.Embed(
        title=title,
        description=description,
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

    # Smart DCA 정보 표시
    if enable_smart_dca:
        smart_dca_rho = trade_data.get("smart_dca_rho")
        smart_dca_max_multiplier = trade_data.get("smart_dca_max_multiplier")
        smart_dca_min_multiplier = trade_data.get("smart_dca_min_multiplier")

        if smart_dca_rho is not None:
            embed.add_field(
                name="🧠 Smart DCA ρ", value=f"{smart_dca_rho:.1f}", inline=True
            )
        if smart_dca_max_multiplier is not None:
            embed.add_field(
                name="📈 최대 투자 배수",
                value=f"{smart_dca_max_multiplier:.1f}x",
                inline=True,
            )
        if smart_dca_min_multiplier is not None:
            embed.add_field(
                name="📉 최소 투자 배수",
                value=f"{smart_dca_min_multiplier:.1f}x",
                inline=True,
            )

    # 추가 매수 배수 정보 표시 (Smart DCA와 일반 DCA 모두 해당)
    add_buy_multiplier = trade_data.get("add_buy_multiplier")
    if add_buy_multiplier is not None:
        embed.add_field(
            name="🔢 추가 매수 배수", value=f"{add_buy_multiplier:.1f}x", inline=True
        )

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
