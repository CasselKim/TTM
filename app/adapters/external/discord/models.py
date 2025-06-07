from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class EmbedFooter(BaseModel):
    """Discord Embed Footer 모델"""

    model_config = ConfigDict(populate_by_name=True, use_enum_values=True)

    text: str
    icon_url: str | None = None


class EmbedAuthor(BaseModel):
    """Discord Embed Author 모델"""

    model_config = ConfigDict(populate_by_name=True, use_enum_values=True)

    name: str
    url: str | None = None
    icon_url: str | None = None


class EmbedField(BaseModel):
    """Discord Embed Field 모델"""

    model_config = ConfigDict(populate_by_name=True, use_enum_values=True)

    name: str
    value: str
    inline: bool = False


class Embed(BaseModel):
    """Discord Embed 모델"""

    model_config = ConfigDict(populate_by_name=True, use_enum_values=True)

    title: str | None = None
    description: str | None = None
    url: str | None = None
    timestamp: datetime | None = None
    color: int | None = None
    footer: EmbedFooter | None = None
    author: EmbedAuthor | None = None
    fields: list[EmbedField] = Field(default_factory=list)

    @field_serializer("timestamp")
    def serialize_timestamp(self, dt: datetime | None) -> str | None:
        """datetime을 ISO 형식으로 직렬화"""
        return dt.isoformat() if dt else None

    def to_discord_dict(self) -> dict[str, Any]:
        """Discord API 형식으로 변환"""
        return self.model_dump(
            exclude_none=True,
            mode="json",  # JSON 호환 타입으로 변환
        )


class WebhookMessage(BaseModel):
    """Discord Webhook 메시지 모델"""

    model_config = ConfigDict(populate_by_name=True, use_enum_values=True)

    content: str | None = None
    username: str | None = None
    avatar_url: str | None = None
    embeds: list[Embed] = Field(default_factory=list)

    def to_discord_dict(self) -> dict[str, Any]:
        """Discord API 형식으로 변환"""
        # embeds를 올바르게 직렬화하기 위해 커스텀 처리
        data = self.model_dump(exclude_none=True, exclude={"embeds"})

        if self.embeds:
            data["embeds"] = [embed.to_discord_dict() for embed in self.embeds]

        return data
