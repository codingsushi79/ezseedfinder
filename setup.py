"""Build the vendored cubiomes native library for ctypes."""

from __future__ import annotations

import os
import sys

from setuptools import Command, Extension, setup
from setuptools.command.bdist_wheel import bdist_wheel
from setuptools.command.build import build

LIB_DIR = "cubiomespi/lib"
CUBIOMES_DIR = "cubiomespi/lib/cubiomes"

CUBIOMES_SOURCES = [
    f"{LIB_DIR}/newlib.c",
    f"{CUBIOMES_DIR}/biomes.c",
    f"{CUBIOMES_DIR}/util.c",
    f"{CUBIOMES_DIR}/noise.c",
    f"{CUBIOMES_DIR}/layers.c",
    f"{CUBIOMES_DIR}/generator.c",
    f"{CUBIOMES_DIR}/finders.c",
    f"{CUBIOMES_DIR}/quadbase.c",
    f"{CUBIOMES_DIR}/biometree.c",
    f"{CUBIOMES_DIR}/biomenoise.c",
]

LIB_CMODULE = f"{LIB_DIR}/lib_cmodule.c"


def ext_modules() -> list[Extension]:
    if sys.platform == "win32":
        return []
    return [
        Extension(
            "cubiomespi.lib_c",
            sources=[*CUBIOMES_SOURCES, LIB_CMODULE],
            include_dirs=[CUBIOMES_DIR],
            libraries=[] if sys.platform == "darwin" else ["m"],
        )
    ]


class build_cubiomes_lib(Command):
    description = "Build vendored cubiomes shared library"
    user_options = [("force", "f", "Force rebuild of native library")]
    boolean_options = ["force"]

    def initialize_options(self) -> None:
        self.force = False
        self.build_lib = None
        self.build_temp = None

    def finalize_options(self) -> None:
        self.set_undefined_options("build", ("build_lib", "build_lib"), ("build_temp", "build_temp"))

    def run(self) -> None:
        from distutils.ccompiler import new_compiler
        from distutils.sysconfig import customize_compiler

        output_dir = os.path.join(self.build_lib, "cubiomespi", "lib")
        os.makedirs(output_dir, exist_ok=True)

        if sys.platform == "win32":
            output_path = os.path.join(output_dir, "lib.dll")
        elif sys.platform == "darwin":
            output_path = os.path.join(output_dir, "lib.dylib")
        else:
            output_path = os.path.join(output_dir, "lib.so")

        if not self.force and os.path.isfile(output_path):
            return

        build_temp = os.path.join(self.build_temp, "cubiomes")
        os.makedirs(build_temp, exist_ok=True)

        compiler = new_compiler()
        customize_compiler(compiler)

        extra_preargs = ["/DNDEBUG"] if compiler.compiler_type == "msvc" else ["-fPIC"]
        objects = compiler.compile(
            CUBIOMES_SOURCES,
            output_dir=build_temp,
            include_dirs=[CUBIOMES_DIR],
            extra_preargs=extra_preargs,
        )

        if compiler.compiler_type == "msvc":
            compiler.link_shared_lib(
                objects,
                "lib",
                output_dir=output_dir,
                extra_preargs=["/DLL"],
            )
        else:
            compiler.link_shared_object(
                objects,
                output_path,
                libraries=["m"],
            )


class bdist_wheel_native(bdist_wheel):
    def initialize_options(self) -> None:
        super().initialize_options()
        self.root_is_pure = False

    def finalize_options(self) -> None:
        super().finalize_options()
        self.root_is_pure = False


class build_with_cubiomes(build):
    sub_commands = (
        build.sub_commands + [("build_cubiomes_lib", None)]
        if sys.platform == "win32"
        else build.sub_commands
    )


setup(
    ext_modules=ext_modules(),
    cmdclass={
        "build_cubiomes_lib": build_cubiomes_lib,
        "build": build_with_cubiomes,
        "bdist_wheel": bdist_wheel_native,
    },
)
