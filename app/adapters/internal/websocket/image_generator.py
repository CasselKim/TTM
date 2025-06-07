"""Discord 봇용 이미지 생성 모듈"""

import io
import logging
import os
import platform
from pathlib import Path
from typing import Any, TypedDict

from PIL import Image, ImageDraw, ImageFont  # type: ignore

logger = logging.getLogger(__name__)


class CryptoData(TypedDict):
    """암호화폐 데이터 타입"""

    currency: str
    volume: float
    current_price: float
    current_value: float
    avg_buy_price: float
    investment_amount: float
    profit_rate: float
    profit_loss: float


def _get_system_font_paths() -> list[Path]:
    """운영체제별 시스템 폰트 경로를 반환"""
    system = platform.system().lower()
    paths = []

    if system == "linux":
        paths.extend(
            [
                Path("/usr/share/fonts/truetype/noto"),
                Path("/usr/share/fonts/truetype/nanum"),
                Path("/usr/share/fonts/truetype/dejavu"),
                Path("/usr/share/fonts/opentype/noto"),
                Path("/usr/local/share/fonts"),
                Path("/usr/share/fonts"),
            ]
        )
    elif system == "darwin":  # macOS
        paths.extend(
            [
                Path("/Library/Fonts"),
                Path("/System/Library/Fonts"),
                Path(os.path.expanduser("~/Library/Fonts")),
            ]
        )
    elif system == "windows":
        paths.extend(
            [
                Path("C:/Windows/Fonts"),
            ]
        )

    return [p for p in paths if p.exists()]


def _get_korean_font_candidates() -> list[str]:
    """한글을 지원하는 폰트 후보 목록을 반환"""
    return [
        # Noto Sans KR (Google Fonts)
        "NotoSansKR-Regular.ttf",
        "NotoSansKR-Bold.ttf",
        "NotoSansCJK-Regular.ttc",
        "NotoSansCJKkr-Regular.otf",
        # 나눔고딕
        "NanumGothic.ttf",
        "NanumGothicBold.ttf",
        "NanumBarunGothic.ttf",
        # 맑은고딕 (Windows)
        "malgun.ttf",
        "malgunbd.ttf",
        # 애플고딕 (macOS)
        "AppleGothic.ttf",
        "AppleSDGothicNeo.ttc",
        # DejaVu (Linux fallback with some Korean support)
        "DejaVuSans.ttf",
        "DejaVuSans-Bold.ttf",
    ]


def _test_korean_support(font: Any) -> bool:
    """폰트가 한글을 지원하는지 테스트"""
    try:
        # 간단한 한글 문자로 테스트
        test_text = "한글"
        # getbbox 메서드로 텍스트 크기 계산 시도
        if hasattr(font, "getbbox"):
            bbox = font.getbbox(test_text)
            # bbox는 (left, top, right, bottom) 튜플
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            return bool(width > 0 and height > 0)
        else:
            # 구버전 Pillow의 경우 textsize 사용
            size = font.getsize(test_text)
            return bool(size[0] > 0 and size[1] > 0)
    except (UnicodeError, OSError):
        return False


