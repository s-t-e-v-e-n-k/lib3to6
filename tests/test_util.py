import ast
from three2six import transpile


# https://gist.github.com/marsam/d2a5af1563d129bb9482
def dump_ast(node, annotate_fields=True, include_attributes=False, indent="  "):
    """
    Return a formatted dump of the tree in *node*.  This is mainly useful for
    debugging purposes.  The returned string will show the names and the values
    for fields.  This makes the code impossible to evaluate, so if evaluation is
    wanted *annotate_fields* must be set to False.  Attributes such as line
    numbers and column offsets are not dumped by default.  If this is wanted,
    *include_attributes* can be set to True.
    """
    def _format(node, level=0):
        if isinstance(node, ast.AST):
            fields = [(a, _format(b, level)) for a, b in ast.iter_fields(node)]
            if include_attributes and node._attributes:
                fields.extend([
                    (a, _format(getattr(node, a), level))
                    for a in node._attributes
                ])

            if annotate_fields:
                field_parts = ("%s=%s" % field for field in fields)
            else:
                field_parts = (b for a, b in fields)

            fields_str = ", ".join(field_parts)
            node_name = node.__class__.__name__
            return node_name + "(" + fields_str + ")"
        elif isinstance(node, list):
            lines = ["["]
            lines.extend((
                indent * (level + 2) + _format(x, level + 2) + ","
                for x in node
            ))
            if len(lines) > 1:
                lines.append(indent * (level + 1) + "]")
            else:
                lines[-1] += "]"
            return "\n".join(lines)
        return repr(node)

    if not isinstance(node, (ast.AST, list)):
        raise TypeError("expected AST, got %r" % node.__class__.__name__)
    return _format(node)


def clean_whitespace(fixture_str):
    if fixture_str.strip().count("\n") == 0:
        return fixture_str.strip()

    fixture_lines = [
        line
        for line in fixture_str.splitlines()
        if line.strip()
    ]
    line_indents = [
        len(line) - len(line.lstrip())
        for line in fixture_lines
    ]
    if not any(line_indents) or min(line_indents) == 0:
        return fixture_str

    indent = min(line_indents)
    return "\n".join([
        line[indent:] for line in fixture_lines
    ])


def parsedump_ast(code, mode="exec", **kwargs):
    """Parse some code from a string and pretty-print it."""
    node = ast.parse(clean_whitespace(code), mode=mode)
    return dump_ast(node, **kwargs)


def transpile_and_dump(module_str, cfg=None):
    if cfg is None:
        cfg = {}
    if "checkers" not in cfg:
        cfg["checkers"] = ""
    if "fixers" not in cfg:
        cfg["fixers"] = ""

    module_str = clean_whitespace(module_str)
    module_data = module_str.encode("utf-8")
    coding, header = transpile.parse_module_header(module_data)
    result_data = transpile.transpile_module(cfg, module_data)
    result_str = result_data.decode("utf-8")
    return coding, header, result_str