from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class EmbedFooter(BaseModel):
    """Discord Embed Footer 모델"""

    text: str
    icon_url: str | None = None


class EmbedAuthor(BaseModel):
    """Discord Embed Author 모델"""

    name: str
    url: str | None = None
    icon_url: str | None = None


class EmbedField(BaseModel):
    """Discord Embed Field 모델"""

    name: str
    value: str
    inline: bool = False


class Embed(BaseModel):
    """Discord Embed 모델"""

    title: str | None = None
    description: str | None = None
    url: str | None = None
    timestamp: datetime | None = None
    color: int | None = None
    footer: EmbedFooter | None = None
    author: EmbedAuthor | None = None
    fields: list[EmbedField] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Discord API 형식으로 변환"""
        data: dict[str, Any] = {}

        if self.title:
            data["title"] = self.title
        if self.description:
            data["description"] = self.description
        if self.url:
            data["url"] = self.url
        if self.timestamp:
            data["timestamp"] = self.timestamp.isoformat()
        if self.color is not None:
            data["color"] = self.color
        if self.footer:
            data["footer"] = self.footer.model_dump(exclude_none=True)
        if self.author:
            data["author"] = self.author.model_dump(exclude_none=True)
        if self.fields:
            data["fields"] = [field.model_dump() for field in self.fields]

        return data


class WebhookMessage(BaseModel):
    """Discord Webhook 메시지 모델"""

    content: str | None = None
    username: str | None = None
    avatar_url: str | None = None
    embeds: list[Embed] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Discord API 형식으로 변환"""
        data: dict[str, Any] = {}

        if self.content:
            data["content"] = self.content
        if self.username:
            data["username"] = self.username
        if self.avatar_url:
            data["avatar_url"] = self.avatar_url
        if self.embeds:
            data["embeds"] = [embed.to_dict() for embed in self.embeds]

        return data