def _get_korean_font(size: int) -> Any:
    """한글을 지원하는 폰트를 찾아서 반환"""

    # 환경변수로 폰트 경로 오버라이드 가능
    env_font_path = os.getenv("TTM_KOREAN_FONT_PATH")
    if env_font_path:
        env_path = Path(env_font_path)
        if env_path.exists():
            try:
                font = ImageFont.truetype(str(env_path), size)
                if _test_korean_support(font):
                    logger.info(f"Using environment font: {env_path}")
                    return font
                else:
                    logger.warning(
                        f"Environment font {env_path} does not support Korean"
                    )
            except (OSError, IOError) as e:
                logger.warning(f"Failed to load environment font {env_path}: {e}")

    # 프로젝트에 번들된 폰트 경로
    project_root = Path(__file__).parent.parent.parent.parent
    bundled_font_dir = project_root / "assets" / "fonts"

    # 모든 폰트 후보 경로 수집
    font_candidates = _get_korean_font_candidates()
    search_paths = [bundled_font_dir] + _get_system_font_paths()

    logger.debug(f"Searching for Korean fonts in {len(search_paths)} directories")

    # 번들된 폰트부터 우선 시도
    for font_name in font_candidates:
        for search_path in search_paths:
            font_path = search_path / font_name
            if font_path.exists():
                try:
                    font = ImageFont.truetype(str(font_path), size)
                    if _test_korean_support(font):
                        logger.info(f"Successfully loaded Korean font: {font_path}")
                        return font
                    else:
                        logger.debug(
                            f"Font {font_path} exists but doesn't support Korean"
                        )
                except (OSError, IOError) as e:
                    logger.debug(f"Failed to load font {font_path}: {e}")
                    continue

    # 모든 후보를 시도했지만 한글 지원 폰트를 찾지 못한 경우
    logger.warning(
        "No Korean-supporting font found. Using default font (Korean text may not display correctly)"
    )

    # 기본 폰트로 폴백하되, 더 큰 사이즈로 가독성 향상
    try:
        return ImageFont.load_default()
    except Exception as e:
        logger.error(f"Failed to load default font: {e}")
        # 최후의 수단: PIL의 기본 내장 폰트
        return ImageFont.load_default()


def _draw_section_header(
    draw: Any,
    x: int,
    y: int,
    text: str,
    icon_color: tuple[int, int, int],
    text_color: tuple[int, int, int],
    font: Any,
) -> None:
    """섹션 헤더를 그립니다 (색상 박스 제거)"""
    # 단순히 텍스트만 그리기 (색상 박스 제거)
    draw.text((x, y), text, fill=text_color, font=font)


