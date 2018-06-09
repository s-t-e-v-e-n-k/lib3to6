import ast
import pytest

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


def parsedump_ast(code, mode="exec", **kwargs):
    """Parse some code from a string and pretty-print it."""
    node = ast.parse(code, mode=mode)   # An ode to the code
    return dump_ast(node, **kwargs)


TEST_STRINGS = {
    "preserved_header": (
        # no explicitfixers, just the header normalization and
        # default fixers
        "",
        """
        #!/usr/bin/env python
        # This file is part of the three2six project
        # https://github.com/mbarkhau/three2six
        # (C) 2018 Manuel Barkhau <mbarkhau@gmail.com>
        #
        # SPDX-License-Identifier:    MIT
        hello = "world"
        """,
        """
        #!/usr/bin/env python
        # -*- coding: utf-8 -*-
        # This file is part of the three2six project
        # https://github.com/mbarkhau/three2six
        # (C) 2018 Manuel Barkhau <mbarkhau@gmail.com>
        #
        # SPDX-License-Identifier:    MIT
        from __future__ import unicode_literals
        from __future__ import print_function
        from __future__ import division
        from __future__ import absolute_import
        hello = "world"
        """,
    ),
    "future_imports": (
        ",".join([
            "AbsoluteImportFutureFixer",
            "DivisionFutureFixer",
            "PrintFunctionFutureFixer",
            "UnicodeLiteralsFutureFixer",
        ]),
        """
        #!/usr/bin/env python
        '''Module Docstring'''
        """,
        """
        #!/usr/bin/env python
        # -*- coding: utf-8 -*-
        '''Module Docstring'''
        from __future__ import unicode_literals
        from __future__ import print_function
        from __future__ import division
        from __future__ import absolute_import
        """,
    ),
    "remove_annotations": (
        "RemoveAnnotationsFixer",
        """
        def foo(arg: arg_annotation) -> ret_annotation:
            pass

        moduleannattr: moduleattr_annotation

        class Bar:
            classannattr: classattr_annotation
            classannassign: classattr_annotation = 22

            def foo(self, arg: arg_annotation) -> ret_annotation:
                pass
        """,
        """
        def foo(arg):
            pass

        moduleannattr = None

        class Bar:
            classannattr = None
            classannassign = 22

            def foo(self, arg):
                pass
        """
    ),
    "fstrings_top_level": (
        "FStringFixer",
        "val = 33; f\"prefix {val / 2:>{3 * 3}} suffix\"",
        "val = 33; \"prefix {0:>{1}} suffix\".format(val / 2, 3 * 3)",
    ),
    "fstrings_nested": (
        "FStringFixer",
        """
        who = "World"
        print(f"Hello {who}!")
        """,
        """
        # -*- coding: utf-8 -*-
        who = "World"
        print("Hello {0}!".format(who))
        """,
    ),
    "new_style_classes": (
        "NewStyleClassesFixer",
        """
        class Foo:
            pass
        """,
        """
        # -*- coding: utf-8 -*-
        class Foo(object):
            pass
        """,
    ),
    "itertools.i(map|zip|filter)": (
        "ItertoolsBuiltinsFixer,PrintFunctionFutureFixer",
        """
        '''Module Docstring'''
        def fn(elem):
            return elem * 2

        list(map(fn, [1, 2, 3, 4]))
        dict(zip("abcd", [1, 2, 3, 4]))
        """,
        """
        # -*- coding: utf-8 -*-
        '''Module Docstring'''
        from __future__ import print_function
        import itertools

        def fn(elem):
            return elem * 2

        list(itertools.imap(fn, [1, 2, 3, 4]))
        dict(itertools.izip("abcd", [1, 2, 3, 4]))
        """,
    )
}


def _clean_whitespace(fixture_str):
    if fixture_str.strip().count("\n") == 0:
        return fixture_str.strip()

    fixture_str = fixture_str.lstrip()
    fixture_lines = fixture_str.splitlines()
    indent = min(
        len(line) - len(line.lstrip())
        for line in fixture_lines
        if len(line) > len(line.lstrip())
    )
    indent_str = " " * indent
    cleaned_lines = []
    for line in fixture_lines:
        if line.startswith(indent_str):
            cleaned_lines.append(line[indent:])
        else:
            cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


@pytest.mark.parametrize("name, fixture", list(TEST_STRINGS.items()))
def test_fixers(name, fixture):
    fixers, in_str, expected_str = fixture
    cfg = {"fixers": fixers}
    in_str = _clean_whitespace(in_str)
    expected_str = _clean_whitespace(expected_str)
    expected_data = expected_str.encode("utf-8")
    expected_coding, expected_header = transpile.parse_module_header(expected_data)

    in_data = in_str.encode("utf-8")
    in_coding, in_header = transpile.parse_module_header(in_data)
    assert in_coding == expected_coding
    assert in_header == expected_header

    result_data = transpile.transpile_module(cfg, in_data)
    result_str = result_data.decode("utf-8")
    assert parsedump_ast(expected_str) == parsedump_ast(result_str)
