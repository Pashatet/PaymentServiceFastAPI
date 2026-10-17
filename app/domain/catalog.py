from app.domain.entities import Tariff

DEFAULT_TARIFFS: tuple[Tariff, ...] = (
    Tariff(id="basic", title="Basic", price=990_000),
    Tariff(id="standard", title="Standard", price=1_990_000),
    Tariff(id="premium", title="Premium", price=2_990_000),
)
