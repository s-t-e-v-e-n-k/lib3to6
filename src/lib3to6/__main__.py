#!/usr/bin/env python
# This file is part of the lib3to6 project
# https://gitlab.com/mbarkhau/lib3to6
#
# Copyright (c) 2018 Manuel Barkhau (mbarkhau@gmail.com) - MIT License
# SPDX-License-Identifier: MIT

import io
import click
import typing as typ

import difflib
from . import packaging
from . import transpile


try:
    import backtrace

    # To enable pretty tracebacks:
    #   echo "export ENABLE_BACKTRACE=1;" >> ~/.bashrc
    backtrace.hook(align=True, strip_path=True, enable_on_envvar_only=True)
except ImportError:
    pass


@click.command()
@click.option(
    "--target-version",
    default="2.7",
    metavar="<version>",
    help="Target version of python.",
)
@click.option(
    "--diff",
    default=False,
    is_flag=True,
    help="Output diff instead of transpiled source.",
)
@click.option(
    "--in-place",
    default=False,
    is_flag=True,
    help="Write result back to input file.",
)
@click.option(
    "--config",
    default="lib3to6.toml",
    required=False,
    metavar="<path>",
    help="Path to config file.",
)
@click.argument(
    "source_files",
    metavar="<source_file>",
    nargs=-1,
    type=click.File(mode="r"),
)
def main(
    target_version: str,
    diff: bool,
    in_place: bool,
    config: str,
    source_files: typ.Iterable[io.TextIOWrapper],
) -> None:
    # TODO (mb 2018-07-12): evaluate build config
    cfg = packaging.eval_build_config()
    differ = difflib.Differ()
    for src_file in source_files:
        source_text = src_file.read()
        fixed_source_text = transpile.transpile_module(cfg, source_text)
        if diff:
            source_lines = source_text.splitlines()
            fixed_source_lines = fixed_source_text.splitlines()
            print("\n".join(differ.compare(source_lines, fixed_source_lines)))
        elif in_place:
            with io.open(src_file.name, mode="w") as fh:
                fh.write(fixed_source_text)
        else:
            print(fixed_source_text)


if __name__ == "__main__":
    main()      # type: ignore