def _format_korean_amount(amount: float) -> str:
    """큰 숫자를 한국식 단위(만, 억)로 표시"""
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
        formatted = f"{amount:.8f}".rstrip("0").rstrip(".")
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

    # 이미지 크기 설정 (여백 최소화)
    width = 800
    base_height = 150  # 기본 높이 감소 (250 → 150)
    row_height = 30  # 각 암호화폐 행 높이 감소 (40 → 30)
    height = (
        base_height + len(crypto_data) * row_height + 150
    )  # 하단 여백 감소 (200 → 50)

    # 색상 정의 (색상 최소화)
    bg_color = (54, 57, 63)  # Discord 다크 배경색
    text_color = (255, 255, 255)  # 흰색 텍스트
    header_color = (255, 255, 255)  # 연한 회색 (헤더용)
    green_color = (87, 242, 135)  # 수익 색상 (수익률용만)
    red_color = (237, 66, 69)  # 손실 색상 (수익률용만)
    gray_color = (153, 170, 181)  # 중성 색상

    # 이미지 생성
    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    # 폰트 설정 (한글 지원 폰트 사용)
    title_font = _get_korean_font(20)
    header_font = _get_korean_font(14)
    normal_font = _get_korean_font(12)

    # 시작 Y 위치 (여백 감소)
    y = 10

    # 제목
    _draw_section_header(draw, 20, y, "계좌 잔고", gray_color, text_color, title_font)
    y += 25  # 제목 후 간격 감소 (50 → 25)

    # KRW 섹션
    _draw_section_header(draw, 20, y, "원화", gray_color, header_color, header_font)
    y += 25  # 헤더 후 간격 조정 (20 → 25)
    draw.text(
        (40, y),
        f"보유 금액: {_format_korean_amount(krw_amount)}원",
        fill=text_color,
        font=normal_font,
    )
    y += 35  # 섹션 간격 조정 (30 → 35)

    # 암호화폐 섹션
    if crypto_data:
        _draw_section_header(
            draw, 20, y, "암호화폐", gray_color, header_color, header_font
        )
        y += 25  # 헤더 후 간격 조정 (20 → 25)

        # 테이블 헤더
        headers = ["통화", "수량", "현재가", "평가금액", "평균단가", "수익률", "손익"]
        col_widths = [60, 100, 80, 80, 80, 80, 80]
        x_positions = [20]

        for width in col_widths[:-1]:
            x_positions.append(x_positions[-1] + width)

        # 헤더 그리기
        for i, header in enumerate(headers):
            draw.text(
                (x_positions[i], y),
                header,
                fill=gray_color,
                font=header_font,
            )
        y += 18  # 헤더 후 간격 조정 (15 → 18)

        # 각 암호화폐 데이터 그리기
        for crypto in crypto_data:
            currency = crypto["currency"][:6]  # 통화명 제한
            volume = _format_currency_amount(crypto["volume"], crypto["currency"])
            current_price = _format_korean_amount(crypto["current_price"])
            current_value = _format_korean_amount(crypto["current_value"])
            avg_price = _format_korean_amount(crypto["avg_buy_price"])

            # 수익률 색상 결정 (오직 수익률에만 색상 적용)
            profit_rate = crypto["profit_rate"]
            if profit_rate > 0:
                profit_color = green_color
                profit_text = f"+{profit_rate:.2f}%"
            elif profit_rate < 0:
                profit_color = red_color
                profit_text = f"{profit_rate:.2f}%"
            else:
                profit_color = gray_color
                profit_text = "0.00%"

            # 손익 금액 (오직 손익 금액에만 색상 적용)
            profit_loss = crypto["profit_loss"]
            if profit_loss > 0:
                loss_color = green_color
                loss_text = f"+{_format_korean_amount(profit_loss)}"
            elif profit_loss < 0:
                loss_color = red_color
                loss_text = f"-{_format_korean_amount(abs(profit_loss))}"
            else:
                loss_color = gray_color
                loss_text = "±0"

            # 데이터 행 그리기 (기본 데이터는 흰색)
            data = [currency, volume, current_price, current_value, avg_price]

            for i, value in enumerate(data):
                draw.text(
                    (x_positions[i], y),
                    str(value),
                    fill=text_color,
                    font=normal_font,
                )

            # 수익률과 손익은 색상 적용
            draw.text(
                (x_positions[5], y),
                profit_text,
                fill=profit_color,
                font=normal_font,
            )
            draw.text(
                (x_positions[6], y),
                loss_text,
                fill=loss_color,
                font=normal_font,
            )

            y += row_height

    # 요약 섹션
    y += 35  # 섹션 간격 조정 (20 → 35)
    _draw_section_header(
        draw, 20, y, "포트폴리오 요약", gray_color, header_color, header_font
    )
    y += 25  # 헤더 후 간격 조정 (20 → 25)

    # 총 평가금액
    draw.text(
        (40, y),
        f"총 평가금액: {_format_korean_amount(total_portfolio_value)}원",
        fill=text_color,
        font=normal_font,
    )
    y += 18  # 줄 간격 조정 (15 → 18)

    # 총 투자금액
    draw.text(
        (40, y),
        f"총 투자금액: {_format_korean_amount(total_portfolio_investment)}원",
        fill=text_color,
        font=normal_font,
    )
    y += 18  # 줄 간격 조정 (15 → 18)

    # 총 수익률 (오직 수익률에만 색상 적용)
    if total_profit_rate > 0:
        total_color = green_color
        total_text = f"총 수익률: +{total_profit_rate:.2f}% (+{_format_korean_amount(total_profit_loss)}원)"
    elif total_profit_rate < 0:
        total_color = red_color
        total_text = f"총 수익률: {total_profit_rate:.2f}% (-{_format_korean_amount(abs(total_profit_loss))}원)"
    else:
        total_color = gray_color
        total_text = "총 수익률: 0.00% (±0원)"

    draw.text(
        (40, y),
        total_text,
        fill=total_color,
        font=normal_font,
    )

    # 이미지를 BytesIO로 변환
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="PNG")
    img_byte_arr.seek(0)

    return img_byte_arr


