"""Discord 봇용 이미지 생성 모듈"""

import io
from typing import Any

from PIL import Image, ImageDraw, ImageFont  # type: ignore

from app.adapters.internal.websocket.discord_bot import CryptoData


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
        return _format_korean_amount(amount)
    else:
        # 암호화폐는 8자리 소수점까지 표시하되, 불필요한 0 제거
        formatted = f"{amount:.8f}".rstrip("0").rstrip(".")
        # 천 단위 구분자 추가 (정수 부분에만)
        parts = formatted.split(".")
        if len(parts) == 2:
            integer_part = f"{int(parts[0]):,}"
            return f"{integer_part}.{parts[1]}"
        else:
            return f"{int(amount):,}"


def create_balance_image(
    krw_amount: float,
    crypto_data: list[CryptoData],
    total_portfolio_value: float,
    total_portfolio_investment: float,
    total_profit_rate: float,
    total_profit_loss: float,
) -> io.BytesIO:
    """잔고 정보를 이미지로 생성"""

    # 이미지 크기 설정
    width = 800
    base_height = 200  # 기본 높이
    row_height = 40  # 각 암호화폐 행 높이
    height = base_height + len(crypto_data) * row_height + 150  # 요약 섹션

    # 색상 정의
    bg_color = (54, 57, 63)  # Discord 다크 배경색
    text_color = (255, 255, 255)  # 흰색 텍스트
    header_color = (88, 101, 242)  # Discord 브랜드 색상
    green_color = (87, 242, 135)  # 수익 색상
    red_color = (237, 66, 69)  # 손실 색상
    gray_color = (153, 170, 181)  # 중성 색상

    # 이미지 생성
    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    # 폰트 설정 (기본 폰트 사용)
    try:
        title_font = ImageFont.truetype("/System/Library/Fonts/Arial Bold.ttf", 20)
        header_font = ImageFont.truetype("/System/Library/Fonts/Arial Bold.ttf", 14)
        normal_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 12)
    except OSError:
        # 폰트를 찾을 수 없는 경우 기본 폰트 사용
        title_font = ImageFont.load_default()
        header_font = ImageFont.load_default()
        normal_font = ImageFont.load_default()

    # 시작 Y 위치
    y = 20

    # 제목
    draw.text((20, y), "💰 계좌 잔고", fill=text_color, font=title_font)
    y += 50

    # KRW 섹션
    draw.text((20, y), "💵 KRW (원화)", fill=header_color, font=header_font)
    y += 30
    draw.text(
        (40, y),
        f"보유 금액: {_format_korean_amount(krw_amount)}원",
        fill=text_color,
        font=normal_font,
    )
    y += 50

    # 암호화폐 섹션
    if crypto_data:
        draw.text((20, y), "🪙 암호화폐", fill=header_color, font=header_font)
        y += 30

        # 테이블 헤더
        headers = ["통화", "수량", "현재가", "평가금액", "평균단가", "수익률", "손익"]
        col_widths = [60, 100, 80, 80, 80, 80, 80]
        x_positions = [20]
        for width in col_widths[:-1]:
            x_positions.append(x_positions[-1] + width)

        # 헤더 그리기
        for i, header in enumerate(headers):
            draw.text((x_positions[i], y), header, fill=gray_color, font=header_font)
        y += 25

        # 구분선
        draw.line((20, y, width - 20, y), fill=gray_color, width=1)
        y += 10

        # 각 암호화폐 데이터
        for crypto in crypto_data:
            # 데이터 준비
            currency = crypto["currency"][:5]
            volume = _format_currency_amount(crypto["volume"], crypto["currency"])[:11]
            current_price = (
                _format_korean_amount(crypto["current_price"])[:9]
                if crypto["current_price"] > 0
                else "-"
            )
            current_value = (
                _format_korean_amount(crypto["current_value"])[:9]
                if crypto["current_value"] > 0
                else "-"
            )
            avg_price = (
                _format_korean_amount(crypto["avg_buy_price"])[:9]
                if crypto["avg_buy_price"] > 0
                else "-"
            )

            # 수익률 색상 결정
            profit_rate = crypto["profit_rate"]
            if profit_rate > 0:
                profit_color = green_color
                profit_text = f"+{profit_rate:.1f}%"
            elif profit_rate < 0:
                profit_color = red_color
                profit_text = f"{profit_rate:.1f}%"
            else:
                profit_color = gray_color
                profit_text = "0.0%"

            # 손익 금액
            profit_loss = crypto["profit_loss"]
            if profit_loss > 0:
                profit_loss_color = green_color
                profit_loss_text = f"+{_format_korean_amount(profit_loss)}"
            elif profit_loss < 0:
                profit_loss_color = red_color
                profit_loss_text = f"-{_format_korean_amount(abs(profit_loss))}"
            else:
                profit_loss_color = gray_color
                profit_loss_text = "±0"

            # 데이터 그리기
            data = [currency, volume, current_price, current_value, avg_price]
            for i, text in enumerate(data):
                draw.text((x_positions[i], y), text, fill=text_color, font=normal_font)

            # 수익률과 손익은 색상 적용
            draw.text(
                (x_positions[5], y), profit_text, fill=profit_color, font=normal_font
            )
            draw.text(
                (x_positions[6], y),
                profit_loss_text,
                fill=profit_loss_color,
                font=normal_font,
            )

            y += row_height

    # 구분선
    y += 20
    draw.line((20, y, width - 20, y), fill=gray_color, width=2)
    y += 20

    # 포트폴리오 요약
    draw.text((20, y), "💎 포트폴리오 요약", fill=header_color, font=header_font)
    y += 30

    # 총 평가금액
    draw.text(
        (40, y),
        f"총 평가금액: {_format_korean_amount(total_portfolio_value)}원",
        fill=text_color,
        font=normal_font,
    )
    y += 25

    # 총 투자금액
    if total_portfolio_investment > 0:
        draw.text(
            (40, y),
            f"총 투자금액: {_format_korean_amount(total_portfolio_investment)}원",
            fill=text_color,
            font=normal_font,
        )
        y += 25

        # 총 수익률
        if total_profit_rate > 0:
            profit_color = green_color
            emoji = "📈"
            profit_text = f"총 수익률: +{total_profit_rate:.2f}% (+{_format_korean_amount(total_profit_loss)}원) {emoji}"
        elif total_profit_rate < 0:
            profit_color = red_color
            emoji = "📉"
            profit_text = f"총 수익률: {total_profit_rate:.2f}% (-{_format_korean_amount(abs(total_profit_loss))}원) {emoji}"
        else:
            profit_color = gray_color
            emoji = "➡️"
            profit_text = f"총 수익률: 0.00% (±0원) {emoji}"

        draw.text((40, y), profit_text, fill=profit_color, font=normal_font)

    # 이미지를 BytesIO로 변환
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    return img_bytes


