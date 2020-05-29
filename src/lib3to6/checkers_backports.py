import ast
import typing as typ
import logging

from . import common
from . import checker_base as cb

# TODO (mb 2020-05-28):
#   instead of functools.singledispatch
#   from singledispatch import singledispatch
#   https://pypi.org/project/singledispatch/
#
#   instead of functools.lru_cache
#   from backports import functools_lru_cache
#   https://pypi.org/project/backports.functools-lru-cache/
#

log = logging.getLogger(__name__)


class ModuleVersionInfo(typ.NamedTuple):

    available_since : str
    backport_module : typ.Optional[str]
    backport_package: typ.Optional[str]


MAYBE_UNUSABLE_MODULES = {
    # simple case 1. Always error because no backport available
    'asyncio': ModuleVersionInfo("3.4", None, None),
    'zipapp' : ModuleVersionInfo("3.5", None, None),
    # simple case 2. Always error because modules have different names and only
    #   backport should be used
    'csv'                : ModuleVersionInfo("3.0", "backports.csv"      , "backports.csv"),
    'selectors'          : ModuleVersionInfo("3.4", "selectors2"         , "selectors2"),
    'pathlib'            : ModuleVersionInfo("3.4", "pathlib2"           , "pathlib2"),
    "importlib.resources": ModuleVersionInfo("3.7", "importlib_resources", "importlib_resources"),
    'inspect'            : ModuleVersionInfo("3.6", "inspect2"           , "inspect2"),
    # complex case. Modules have the same name.
    # - By default, only log.warning if these are modules are imported.
    # - If opt-in via 'backports' option, check that they have been
    #   explicitly whitelisted.
    'lzma'       : ModuleVersionInfo("3.3", "lzma"       , "backports.lzma"),
    'ipaddress'  : ModuleVersionInfo("3.4", "ipaddress"  , "py2-ipaddress"),
    'enum'       : ModuleVersionInfo("3.4", "enum"       , "enum34"),
    'typing'     : ModuleVersionInfo("3.5", 'typing'     , 'typing'),
    'secrets'    : ModuleVersionInfo("3.6", "secrets"    , "python2-secrets"),
    'statistics' : ModuleVersionInfo("3.4", "statistics" , "statistics"),
    'dataclasses': ModuleVersionInfo("3.7", "dataclasses", "dataclasses"),
    'contextvars': ModuleVersionInfo("3.7", "contextvars", "contextvars"),
}


class NoUnusableImportsChecker(cb.CheckerBase):
    # NOTE (mb 2020-05-28): The naming of this makes sense, no the name
    #   "OnlyUsableImportsChecker" would not be better, because this doesn't
    #   check all imports ever in existence, it only checks that unusable
    #   imports are not used at the top level.

    # NOTE (mb 2020-05-28): This checker only checks top level imports.
    #   This allows for the common idom to work without errors.
    #
    #   try:
    #       import newmodule
    #   except ImportError:
    #       improt backport_module as newmodule

    def __call__(self, ctx: common.BuildContext, tree: ast.Module) -> None:
        # NOTE (mb 2020-05-28): Strict mode will fail hard
        # only passraises an error if an unusable
        #   module is not
        #   used Only warn about backported modules after
        #   opt-in to this check. Existing systems will have to update
        #   their config for this check to work and we don't want to
        #   break them.

        _backports = ctx.cfg.backports

        if _backports is None:
            is_strict_mode = False
            installed_backports: typ.Set[str] = set()
        else:
            is_strict_mode      = True
            installed_backports = _backports

        target_version = ctx.cfg.target_version
        for node in ast.iter_child_nodes(tree):
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue

            module_names: typ.List[str] = []
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_names.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module_name = node.module
                if module_name:
                    module_names.append(module_name)

            for mname in module_names:
                if mname not in MAYBE_UNUSABLE_MODULES:
                    continue

                vnfo = MAYBE_UNUSABLE_MODULES[mname]
                if target_version >= vnfo.available_since:
                    # target supports the newer name
                    continue

                if mname in installed_backports:
                    # explicitly whitelisted
                    continue

                if mname == vnfo.backport_module and not is_strict_mode:
                    lineno = common.get_node_lineno(node)
                    loc    = f"{ctx.filepath}@{lineno}"
                    msg    = f"{loc}: Use of import '{mname}' may be incompatible with {target_version}. "
                    log.warning(msg)
                    continue

                errmsg = (
                    f"Prohibited import '{mname}' "
                    f"(only available since python {vnfo.available_since})."
                )

                if vnfo.backport_package:
                    errmsg += f" Use 'https://pypi.org/project/{vnfo.backport_package}' instead."
                else:
                    errmsg += " No backported for this package is known."

                raise common.CheckError(errmsg, node)