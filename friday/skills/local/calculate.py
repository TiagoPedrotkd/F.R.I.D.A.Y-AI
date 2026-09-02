"""Local calculator skill (sympy / safe arithmetic)."""

from __future__ import annotations

import ast
import operator
from typing import Any

from friday.skills.base import SkillResult

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _eval_node(node: ast.AST) -> float | int:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_node(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    raise ValueError("Expressao nao permitida")


def safe_eval(expr: str) -> float | int:
    tree = ast.parse(expr.strip(), mode="eval")
    return _eval_node(tree)


class CalculateSkill:
    name = "calculate"
    description = (
        "Avalia uma expressao matematica localmente (aritmetica segura). "
        "Usa para calculos exactos; nao inventes resultados."
    )
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "Expressao, ex: (12.5 * 3) + 7 / 2",
            }
        },
        "required": ["expression"],
    }

    async def execute(self, arguments: dict[str, Any]) -> SkillResult:
        expr = (arguments.get("expression") or "").strip()
        if not expr:
            return SkillResult(success=False, content="", error="Expressao vazia.")
        try:
            try:
                import sympy

                result = sympy.N(sympy.sympify(expr))
                text = str(result)
            except Exception:
                result = safe_eval(expr)
                text = str(result)
        except Exception as exc:
            return SkillResult(
                success=False,
                content="",
                error=f"Nao consegui calcular: {exc}",
            )
        return SkillResult(
            success=True,
            content=f"Resultado: {text}",
            metadata={"kind": "calculate", "expression": expr, "result": text},
        )
