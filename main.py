import argparse
import sys
from pathlib import Path
from typing import Dict

SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

from models.production_functions import get_production_function, list_production_functions

try:
    import sympy as sp
except ImportError:
    sp = None


def ai_adjusted_output(labor: float, capital: float, ai_factor: float, production_fn: Dict, params: Dict[str, float]) -> float:
    """
    Evaluate the chosen production function and apply the AI multiplier.
    """
    base_output = production_fn["numeric"](labor, capital, params)
    return base_output * ai_factor


def parse_param_overrides(pairs):
    overrides: Dict[str, float] = {}
    for item in pairs or []:
        if "=" not in item:
            raise ValueError(f"Invalid parameter override '{item}'. Use NAME=VALUE.")
        key, value = item.split("=", 1)
        try:
            overrides[key.strip()] = float(value)
        except ValueError as exc:
            raise ValueError(f"Could not convert value for '{key}': {value}") from exc
    return overrides


def apply_named_overrides(params: Dict[str, float], **overrides):
    for key, value in overrides.items():
        if value is None:
            continue
        params[key] = value


def print_production_steps(function_name: str, production_fn: Dict, labor: float, capital: float, ai_factor: float, params: Dict[str, float]):
    """
    Show symbolic steps for the chosen production function when SymPy is available.
    """
    if sp is None:
        print("SymPy not installed; run `pip install sympy` to see step-by-step output.")
        return

    sp.init_printing(use_unicode=False)

    L, K = sp.symbols("L K", positive=True)
    Q = sp.symbols("Q")
    symbolic_info = production_fn["symbolic"](sp, L, K)
    base_expr = sp.Eq(Q, symbolic_info["expr"])

    print(f"{function_name.replace('_', ' ').title()} production function:")
    description = symbolic_info.get("description")
    if description:
        print(description)
    sp.pprint(base_expr, use_unicode=False)

    substitution_map = {L: labor, K: capital}
    for param_name, symbol in symbolic_info["symbols"].items():
        value = params[param_name]
        substitution_map[symbol] = sp.nsimplify(value)

    base_numeric_expr = sp.Eq(Q, base_expr.rhs.subs(substitution_map))
    print("\nAfter substituting inputs and parameters:")
    sp.pprint(base_numeric_expr, use_unicode=False)

    base_value = sp.N(base_numeric_expr.rhs)
    print(f"\nBase output (numeric): {base_value}")

    Q_ai = sp.symbols("Q_AI")
    ai_expr = sp.Eq(Q_ai, sp.Symbol("AI") * base_expr.rhs)
    print("\nAI-transformed production function:")
    sp.pprint(ai_expr, use_unicode=False)

    ai_subs = substitution_map.copy()
    ai_subs[sp.Symbol("AI")] = sp.nsimplify(ai_factor)
    ai_numeric_expr = sp.Eq(Q_ai, ai_expr.rhs.subs(ai_subs))
    print("\nAfter substituting inputs, parameters, and AI factor:")
    sp.pprint(ai_numeric_expr, use_unicode=False)

    ai_value = sp.N(ai_numeric_expr.rhs)
    print(f"\nAI-transformed output (numeric): {ai_value}")


def print_available_functions():
    registry = list_production_functions()
    print("Available production functions:\n")
    for name, details in sorted(registry.items()):
        print(f"- {name}: {details['description']}")
        defaults = ", ".join(f"{key}={value}" for key, value in details["defaults"].items())
        print(f"  Defaults: {defaults}")
        docs = details.get("param_docs", {})
        if docs:
            for param, doc in docs.items():
                print(f"    {param}: {doc}")
        print()


def parse_args():
    function_choices = sorted(list_production_functions().keys())
    parser = argparse.ArgumentParser(
        description="Evaluate production functions with an optional AI multiplier.",
    )
    parser.add_argument("--labor", type=float, default=100.0, help="Labor input (default: 100)")
    parser.add_argument("--capital", type=float, default=200.0, help="Capital input (default: 200)")
    parser.add_argument(
        "--ai-factor",
        type=float,
        default=1.15,
        help="AI multiplier applied to output (default: 1.15)",
    )
    parser.add_argument(
        "--function",
        choices=function_choices,
        default="cobb_douglas",
        help="Production function to evaluate.",
    )
    parser.add_argument("--alpha", type=float, help="Shortcut for Cobb-Douglas alpha parameter.")
    parser.add_argument("--beta", type=float, help="Shortcut for Cobb-Douglas beta parameter.")
    parser.add_argument("--total-factor", type=float, help="Shortcut for the scaling parameter A.")
    parser.add_argument(
        "--param",
        action="append",
        metavar="NAME=VALUE",
        default=[],
        help="Override/add production-function-specific parameters (repeatable).",
    )
    parser.add_argument(
        "--show-steps",
        action="store_true",
        help="Print symbolic step-by-step derivation (requires SymPy).",
    )
    parser.add_argument(
        "--list-functions",
        action="store_true",
        help="List available production functions and exit.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if args.list_functions:
        print_available_functions()
        return

    production_fn = get_production_function(args.function)
    params = production_fn["defaults"].copy()

    apply_named_overrides(
        params,
        A=args.total_factor,
        alpha=args.alpha,
        beta=args.beta,
    )

    try:
        params.update(parse_param_overrides(args.param))
    except ValueError as error:
        print(f"Parameter error: {error}")
        sys.exit(1)

    missing_keys = [key for key in production_fn["defaults"].keys() if key not in params]
    if missing_keys:
        print(f"Missing parameters for {args.function}: {', '.join(missing_keys)}")
        sys.exit(1)

    output = ai_adjusted_output(
        args.labor,
        args.capital,
        args.ai_factor,
        production_fn,
        params,
    )
    print(f"AI-adjusted output: {output}")

    if args.show_steps:
        print()
        print_production_steps(
            args.function,
            production_fn,
            args.labor,
            args.capital,
            args.ai_factor,
            params,
        )


if __name__ == "__main__":
    main()