def create_infinite_buying_image(market_status: Any) -> io.BytesIO:
    """무한매수법 상태를 이미지로 생성"""

    # 이미지 크기 설정
    width = 600
    height = 400

    # 색상 정의
    bg_color = (54, 57, 63)
    text_color = (255, 255, 255)
    header_color = (88, 101, 242)
    green_color = (87, 242, 135)
    red_color = (237, 66, 69)
    gray_color = (153, 170, 181)

    # 이미지 생성
    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    # 폰트 설정
    try:
        title_font = ImageFont.truetype("/System/Library/Fonts/Arial Bold.ttf", 18)
        normal_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 12)
    except OSError:
        title_font = ImageFont.load_default()
        normal_font = ImageFont.load_default()

    y = 20

    # 제목
    draw.text(
        (20, y),
        f"🔄 {market_status.market} 무한매수법 상태",
        fill=text_color,
        font=title_font,
    )
    y += 40

    # 기본 정보
    info_lines = [
        f"상태: {market_status.phase}",
        f"현재 회차: {market_status.current_round}회",
        f"사이클 ID: {market_status.cycle_id or 'N/A'}",
        "",
        f"총 투자액: {_format_korean_amount(float(market_status.total_investment))}원",
        f"평균 단가: {_format_korean_amount(float(market_status.average_price))}원",
        f"목표 가격: {_format_korean_amount(float(market_status.target_sell_price))}원",
    ]

    for line in info_lines:
        if line:  # 빈 줄이 아닌 경우
            draw.text((20, y), line, fill=text_color, font=normal_font)
        y += 20

    # 수익률 정보 (있는 경우)
    if market_status.current_price and market_status.current_profit_rate is not None:
        y += 10
        draw.text((20, y), "📊 실시간 수익률", fill=header_color, font=title_font)
        y += 30

        # 현재가
        draw.text(
            (20, y),
            f"현재가: {_format_korean_amount(float(market_status.current_price))}원",
            fill=text_color,
            font=normal_font,
        )
        y += 20

        # 평가금액
        if market_status.current_value:
            draw.text(
                (20, y),
                f"현재 평가금액: {_format_korean_amount(float(market_status.current_value))}원",
                fill=text_color,
                font=normal_font,
            )
            y += 20

        # 수익률
        profit_rate = float(market_status.current_profit_rate) * 100
        if profit_rate > 0:
            profit_color = green_color
            profit_text = f"현재 수익률: +{profit_rate:.2f}%"
        elif profit_rate < 0:
            profit_color = red_color
            profit_text = f"현재 수익률: {profit_rate:.2f}%"
        else:
            profit_color = gray_color
            profit_text = "현재 수익률: 0.00%"

        draw.text((20, y), profit_text, fill=profit_color, font=normal_font)
        y += 20

        # 손익 금액
        if market_status.profit_loss_amount is not None:
            profit_loss = float(market_status.profit_loss_amount)
            if profit_loss > 0:
                profit_loss_color = green_color
                profit_loss_text = f"손익 금액: +{_format_korean_amount(profit_loss)}원"
            elif profit_loss < 0:
                profit_loss_color = red_color
                profit_loss_text = (
                    f"손익 금액: -{_format_korean_amount(abs(profit_loss))}원"
                )
            else:
                profit_loss_color = gray_color
                profit_loss_text = "손익 금액: ±0원"

            draw.text(
                (20, y), profit_loss_text, fill=profit_loss_color, font=normal_font
            )

    # 이미지를 BytesIO로 변환
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    return img_bytes
