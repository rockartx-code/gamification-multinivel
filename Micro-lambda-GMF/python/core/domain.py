"""Vocabulario del dominio: estados con nombre en vez de literales sueltos."""


class OrderStatus:
    """Estados del ciclo de vida de un pedido.

    Antes eran literales sueltos repetidos por todo el backend: un typo como
    `"peding"` no fallaba, simplemente no coincidía nunca con nada.
    """
    PENDING = "pending"
    PAID = "paid"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    RETURNED = "returned"
    REFUNDED = "refunded"
    REJECTED = "rejected"

    ALL = (PENDING, PAID, SHIPPED, DELIVERED, CANCELLED, RETURNED, REFUNDED, REJECTED)
    #: Estados en los que el pedido ya no consume ni genera comisiones.
    TERMINAL = (CANCELLED, RETURNED, REFUNDED, REJECTED)

class CommissionStatus:
    """Estados de una fila del ledger de comisiones."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    BLOCKED = "blocked"

    ALL = (PENDING, CONFIRMED, BLOCKED)

class CommissionMonthStatus:
    """Estado del mes contable completo de un beneficiario."""
    IN_PROGRESS = "IN_PROGRESS"
    PAID = "PAID"
