from decimal import Decimal
from pydantic import BaseModel
from app.domain.models.dca import DcaConfig


class DcaConfigDTO(BaseModel):
    initial_buy_amount: int | None = None
    add_buy_multiplier: Decimal | None = None
    target_profit_rate: Decimal | None = None
    price_drop_threshold: Decimal | None = None
    force_stop_loss_rate: Decimal | None = None
    max_buy_rounds: int | None = None
    max_investment_ratio: Decimal | None = None
    min_buy_interval_minutes: int | None = None
    max_cycle_days: int | None = None
    time_based_buy_interval_hours: int | None = None
    enable_time_based_buying: bool | None = None

    def to_entity(self) -> DcaConfig:
        dto_dict = self.model_dump(exclude_none=True)
        return DcaConfig(**dto_dict)
