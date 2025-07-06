import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from app.application.usecase.account_usecase import AccountUseCase
from app.application.usecase.dca_usecase import DcaUsecase
from app.application.usecase.discord_ui_usecase import DiscordUIUseCase
from app.application.usecase.order_usecase import OrderUseCase
from app.application.usecase.ticker_usecase import TickerUseCase
from common.discord.bot import DiscordBot
from common.discord.ui import (
    execute_trade_direct,
    DcaSelectionView,
    is_embed_valid,
    create_fallback_embed,
)

logger = logging.getLogger(__name__)


class DiscordCommandAdapter(commands.Cog):
    """Discord 명령어 어댑터"""

    def __init__(
        self,
        bot: DiscordBot,
        account_usecase: AccountUseCase,
        ticker_usecase: TickerUseCase,
        order_usecase: OrderUseCase,
        dca_usecase: DcaUsecase,
        ui_usecase: DiscordUIUseCase,
    ) -> None:
        super().__init__()
        self.bot = bot
        self.account_usecase = account_usecase
        self.ticker_usecase = ticker_usecase
        self.order_usecase = order_usecase
        self.dca_usecase = dca_usecase
        self.ui_usecase = ui_usecase

    @app_commands.command(
        name="balance", description="현재 보유 자산 현황을 확인합니다"
    )
    async def balance_command(self, interaction: discord.Interaction) -> None:
        """잔고 조회 Slash Command"""
        await interaction.response.defer(ephemeral=True)
        try:
            user_id = str(interaction.user.id)
            logger.info(f"잔고 조회 시작 (user_id: {user_id})")

            embed = await self.ui_usecase.create_balance_embed(user_id)
            logger.info(f"embed 생성 완료 (user_id: {user_id})")

            if not is_embed_valid(embed):
                logger.warning(f"유효하지 않은 잔고 embed 생성됨 (user_id: {user_id})")
                embed = create_fallback_embed("잔고")

            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(f"잔고 조회 응답 완료 (user_id: {user_id})")
        except Exception as e:
            logger.exception(
                f"잔고 조회 중 오류 발생 (user_id: {interaction.user.id}): {e}"
            )
            embed = discord.Embed(
                title="❌ 오류 발생",
                description="잔고 조회 중 오류가 발생했습니다.\n잠시 후 다시 시도해주세요.",
                color=0xFF0000,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(
        name="dca_status", description="자동매매 진행 상황을 확인합니다"
    )
    @app_commands.describe(mode="출력 모드: 요약 또는 상세")
    @app_commands.choices(
        mode=[
            app_commands.Choice(name="요약", value="summary"),
            app_commands.Choice(name="상세", value="detail"),
        ]
    )
    async def dca_status_command(
        self,
        interaction: discord.Interaction,
        mode: Optional[app_commands.Choice[str]] = None,
    ) -> None:
        """DCA 상태 조회 Slash Command (요약/상세 선택)"""
        await interaction.response.defer(ephemeral=True)
        try:
            user_id = str(interaction.user.id)
            logger.info(
                f"DCA 상태 조회 시작 (user_id: {user_id}, mode: {mode.value if mode else 'summary'})"
            )

            if mode and mode.value == "detail":
                embed = await self.ui_usecase.create_dca_status_embed_detail(user_id)
            else:
                embed = await self.ui_usecase.create_dca_status_embed(user_id)
            logger.info(f"embed 생성 완료 (user_id: {user_id})")

            if not is_embed_valid(embed):
                logger.warning(
                    f"유효하지 않은 DCA 상태 embed 생성됨 (user_id: {user_id})"
                )
                embed = create_fallback_embed("DCA 상태")

            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(f"DCA 상태 조회 응답 완료 (user_id: {user_id})")
        except Exception as e:
            logger.exception(
                f"DCA 상태 조회 중 오류 발생 (user_id: {interaction.user.id}): {e}"
            )
            embed = discord.Embed(
                title="❌ 오류 발생",
                description="DCA 상태 조회 중 오류가 발생했습니다.\n잠시 후 다시 시도해주세요.",
                color=0xFF0000,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="profit", description="투자 수익률을 분석합니다")
    async def profit_command(self, interaction: discord.Interaction) -> None:
        """수익률 조회 Slash Command"""
        await interaction.response.defer(ephemeral=True)
        try:
            user_id = str(interaction.user.id)
            logger.info(f"수익률 조회 시작 (user_id: {user_id})")

            logger.debug(
                f"ui_usecase.create_profit_embed 호출 시작 (user_id: {user_id})"
            )
            embed = await self.ui_usecase.create_profit_embed(user_id)
            logger.debug(
                f"ui_usecase.create_profit_embed 호출 완료 (user_id: {user_id}), embed is None: {embed is None}"
            )

            logger.info(f"embed 생성 완료 (user_id: {user_id})")

            if not is_embed_valid(embed):
                logger.warning(
                    f"유효하지 않은 수익률 embed 생성됨 (user_id: {user_id})"
                )
                embed = create_fallback_embed("수익률")

            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(f"수익률 조회 응답 완료 (user_id: {user_id})")
        except Exception as e:
            logger.exception(
                f"수익률 조회 중 오류 발생 (user_id: {interaction.user.id}): {e}"
            )
            embed = discord.Embed(
                title="❌ 오류 발생",
                description="수익률 조회 중 오류가 발생했습니다.\n잠시 후 다시 시도해주세요.",
                color=0xFF0000,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(
        name="trade_start", description="새로운 자동매매를 시작합니다"
    )
    @app_commands.describe(
        symbol="코인 심볼 (예: BTC, ETH, DOGE)",
        amount="매수 금액 (KRW, 예: 100000 = 10만원)",
        total_count="총 매수 횟수 (예: 10)",
        interval_hours="매수 간격 (시간, 예: 24 = 24시간마다)",
        add_buy_multiplier="추가 매수 배수 (예: 1.5)",
        enable_smart_dca="Smart DCA 사용 여부",
        target_profit_rate="목표 수익률 (예: 0.1 = 10%)",
        price_drop_threshold="추가 매수 트리거 하락률 (예: -0.025 = -2.5%)",
        force_stop_loss_rate="강제 손절률 (예: -0.25 = -25%)",
        smart_dca_rho="Smart DCA ρ 파라미터 (예: 1.5, Smart DCA 활성화시만)",
        smart_dca_max_multiplier="Smart DCA 최대 투자 배수 (예: 5.0)",
        smart_dca_min_multiplier="Smart DCA 최소 투자 배수 (예: 0.1)",
    )
    async def trade_execute_command(
        self,
        interaction: discord.Interaction,
        symbol: str = "BTC",
        amount: int = 100000,
        total_count: int = 10,
        interval_hours: int = 24,
        add_buy_multiplier: float = 1.5,
        enable_smart_dca: bool = False,
        target_profit_rate: float = 0.1,
        price_drop_threshold: float = -0.025,
        force_stop_loss_rate: float = -0.25,
        smart_dca_rho: float = 1.5,
        smart_dca_max_multiplier: float = 5.0,
        smart_dca_min_multiplier: float = 0.1,
    ) -> None:
        """DCA 시작 Slash Command (직접 실행)"""
        logger.info(
            f"DCA 직접 실행 시작 (user_id: {interaction.user.id}, symbol: {symbol}, smart_dca: {enable_smart_dca})"
        )

        # advanced 옵션 구성
        advanced_options = {
            "target_profit_rate": target_profit_rate,
            "price_drop_threshold": price_drop_threshold,
            "force_stop_loss_rate": force_stop_loss_rate,
            "smart_dca_rho": smart_dca_rho,
            "smart_dca_max_multiplier": smart_dca_max_multiplier,
            "smart_dca_min_multiplier": smart_dca_min_multiplier,
        }

        # 직접 실행
        await execute_trade_direct(
            ui_usecase=self.ui_usecase,
            interaction=interaction,
            symbol=symbol,
            amount=amount,
            total_count=total_count,
            interval_hours=interval_hours,
            add_buy_multiplier=add_buy_multiplier,
            enable_smart_dca=enable_smart_dca,
            advanced_options=advanced_options,
        )

    @app_commands.command(
        name="trade_stop", description="진행 중인 자동매매를 중단합니다"
    )
    async def trade_stop_command(self, interaction: discord.Interaction) -> None:
        """매매 중단 Slash Command"""
        await interaction.response.defer(ephemeral=True)

        try:
            user_id = str(interaction.user.id)
            dca_list = await self.ui_usecase.get_active_dca_list(user_id)

            if not dca_list:
                embed = discord.Embed(
                    title="ℹ️ 진행중인 DCA 없음",
                    description="현재 진행중인 DCA가 없습니다.\n\n"
                    "새로운 DCA를 시작하려면 `/trade_start` 커맨드를 사용하세요.",
                    color=0x808080,
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            embed = discord.Embed(
                title="⏹️ DCA 중단 선택",
                description=f"**{len(dca_list)}개의 진행중인 DCA**가 있습니다.\n\n"
                "중단할 DCA를 선택해주세요:\n\n"
                "• 🛑 **중단만 하기**: DCA만 중단하고 코인은 보관\n"
                "• 💸 **강제매도**: DCA 중단 후 보유 코인 전량 매도",
                color=0xFF8C00,
            )

            view = DcaSelectionView(self.ui_usecase, dca_list)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            logger.info(
                f"DCA 중단 화면 표시 완료 (user_id: {user_id}, DCA 개수: {len(dca_list)})"
            )

        except Exception as e:
            logger.exception(
                f"DCA 중단 화면 표시 중 오류 (user_id: {interaction.user.id}): {e}"
            )
            embed = discord.Embed(
                title="❌ 오류 발생",
                description="DCA 목록을 불러오는 중 오류가 발생했습니다.\n잠시 후 다시 시도해주세요.",
                color=0xFF0000,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(
        name="update_dca_config", description="진행 중인 DCA의 설정을 변경합니다"
    )
    @app_commands.describe(
        target_profit_rate="목표 수익률 (예: 0.1 = 10%)",
        price_drop_threshold="추가 매수 트리거 하락률 (예: -0.025 = -2.5%)",
        force_stop_loss_rate="강제 손절률 (예: -0.25 = -25%)",
        add_buy_multiplier="추가 매수 배수 (예: 1.5)",
        enable_smart_dca="Smart DCA 사용 여부",
        smart_dca_rho="Smart DCA ρ 파라미터 (예: 1.5)",
        smart_dca_max_multiplier="Smart DCA 최대 투자 배수 (예: 5.0)",
        smart_dca_min_multiplier="Smart DCA 최소 투자 배수 (예: 0.1)",
        time_interval_hours="시간 기반 매수 간격 (시간, 예: 24)",
        enable_time_based="시간 기반 매수 활성화 여부",
        max_rounds="최대 매수 회차 (예: 10)",
    )
    async def update_dca_config_command(
        self,
        interaction: discord.Interaction,
        target_profit_rate: float | None = None,
        price_drop_threshold: float | None = None,
        force_stop_loss_rate: float | None = None,
        add_buy_multiplier: float | None = None,
        enable_smart_dca: bool | None = None,
        smart_dca_rho: float | None = None,
        smart_dca_max_multiplier: float | None = None,
        smart_dca_min_multiplier: float | None = None,
        time_interval_hours: int | None = None,
        enable_time_based: bool | None = None,
        max_rounds: int | None = None,
    ) -> None:
        """DCA 설정 변경 Slash Command"""
        await interaction.response.defer(ephemeral=True)

        try:
            user_id = str(interaction.user.id)
            logger.info(f"DCA 설정 변경 요청 (user_id: {user_id})")

            # 1. 진행중인 DCA 목록 조회
            dca_list = await self.ui_usecase.get_active_dca_list(user_id)

            if not dca_list:
                embed = discord.Embed(
                    title="ℹ️ 진행중인 DCA 없음",
                    description="현재 진행중인 DCA가 없습니다.\n\n"
                    "새로운 DCA를 시작하려면 `/trade_start` 커맨드를 사용하세요.",
                    color=0x808080,
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # 2. 첫 번째 DCA의 설정 변경 (단일 사용자 가정)
            first_dca = dca_list[0]
            market = first_dca["market"]

            # 3. Decimal 변환
            from decimal import Decimal
            from typing import Any

            kwargs: dict[str, Any] = {}
            if target_profit_rate is not None:
                kwargs["target_profit_rate"] = Decimal(str(target_profit_rate))
            if price_drop_threshold is not None:
                kwargs["price_drop_threshold"] = Decimal(str(price_drop_threshold))
            if force_stop_loss_rate is not None:
                kwargs["force_stop_loss_rate"] = Decimal(str(force_stop_loss_rate))
            if add_buy_multiplier is not None:
                kwargs["add_buy_multiplier"] = Decimal(str(add_buy_multiplier))
            if enable_smart_dca is not None:
                kwargs["enable_smart_dca"] = enable_smart_dca
            if smart_dca_rho is not None:
                kwargs["smart_dca_rho"] = Decimal(str(smart_dca_rho))
            if smart_dca_max_multiplier is not None:
                kwargs["smart_dca_max_multiplier"] = Decimal(
                    str(smart_dca_max_multiplier)
                )
            if smart_dca_min_multiplier is not None:
                kwargs["smart_dca_min_multiplier"] = Decimal(
                    str(smart_dca_min_multiplier)
                )
            if time_interval_hours is not None:
                kwargs["time_based_buy_interval_hours"] = time_interval_hours
            if enable_time_based is not None:
                kwargs["enable_time_based_buying"] = enable_time_based
            if max_rounds is not None:
                kwargs["max_buy_rounds"] = max_rounds

            # 4. 설정 변경할 값이 있는지 확인
            if not kwargs:
                embed = discord.Embed(
                    title="⚠️ 변경할 설정 없음",
                    description="변경할 설정 값을 입력해주세요.\n\n"
                    "사용 가능한 옵션:\n"
                    "• `target_profit_rate`: 목표 수익률\n"
                    "• `price_drop_threshold`: 추가 매수 트리거 하락률\n"
                    "• `force_stop_loss_rate`: 강제 손절률\n"
                    "• `add_buy_multiplier`: 추가 매수 배수\n"
                    "• `enable_smart_dca`: Smart DCA 활성화\n"
                    "• `smart_dca_rho`: Smart DCA ρ 파라미터\n"
                    "• `max_rounds`: 최대 매수 회차",
                    color=0xFFA500,
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # 5. 설정 변경 실행
            result = await self.ui_usecase.update_dca_config(
                user_id=user_id,
                market=market,
                **kwargs,
            )

            # 6. 결과 응답
            if result["success"]:
                config = result["updated_config"]
                embed = discord.Embed(
                    title="✅ DCA 설정 변경 완료",
                    description=f"**{result['symbol']}** DCA의 설정이 변경되었습니다.",
                    color=0x00FF00,
                )

                # 변경된 설정만 표시
                changed_fields = []
                if target_profit_rate is not None:
                    changed_fields.append(
                        ("목표 수익률", f"{config['target_profit_rate']:.1%}", True)
                    )
                if price_drop_threshold is not None:
                    changed_fields.append(
                        (
                            "추가 매수 하락률",
                            f"{config['price_drop_threshold']:.1%}",
                            True,
                        )
                    )
                if force_stop_loss_rate is not None:
                    changed_fields.append(
                        ("강제 손절률", f"{config['force_stop_loss_rate']:.1%}", True)
                    )
                if add_buy_multiplier is not None:
                    changed_fields.append(
                        ("추가 매수 배수", f"{config['add_buy_multiplier']:.1f}x", True)
                    )
                if enable_smart_dca is not None:
                    smart_status = (
                        "활성화" if config["enable_smart_dca"] else "비활성화"
                    )
                    changed_fields.append(("Smart DCA", smart_status, True))
                if smart_dca_rho is not None:
                    changed_fields.append(
                        ("Smart DCA ρ", f"{config['smart_dca_rho']:.1f}", True)
                    )
                if max_rounds is not None:
                    changed_fields.append(
                        ("최대 매수 회차", f"{config['max_buy_rounds']}회", True)
                    )
                if time_interval_hours is not None:
                    changed_fields.append(
                        (
                            "시간 기반 간격",
                            f"{config['time_based_buy_interval_hours']}시간",
                            True,
                        )
                    )
                if enable_time_based is not None:
                    time_status = (
                        "활성화" if config["enable_time_based_buying"] else "비활성화"
                    )
                    changed_fields.append(("시간 기반 매수", time_status, True))

                for name, value, inline in changed_fields:
                    embed.add_field(name=name, value=value, inline=inline)

            else:
                embed = discord.Embed(
                    title="❌ 설정 변경 실패",
                    description=f"DCA 설정 변경 중 오류가 발생했습니다.\n\n**오류**: {result['message']}",
                    color=0xFF0000,
                )

            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(f"DCA 설정 변경 응답 완료 (user_id: {user_id})")

        except Exception as e:
            logger.exception(
                f"DCA 설정 변경 중 오류 발생 (user_id: {interaction.user.id}): {e}"
            )
            embed = discord.Embed(
                title="❌ 오류 발생",
                description="DCA 설정 변경 중 오류가 발생했습니다.\n잠시 후 다시 시도해주세요.",
                color=0xFF0000,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
