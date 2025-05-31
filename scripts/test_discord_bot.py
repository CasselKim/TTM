#!/usr/bin/env python3
"""Discord Bot 테스트 스크립트"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

# 스크립트 상수
DEFAULT_ASYNC_SLEEP_SECONDS = 1  # 기본 비동기 대기 시간

# 프로젝트 루트 경로를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

from app.adapters.secondary.discord import DiscordBotAdapter

# 환경 변수 로드
load_dotenv()


async def test_discord_bot():
    """Discord Bot 테스트"""
    bot_token = os.getenv("DISCORD_BOT_TOKEN")
    channel_id = os.getenv("DISCORD_CHANNEL_ID")

    if not bot_token:
        print("❌ DISCORD_BOT_TOKEN 환경 변수가 설정되지 않았습니다.")
        return

    if not channel_id:
        print("❌ DISCORD_CHANNEL_ID 환경 변수가 설정되지 않았습니다.")
        return

    # Discord 봇 어댑터 생성
    discord = DiscordBotAdapter(bot_token=bot_token, channel_id=int(channel_id))

    print("🤖 Discord Bot 테스트를 시작합니다...")

    # 봇 시작 (백그라운드)
    bot_task = asyncio.create_task(discord.start())

    try:
        # 봇이 준비될 때까지 대기
        print("⏳ Discord Bot이 준비될 때까지 대기 중...")
        await discord.wait_until_ready()
        print("✅ Discord Bot이 준비되었습니다!")

        # 1. 거래 체결 알림 테스트
        print("\n📊 거래 체결 알림 테스트...")
        success = await discord.send_trade_notification(
            market="KRW-BTC",
            side="BUY",
            price=85000000,
            volume=0.001,
            total_price=85000,
            fee=42.5,
            executed_at=datetime.now(),
        )
        print(f"✅ 매수 알림 전송: {'성공' if success else '실패'}")

        await asyncio.sleep(DEFAULT_ASYNC_SLEEP_SECONDS)

        success = await discord.send_trade_notification(
            market="KRW-ETH",
            side="SELL",
            price=3500000,
            volume=0.5,
            total_price=1750000,
            fee=875,
            executed_at=datetime.now(),
        )
        print(f"✅ 매도 알림 전송: {'성공' if success else '실패'}")

        # 2. 에러 알림 테스트
        print("\n⚠️ 에러 알림 테스트...")
        success = await discord.send_error_notification(
            error_type="OrderError",
            error_message="잔고가 부족합니다.",
            details="요청 금액: 1,000,000 KRW\n사용 가능 잔고: 500,000 KRW",
        )
        print(f"✅ 에러 알림 전송: {'성공' if success else '실패'}")

        # 3. 정보 알림 테스트
        print("\n📢 정보 알림 테스트...")
        success = await discord.send_info_notification(
            title="봇 테스트",
            message="Discord Bot 테스트가 진행 중입니다.",
            fields=[
                ("버전", "1.0.0", True),
                ("테스트 환경", "Local", True),
                ("시작 시간", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), False),
            ],
        )
        print(f"✅ 정보 알림 전송: {'성공' if success else '실패'}")

        # 4. 텍스트 메시지 테스트
        print("\n💬 텍스트 메시지 테스트...")
        success = await discord.send_message("Discord Bot 테스트 메시지입니다. 🚀")
        print(f"✅ 텍스트 메시지 전송: {'성공' if success else '실패'}")

        print("\n✨ Discord Bot 테스트가 완료되었습니다!")

    finally:
        # 봇 종료
        print("\n🔧 Discord Bot을 종료합니다...")
        await discord.close()
        bot_task.cancel()
        try:
            await bot_task
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":
    asyncio.run(test_discord_bot())