def create_infinite_buying_image(market_status: Any) -> io.BytesIO:
    """무한매수법 상태를 이미지로 생성"""

    # 이미지 크기 설정
    width = 800
    height = 450

    # 색상 정의 (색상 최소화)
    bg_color = (54, 57, 63)  # Discord 다크 배경색
    text_color = (255, 255, 255)  # 흰색 텍스트
    header_color = (220, 220, 220)  # 연한 회색 (헤더용)
    green_color = (87, 242, 135)  # 수익 색상 (수익률용만)
    red_color = (237, 66, 69)  # 손실 색상 (수익률용만)
    gray_color = (153, 170, 181)  # 중성 색상

    # 이미지 생성
    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    # 폰트 설정
    title_font = _get_korean_font(20)
    header_font = _get_korean_font(14)
    normal_font = _get_korean_font(12)

    # 시작 Y 위치
    y = 20

    # 제목
    market = getattr(market_status, "market", "N/A")
    _draw_section_header(
        draw, 20, y, f"{market} 무한매수법 상태", gray_color, text_color, title_font
    )
    y += 50

    # 기본 정보 섹션
    _draw_section_header(
        draw, 20, y, "기본 정보", gray_color, header_color, header_font
    )
    y += 30

    # 상태 정보
    phase = getattr(market_status, "phase", "N/A")
    current_round = getattr(market_status, "current_round", 0)
    cycle_id = getattr(market_status, "cycle_id", "N/A")

    draw.text((40, y), f"상태: {phase}", fill=text_color, font=normal_font)
    y += 20
    draw.text(
        (40, y), f"현재 회차: {current_round}회", fill=text_color, font=normal_font
    )
    y += 20
    draw.text((40, y), f"사이클 ID: {cycle_id}", fill=gray_color, font=normal_font)
    y += 40

    # 투자 정보 섹션
    _draw_section_header(
        draw, 20, y, "투자 정보", gray_color, header_color, header_font
    )
    y += 30

    total_investment = float(getattr(market_status, "total_investment", 0))
    average_price = float(getattr(market_status, "average_price", 0))
    target_sell_price = float(getattr(market_status, "target_sell_price", 0))

    draw.text(
        (40, y),
        f"총 투자액: {_format_korean_amount(total_investment)}원",
        fill=text_color,
        font=normal_font,
    )
    y += 20
    draw.text(
        (40, y),
        f"평균 단가: {_format_korean_amount(average_price)}원",
        fill=text_color,
        font=normal_font,
    )
    y += 20
    draw.text(
        (40, y),
        f"목표 가격: {_format_korean_amount(target_sell_price)}원",
        fill=text_color,
        font=normal_font,
    )
    y += 40

    # 현재 수익 정보 (있는 경우)
    current_price = getattr(market_status, "current_price", None)
    current_profit_rate = getattr(market_status, "current_profit_rate", None)
    profit_loss_amount = getattr(market_status, "profit_loss_amount", None)

    if current_price and current_profit_rate is not None:
        _draw_section_header(
            draw, 20, y, "현재 수익 정보", gray_color, header_color, header_font
        )
        y += 30

        draw.text(
            (40, y),
            f"현재가: {_format_korean_amount(float(current_price))}원",
            fill=text_color,
            font=normal_font,
        )
        y += 20

        # 수익률 색상 결정 (오직 수익률에만 색상 적용)
        profit_rate_percent = float(current_profit_rate) * 100
        if profit_rate_percent > 0:
            profit_color = green_color
            profit_text = f"현재 수익률: +{profit_rate_percent:.2f}%"
        elif profit_rate_percent < 0:
            profit_color = red_color
            profit_text = f"현재 수익률: {profit_rate_percent:.2f}%"
        else:
            profit_color = gray_color
            profit_text = "현재 수익률: 0.00%"

        draw.text((40, y), profit_text, fill=profit_color, font=normal_font)
        y += 20

        # 손익 금액 (오직 손익 금액에만 색상 적용)
        if profit_loss_amount is not None:
            profit_loss = float(profit_loss_amount)
            if profit_loss > 0:
                loss_color = green_color
                loss_text = f"손익 금액: +{_format_korean_amount(profit_loss)}원"
            elif profit_loss < 0:
                loss_color = red_color
                loss_text = f"손익 금액: -{_format_korean_amount(abs(profit_loss))}원"
            else:
                loss_color = gray_color
                loss_text = "손익 금액: ±0원"

            draw.text((40, y), loss_text, fill=loss_color, font=normal_font)

    # 이미지를 BytesIO로 변환
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="PNG")
    img_byte_arr.seek(0)

    return img_byte_arr
