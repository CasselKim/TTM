"""
Technical Indicators for Smart DCA

Implements technical indicators for volatility and momentum analysis based on academic research.
Used to dynamically adjust DCA parameters based on market conditions.
"""

from decimal import Decimal
from typing import List, Optional, Tuple
import math


class TechnicalIndicators:
    """
    Technical indicators for smart DCA based on academic research.

    Implements:
    - ATR (Average True Range) for volatility measurement
    - RSI (Relative Strength Index) for momentum filtering
    - Bollinger Bands for volatility bands
    - Value Averaging calculations for dynamic thresholds
    """

    @staticmethod
    def calculate_atr(
        high_prices: List[Decimal],
        low_prices: List[Decimal],
        close_prices: List[Decimal],
        period: int = 14,
    ) -> Optional[Decimal]:
        """
        Calculate Average True Range (ATR)

        Args:
            high_prices: List of high prices
            low_prices: List of low prices
            close_prices: List of closing prices
            period: Period for ATR calculation (default 14)

        Returns:
            ATR value or None if insufficient data
        """
        if (
            len(high_prices) < period + 1
            or len(low_prices) < period + 1
            or len(close_prices) < period + 1
        ):
            return None

        true_ranges = []
        for i in range(1, len(close_prices)):
            high_low = high_prices[i] - low_prices[i]
            high_close = abs(high_prices[i] - close_prices[i - 1])
            low_close = abs(low_prices[i] - close_prices[i - 1])
            true_range = max(high_low, high_close, low_close)
            true_ranges.append(true_range)

        if len(true_ranges) < period:
            return None

        # Simple moving average of true ranges
        atr = sum(true_ranges[-period:]) / Decimal(str(period))
        return atr

    @staticmethod
    def calculate_rsi(prices: List[Decimal], period: int = 14) -> Optional[Decimal]:
        """
        Calculate Relative Strength Index (RSI)

        Args:
            prices: List of closing prices
            period: Period for RSI calculation (default 14)

        Returns:
            RSI value (0-100) or None if insufficient data
        """
        if len(prices) < period + 1:
            return None

        gains = []
        losses = []

        for i in range(1, len(prices)):
            change = prices[i] - prices[i - 1]
            if change > 0:
                gains.append(change)
                losses.append(Decimal("0"))
            else:
                gains.append(Decimal("0"))
                losses.append(abs(change))

        if len(gains) < period:
            return None

        avg_gain = sum(gains[-period:]) / Decimal(str(period))
        avg_loss = sum(losses[-period:]) / Decimal(str(period))

        if avg_loss == 0:
            return Decimal("100")

        rs = avg_gain / avg_loss
        rsi = Decimal("100") - (Decimal("100") / (Decimal("1") + rs))
        return rsi

    @staticmethod
    def calculate_bollinger_bands(
        prices: List[Decimal], period: int = 20, std_dev: float = 2.0
    ) -> Optional[Tuple[Decimal, Decimal, Decimal]]:
        """
        Calculate Bollinger Bands

        Args:
            prices: List of closing prices
            period: Period for moving average (default 20)
            std_dev: Standard deviation multiplier (default 2.0)

        Returns:
            Tuple of (lower_band, middle_band, upper_band) or None if insufficient data
        """
        if len(prices) < period:
            return None

        # Calculate simple moving average
        sma = sum(prices[-period:]) / Decimal(str(period))

        # Calculate standard deviation
        variance = sum((price - sma) ** 2 for price in prices[-period:]) / Decimal(
            str(period)
        )
        std = Decimal(str(math.sqrt(float(variance))))

        # Calculate bands
        std_multiplier = Decimal(str(std_dev))
        upper_band = sma + (std * std_multiplier)
        lower_band = sma - (std * std_multiplier)

        return lower_band, sma, upper_band

    @staticmethod
    def calculate_volatility_condition(
        atr: Decimal, atr_history: List[Decimal], period: int = 20
    ) -> str:
        """
        Determine volatility condition based on ATR

        Args:
            atr: Current ATR value
            atr_history: Historical ATR values
            period: Period for calculating average ATR

        Returns:
            Volatility condition: "HIGH", "NORMAL", or "LOW"
        """
        if len(atr_history) < period:
            return "NORMAL"

        avg_atr = sum(atr_history[-period:]) / Decimal(str(period))

        if atr > avg_atr * Decimal("1.5"):
            return "HIGH"
        elif atr < avg_atr * Decimal("0.8"):
            return "LOW"
        else:
            return "NORMAL"

    @staticmethod
    def calculate_value_averaging_target(
        initial_value: Decimal, monthly_growth_rate: Decimal, periods_elapsed: int
    ) -> Decimal:
        """
        Calculate Value Averaging target value

        Args:
            initial_value: Initial portfolio value
            monthly_growth_rate: Target monthly growth rate (e.g., 0.01 for 1%)
            periods_elapsed: Number of periods elapsed

        Returns:
            Target portfolio value
        """
        growth_factor = (Decimal("1") + monthly_growth_rate) ** periods_elapsed
        return initial_value * growth_factor

    @staticmethod
    def calculate_bollinger_width(
        upper_band: Decimal, lower_band: Decimal, middle_band: Decimal
    ) -> Decimal:
        """
        Calculate Bollinger Band width as percentage of middle band

        Args:
            upper_band: Upper Bollinger Band
            lower_band: Lower Bollinger Band
            middle_band: Middle Bollinger Band (SMA)

        Returns:
            Band width as percentage
        """
        if middle_band == 0:
            return Decimal("0")

        width = (upper_band - lower_band) / middle_band
        return width

    @staticmethod
    def is_oversold(rsi: Decimal, threshold: Decimal = Decimal("30")) -> bool:
        """Check if RSI indicates oversold condition"""
        return rsi < threshold

    @staticmethod
    def is_overbought(rsi: Decimal, threshold: Decimal = Decimal("70")) -> bool:
        """Check if RSI indicates overbought condition"""
        return rsi > threshold

    @staticmethod
    def is_below_lower_bollinger(price: Decimal, lower_band: Decimal) -> bool:
        """Check if price is below lower Bollinger Band"""
        return price < lower_band

    @staticmethod
    def is_above_upper_bollinger(price: Decimal, upper_band: Decimal) -> bool:
        """Check if price is above upper Bollinger Band"""
        return price > upper_band
