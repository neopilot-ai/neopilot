from astroid import nodes
from pylint.checkers import BaseChecker
from pylint.lint import PyLinter


class DirectEnvironmentVariableReference(BaseChecker):
    name = "direct-environment-variable-reference"
    msgs = {
        "W5002": (
            "Direct environment variable reference detected.",
            "direct-environment-variable-reference",
            "See https://github.com/neopilot-ai/neopilot/-/blob/main/docs/application_settings.md for more information.",  # pylint: disable=line-too-long
        )
    }

    def visit_attribute(self, attribute: nodes.Attribute) -> None:
        if (
            hasattr(attribute, "expr")
            and hasattr(attribute, "attrname")
            and hasattr(attribute.expr, "name")
            and attribute.expr.name == "os"
            and attribute.attrname in {"environ", "getenv"}
        ):
            self.add_message("direct-environment-variable-reference", node=attribute)


def register(linter: "PyLinter") -> None:
    linter.register_checker(DirectEnvironmentVariableReference(linter))
