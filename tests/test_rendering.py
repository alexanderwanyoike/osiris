"""Whether the desktop is drawn by a GPU, which decides if wallpapers move."""

from osiris.platform.hardware import rendering_accelerated
from osiris.platform.process import CommandError, FakeRunner, Result

MESA_GPU = """name of display: :0
Extended renderer info (GLX_MESA_query_renderer):
    Vendor: Intel (0x8086)
    Device: Mesa Intel(R) UHD Graphics (TGL GT1) (0x9a68)
    Accelerated: yes
OpenGL renderer string: Mesa Intel(R) UHD Graphics (TGL GT1)
"""

LLVMPIPE = """name of display: :0
Extended renderer info (GLX_MESA_query_renderer):
    Vendor: Mesa (0xffffffff)
    Device: llvmpipe (LLVM 20.1.2, 256 bits) (0xffffffff)
    Accelerated: no
OpenGL renderer string: llvmpipe (LLVM 20.1.2, 256 bits)
"""

# NVIDIA's own driver does not implement GLX_MESA_query_renderer.
NVIDIA = """name of display: :0
OpenGL vendor string: NVIDIA Corporation
OpenGL renderer string: NVIDIA GeForce RTX 3050 Ti Laptop GPU/PCIe/SSE2
"""


def answer(stdout: str) -> FakeRunner:
    return FakeRunner(results={"glxinfo": Result(("glxinfo", "-B"), 0, stdout)})


def test_mesa_says_when_a_gpu_draws() -> None:
    assert rendering_accelerated(answer(MESA_GPU)) is True


def test_mesa_says_when_the_cpu_draws() -> None:
    assert rendering_accelerated(answer(LLVMPIPE)) is False


def test_a_driver_that_does_not_say_is_judged_by_its_name() -> None:
    assert rendering_accelerated(answer(NVIDIA)) is True
    software = "OpenGL renderer string: softpipe\n"
    assert rendering_accelerated(answer(software)) is False


def test_without_glxinfo_a_gpu_is_assumed() -> None:
    assert rendering_accelerated(FakeRunner(results={"glxinfo": FileNotFoundError()}))
    failed = CommandError(("glxinfo", "-B"), 1, "Error: unable to open display")
    assert rendering_accelerated(FakeRunner(results={"glxinfo": failed}))
