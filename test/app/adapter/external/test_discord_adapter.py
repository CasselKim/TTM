from app.adapters.external.discord.notification_adapter import _truncate_field_value


class TestDiscordAdapter:
    """Discord 어댑터 테스트"""

    def test_truncate_field_value_short_text(self) -> None:
        """짧은 텍스트는 그대로 반환"""
        short_text = "This is a short text"
        result = _truncate_field_value(short_text)
        assert result == short_text

    def test_truncate_field_value_exact_limit(self) -> None:
        """정확히 1024자인 텍스트는 그대로 반환"""
        exact_text = "A" * 1024
        result = _truncate_field_value(exact_text)
        assert result == exact_text
        assert len(result) == 1024

    def test_truncate_field_value_over_limit(self) -> None:
        """1024자를 초과하는 텍스트는 자르고 '...' 추가"""
        long_text = "A" * 1030
        result = _truncate_field_value(long_text)

        assert len(result) == 1024
        assert result.endswith("...")
        assert result[:-3] == "A" * 1021

    def test_truncate_field_value_custom_limit(self) -> None:
        """사용자 정의 길이 제한 테스트"""
        text = "A" * 50
        result = _truncate_field_value(text, max_length=30)

        assert len(result) == 30
        assert result.endswith("...")
        assert result[:-3] == "A" * 27

    def test_truncate_field_value_empty_string(self) -> None:
        """빈 문자열 처리"""
        result = _truncate_field_value("")
        assert result == ""

    def test_truncate_field_value_very_short_limit(self) -> None:
        """매우 짧은 제한 길이 처리"""
        text = "Hello World"
        result = _truncate_field_value(text, max_length=5)

        assert len(result) == 5
        assert result == "He..."
