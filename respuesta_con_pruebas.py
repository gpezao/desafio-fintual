from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class Stock:
    """
    Representa un activo financiero individual.
    La clase es inmutable para evitar que el estado del activo
    cambie de forma inesperada dentro del portafolio.
    """
    symbol: str
    current_price: float

    def get_current_price(self) -> float:
        """
        El precio se expone mediante un método para permitir,
        en el futuro, desacoplar la fuente del precio (API, cache, mock, etc.).
        """
        return self.current_price


@dataclass
class Position:
    """
    Representa una posición concreta dentro del portafolio.
    Separar Stock de Position evita mezclar identidad del activo
    con decisiones de inversión.
    """
    stock: Stock
    quantity: float

    @property
    def market_value(self) -> float:
        return self.quantity * self.stock.get_current_price()


@dataclass
class RebalanceAction:
    """
    Resultado del rebalanceo.
    No ejecuta operaciones: solo comunica decisiones.
    Esta separación es crítica en sistemas financieros auditables.
    """
    stock: Stock
    action: str  # "BUY" o "SELL"
    quantity: float
    value: float


class Portfolio:
    """
    El Portfolio concentra toda la lógica financiera.
    Los Stocks no saben nada del portafolio;
    el portafolio sí conoce a sus activos.
    """

    def __init__(
        self,
        positions: List[Position],
        target_allocation: Dict[str, float],
        tolerance: float = 0.05
    ):
        """
        :param positions: posiciones actuales del portafolio
        :param target_allocation: asignación objetivo por símbolo (suma 1.0)
        :param tolerance: banda de tolerancia permitida (ej: 0.05 = ±5%)
        """
        self.positions = {p.stock.symbol: p for p in positions}
        self.target_allocation = target_allocation
        self.tolerance = tolerance

    @property
    def total_value(self) -> float:
        return sum(position.market_value for position in self.positions.values())

    def current_allocation(self) -> Dict[str, float]:
        """
        Calcula la distribución actual del portafolio.
        Se separa en un método para facilitar testing y trazabilidad.
        """
        total = self.total_value
        return {
            symbol: position.market_value / total
            for symbol, position in self.positions.items()
        }

    def rebalance(self) -> List[RebalanceAction]:
        """
        Aplica un rebalanceo basado en metas + bandas.

        Regla central:
        - Mientras el peso esté dentro de la banda, no se actúa.
        - Si se rompe la banda, se rebalancea hacia la meta central.

        Esto evita sobreoperar y permite que los ganadores sigan creciendo.
        """
        actions: List[RebalanceAction] = []
        total_value = self.total_value
        current_allocation = self.current_allocation()

        for symbol, target_weight in self.target_allocation.items():
            if symbol not in self.positions:
                # En un sistema real, aquí se podría decidir
                # si se permite incorporar nuevos activos.
                continue

            position = self.positions[symbol]
            current_weight = current_allocation.get(symbol, 0.0)

            lower_bound = target_weight - self.tolerance
            upper_bound = target_weight + self.tolerance

            # Mientras esté dentro de la banda, no se interviene.
            if lower_bound <= current_weight <= upper_bound:
                continue

            # Al salir de la banda, se vuelve al objetivo central,
            # no al borde. Esto simplifica el modelo mental del usuario.
            target_value = total_value * target_weight
            delta_value = target_value - position.market_value

            # Convertimos dinero en cantidad de acciones.
            quantity_delta = delta_value / position.stock.get_current_price()

            action_type = "BUY" if quantity_delta > 0 else "SELL"

            actions.append(
                RebalanceAction(
                    stock=position.stock,
                    action=action_type,
                    quantity=abs(quantity_delta),
                    value=abs(delta_value)
                )
            )

        return actions


# -----------------------------
# LÓGICA DE PRUEBA INTERACTIVA
# -----------------------------

def prompt_float(message: str) -> float:
    """
    Centralizar la lectura de números evita duplicar validaciones
    y mantiene la interacción clara.
    """
    while True:
        try:
            return float(input(message))
        except ValueError:
            print("⚠️  Ingresa un número válido.")


def build_positions() -> List[Position]:
    """
    Permite construir el portafolio actual desde teclado.
    Se prioriza claridad antes que velocidad.
    """
    positions = []
    num_stocks = int(prompt_float("¿Cuántas acciones distintas tiene el portafolio? "))

    for _ in range(num_stocks):
        symbol = input("\nSímbolo de la acción (ej: AAPL): ").upper()
        price = prompt_float(f"Precio actual de {symbol}: ")
        quantity = prompt_float(f"Cantidad de acciones de {symbol}: ")

        stock = Stock(symbol=symbol, current_price=price)
        positions.append(Position(stock=stock, quantity=quantity))

    return positions


def build_target_allocation() -> dict:
    """
    La asignación se pide explícitamente para reforzar
    el modelo mental de metas porcentuales.
    """
    allocation = {}
    num_targets = int(prompt_float("\n¿Cuántas metas de asignación deseas definir? "))

    print("\nIngresa los porcentajes como decimales (ej: 0.4 para 40%)")

    for _ in range(num_targets):
        symbol = input("Símbolo: ").upper()
        weight = prompt_float(f"Peso objetivo para {symbol}: ")
        allocation[symbol] = weight

    return allocation


def print_portfolio_state(portfolio: Portfolio):
    """
    Mostrar el estado actual ayuda a validar visualmente
    si el rebalanceo tiene sentido.
    """
    print("\n📊 Estado actual del portafolio:")
    print(f"Valor total: ${portfolio.total_value:,.2f}\n")

    allocation = portfolio.current_allocation()

    for symbol, position in portfolio.positions.items():
        weight = allocation[symbol] * 100
        print(
            f"- {symbol}: "
            f"{position.quantity:.2f} acciones | "
            f"${position.market_value:,.2f} | "
            f"{weight:.2f}%"
        )


def print_rebalance_actions(actions: List[RebalanceAction]):
    """
    La salida se presenta como recomendaciones claras,
    no como órdenes técnicas.
    """
    if not actions:
        print("\n✅ El portafolio está dentro de las bandas. No se requieren ajustes.")
        return

    print("\n🔄 Acciones recomendadas para rebalancear:\n")

    for action in actions:
        print(
            f"{action.action} {action.quantity:.2f} acciones de {action.stock.symbol} "
            f"(≈ ${action.value:,.2f})"
        )


def main():
    print("\n=== Simulador de Rebalanceo (Metas + Bandas) ===\n")

    positions = build_positions()
    target_allocation = build_target_allocation()
    tolerance = prompt_float("\nDefine la banda de tolerancia (ej: 0.05 = ±5%): ")

    portfolio = Portfolio(
        positions=positions,
        target_allocation=target_allocation,
        tolerance=tolerance
    )

    print_portfolio_state(portfolio)

    actions = portfolio.rebalance()
    print_rebalance_actions(actions)


if __name__ == "__main__":
    main()
