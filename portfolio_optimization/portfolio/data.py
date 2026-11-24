
"""Load and validate OR-Library portfolio datasets.

AI-assisted implementation. See docs/ai_usage.md.

The source format is:
- First line: number of assets.
- Next n lines: expected return and standard deviation.
- Remaining n(n+1)/2 lines: 1-based asset indices and correlation.
"""

from dataclasses import dataclass
import math
from pathlib import Path


@dataclass(frozen=True)
class PortfolioData:
    """Immutable portfolio statistics for one benchmark dataset."""

    name: str
    returns: tuple[float, ...]
    std_devs: tuple[float, ...]
    correlation: tuple[tuple[float, ...], ...]
    covariance: tuple[tuple[float, ...], ...]

    @property
    def n_assets(self) -> int:
        return len(self.returns)


def parse_portfolio_text(
    text: str,
    name: str = "portfolio",
) -> PortfolioData:
    """Parse portfolio data and reject invalid or incomplete records."""

    rows = [
        (line_number, line.split())
        for line_number, line in enumerate(text.splitlines(), start=1)
        if line.strip()
    ]

    if not rows or len(rows[0][1]) != 1:
        raise ValueError("Expected asset count on the first line")

    try:
        n = int(rows[0][1][0])
    except ValueError as exc:
        raise ValueError("Invalid asset count") from exc

    if n <= 0:
        raise ValueError("Asset count must be positive")

    pair_count = n * (n + 1) // 2
    expected_lines = 1 + n + pair_count

    if len(rows) != expected_lines:
        raise ValueError(
            f"Expected {expected_lines} data lines for {n} assets, "
            f"found {len(rows)}"
        )

    returns = []
    std_devs = []

    for line_number, fields in rows[1 : 1 + n]:
        if len(fields) != 2:
            raise ValueError(
                f"Line {line_number}: expected return and standard deviation"
            )

        try:
            expected_return, std_dev = map(float, fields)
        except ValueError as exc:
            raise ValueError(
                f"Line {line_number}: invalid asset statistics"
            ) from exc

        if not math.isfinite(expected_return) or not math.isfinite(std_dev):
            raise ValueError(
                f"Line {line_number}: non-finite asset statistics"
            )

        if std_dev < 0:
            raise ValueError(
                f"Line {line_number}: negative standard deviation"
            )

        returns.append(expected_return)
        std_devs.append(std_dev)

    correlation = [[0.0] * n for _ in range(n)]
    seen_pairs = set()

    for line_number, fields in rows[1 + n :]:
        if len(fields) != 3:
            raise ValueError(
                f"Line {line_number}: expected two indices and correlation"
            )

        try:
            i = int(fields[0])
            j = int(fields[1])
            rho = float(fields[2])
        except ValueError as exc:
            raise ValueError(
                f"Line {line_number}: invalid correlation record"
            ) from exc

        if not 1 <= i <= n or not 1 <= j <= n:
            raise ValueError(
                f"Line {line_number}: asset index out of range"
            )

        if not math.isfinite(rho) or not -1.0 <= rho <= 1.0:
            raise ValueError(
                f"Line {line_number}: correlation must be finite "
                "and within [-1, 1]"
            )

        i -= 1
        j -= 1

        pair = (min(i, j), max(i, j))

        if pair in seen_pairs:
            raise ValueError(
                f"Line {line_number}: duplicate correlation pair {pair}"
            )

        seen_pairs.add(pair)

        if i == j and not math.isclose(
            rho, 1.0, rel_tol=0.0, abs_tol=1e-9
        ):
            raise ValueError(
                f"Line {line_number}: diagonal correlation must equal 1"
            )

        correlation[i][j] = rho
        correlation[j][i] = rho

    if len(seen_pairs) != pair_count:
        raise ValueError("Incomplete correlation matrix")

    covariance = [
        [
            std_devs[i] * std_devs[j] * correlation[i][j]
            for j in range(n)
        ]
        for i in range(n)
    ]

    return PortfolioData(
        name=name,
        returns=tuple(returns),
        std_devs=tuple(std_devs),
        correlation=tuple(tuple(row) for row in correlation),
        covariance=tuple(tuple(row) for row in covariance),
    )


def load_portfolio(path: str | Path) -> PortfolioData:
    """Load an OR-Library portfolio file from disk."""

    path = Path(path)
    text = path.read_text(encoding="utf-8")
    return parse_portfolio_text(text, name=path.stem)
