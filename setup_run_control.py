from setuptools import setup
from Cython.Build import cythonize

setup(
    # Reemplaza 'nucleo.pyx' si le pusiste otro nombre
    ext_modules = cythonize("run_control.pyx", language_level=3)
)