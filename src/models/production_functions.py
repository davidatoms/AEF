from __future__ import annotations

from typing import Any, Callable, Dict

from .cobbDouglas import cobb_douglas as cobb_douglas_numeric


ProductionFunction = Dict[str, Any]


def cobb_douglas_symbolic(sp_module, L, K):
    A_sym, alpha_sym, beta_sym = sp_module.symbols("A alpha beta", positive=True)
    expr = A_sym * L ** alpha_sym * K ** beta_sym
    return {
        "expr": expr,
        "symbols": {"A": A_sym, "alpha": alpha_sym, "beta": beta_sym},
        "description": "Q = A * L^alpha * K^beta",
    }


def ces_numeric(labor: float, capital: float, params: Dict[str, float]) -> float:
    A = params.get("A", 1.0)
    delta = params.get("delta", 0.5)
    rho = params.get("rho", -0.5)

    inside = delta * (labor ** rho) + (1.0 - delta) * (capital ** rho)
    return A * (inside ** (1.0 / rho))


def ces_symbolic(sp_module, L, K):
    A_sym, delta_sym, rho_sym = sp_module.symbols("A delta rho", positive=True)
    expr = A_sym * (delta_sym * L ** rho_sym + (1 - delta_sym) * K ** rho_sym) ** (1 / rho_sym)
    return {
        "expr": expr,
        "symbols": {"A": A_sym, "delta": delta_sym, "rho": rho_sym},
        "description": "Q = A * [delta*L^rho + (1-delta)*K^rho]^(1/rho)",
    }


def leontief_numeric(labor: float, capital: float, params: Dict[str, float]) -> float:
    A = params.get("A", 1.0)
    a_coef = params.get("a_coef", 1.0)
    b_coef = params.get("b_coef", 1.0)
    return A * min(labor / a_coef, capital / b_coef)


def leontief_symbolic(sp_module, L, K):
    A_sym, a_sym, b_sym = sp_module.symbols("A a_coef b_coef", positive=True)
    expr = A_sym * sp_module.Min(L / a_sym, K / b_sym)
    return {
        "expr": expr,
        "symbols": {"A": A_sym, "a_coef": a_sym, "b_coef": b_sym},
        "description": "Q = A * min(L/a_coef, K/b_coef)",
    }


_PRODUCTION_FUNCTIONS: Dict[str, ProductionFunction] = {
    "cobb_douglas": {
        "numeric": lambda labor, capital, params: cobb_douglas_numeric(
            labor, capital, params.get("alpha", 0.3), params.get("beta", 0.7), A=params.get("A", 1.0)
        ),
        "symbolic": cobb_douglas_symbolic,
        "defaults": {"A": 1.0, "alpha": 0.3, "beta": 0.7},
        "param_docs": {
            "A": "Total factor productivity",
            "alpha": "Output elasticity of labor",
            "beta": "Output elasticity of capital",
        },
        "description": "Cobb-Douglas production function with constant elasticities.",
    },
    "ces": {
        "numeric": ces_numeric,
        "symbolic": ces_symbolic,
        "defaults": {"A": 1.0, "delta": 0.5, "rho": -0.5},
        "param_docs": {
            "A": "Scaling factor",
            "delta": "Share parameter (labor weight)",
            "rho": "Substitution parameter (rho != 0)",
        },
        "description": "Constant elasticity of substitution (CES) production function.",
    },
    "leontief": {
        "numeric": leontief_numeric,
        "symbolic": leontief_symbolic,
        "defaults": {"A": 1.0, "a_coef": 1.0, "b_coef": 1.0},
        "param_docs": {
            "A": "Scaling factor",
            "a_coef": "Labor requirement per unit of output",
            "b_coef": "Capital requirement per unit of output",
        },
        "description": "Leontief (perfect complements) production function.",
    },
}


def get_production_function(name: str) -> ProductionFunction:
    normalized = name.lower()
    if normalized not in _PRODUCTION_FUNCTIONS:
        available = ", ".join(sorted(_PRODUCTION_FUNCTIONS.keys()))
        raise ValueError(f"Unknown production function '{name}'. Available options: {available}")
    return _PRODUCTION_FUNCTIONS[normalized]


def list_production_functions() -> Dict[str, ProductionFunction]:
    return {name: data.copy() for name, data in _PRODUCTION_FUNCTIONS.items()}
