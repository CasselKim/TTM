#!/usr/bin/env python3
"""폰트 로딩 테스트 스크립트"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.internal.websocket.image_generator import (
    _get_korean_font,
    _get_korean_font_candidates,
    _get_system_font_paths,
    _test_korean_support,
)


def test_font_loading() -> bool:
    """폰트 로딩 테스트"""
    print("=== 폰트 로딩 테스트 ===")

    # 시스템 폰트 경로 확인
    print("\n1. 시스템 폰트 경로:")
    font_paths = _get_system_font_paths()
    for path in font_paths:
        print(f"  - {path} (존재: {path.exists()})")

    # 폰트 후보 목록
    print("\n2. 폰트 후보 목록:")
    candidates = _get_korean_font_candidates()
    for candidate in candidates[:5]:  # 처음 5개만 출력
        print(f"  - {candidate}")
    print(f"  ... 총 {len(candidates)}개 후보")

    # 실제 폰트 로딩 테스트
    print("\n3. 폰트 로딩 테스트:")
    try:
        font = _get_korean_font(14)
        print(f"  ✓ 폰트 로딩 성공: {type(font)}")

        # 한글 지원 테스트
        korean_support = _test_korean_support(font)
        print(f"  ✓ 한글 지원: {korean_support}")

        # 테스트 이미지 생성
        from PIL import Image, ImageDraw

        test_img = Image.new("RGB", (300, 100), (255, 255, 255))
        draw = ImageDraw.Draw(test_img)

        test_text = "한글 테스트 1234 ABC"
        draw.text((10, 30), test_text, fill=(0, 0, 0), font=font)

        # 결과 저장
        output_path = project_root / "font_test_result.png"
        test_img.save(output_path)
        print(f"  ✓ 테스트 이미지 생성: {output_path}")

    except Exception as e:
        print(f"  ✗ 폰트 로딩 실패: {e}")
        return False

    print("\n=== 테스트 완료 ===")
    return True


if __name__ == "__main__":
    import logging

    # 로깅 설정
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")

    success = test_font_loading()
    sys.exit(0 if success else 1)
