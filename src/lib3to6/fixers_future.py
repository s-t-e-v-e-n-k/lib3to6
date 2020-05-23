# This file is part of the lib3to6 project
# https://gitlab.com/mbarkhau/lib3to6
#
# Copyright (c) 2019 Manuel Barkhau (mbarkhau@gmail.com) - MIT License
# SPDX-License-Identifier: MIT

import ast

from . import common
from . import fixer_base as fb


class FutureImportFixerBase(fb.FixerBase):

    future_name: str

    def __call__(self, cfg: common.BuildConfig, tree: ast.Module) -> ast.Module:
        self.required_imports.add(common.ImportDecl("__future__", self.future_name, None))
        return tree


class AnnotationsFutureFixer(FutureImportFixerBase):

    version_info = fb.VersionInfo(apply_since="3.7", apply_until="3.99")

    future_name = "annotations"


class GeneratorStopFutureFixer(FutureImportFixerBase):

    version_info = fb.VersionInfo(apply_since="3.5", apply_until="3.6")

    future_name = "generator_stop"


class UnicodeLiteralsFutureFixer(FutureImportFixerBase):

    version_info = fb.VersionInfo(apply_since="2.6", apply_until="2.7")

    future_name = "unicode_literals"


class PrintFunctionFutureFixer(FutureImportFixerBase):

    version_info = fb.VersionInfo(apply_since="2.6", apply_until="2.7")

    future_name = "print_function"


class WithStatementFutureFixer(FutureImportFixerBase):

    version_info = fb.VersionInfo(apply_since="2.5", apply_until="2.5")

    future_name = "with_statement"


class AbsoluteImportFutureFixer(FutureImportFixerBase):

    version_info = fb.VersionInfo(apply_since="2.5", apply_until="2.7")

    future_name = "absolute_import"


class DivisionFutureFixer(FutureImportFixerBase):

    version_info = fb.VersionInfo(apply_since="2.2", apply_until="2.7")

    future_name = "division"


class GeneratorsFutureFixer(FutureImportFixerBase):

    version_info = fb.VersionInfo(apply_since="2.2", apply_until="2.2")

    future_name = "generators"


class NestedScopesFutureFixer(FutureImportFixerBase):

    version_info = fb.VersionInfo(apply_since="2.1", apply_until="2.1")

    future_name = "nested_scopes"


class RemoveUnsupportedFuturesFixer(fb.FixerBase):

    version_info = fb.VersionInfo(apply_since="2.0", apply_until="3.99")

    def __call__(self, cfg: common.BuildConfig, tree: ast.Module) -> ast.Module:
        target_version    = cfg.get('target_version', "2.7")
        supported_futures = set()
        for cls in FutureImportFixerBase.__subclasses__():
            if cls.is_compatible_with(target_version):
                supported_futures.add(cls.future_name)

        nodes_to_del = []
        for i, node in enumerate(tree.body):
            if not isinstance(node, ast.ImportFrom):
                break

            is_future_import = node.module == '__future__' and node.level == 0
            if not is_future_import:
                break

            new_names = [alias for alias in node.names if alias.name in supported_futures]
            if new_names == node.names:
                continue

            if not any(new_names):
                nodes_to_del.append(i)
            else:
                node.names = new_names

        for i in reversed(nodes_to_del):
            del tree.body[i : i + 1]

        return tree
