from setuptools import setup, Extension
from Cython.Build import cythonize
import os

# 1. Definimos las carpetas que queremos proteger
carpetas_a_compilar = ['api/controllers', 'api/models', 'api/services', 'api/utils']
extensions = []

# 2. Recorremos cada carpeta para buscar archivos .pyx
for carpeta in carpetas_a_compilar:
    # Caminamos por el directorio
    for root, dirs, files in os.walk(carpeta):
        for file in files:
            if file.endswith(".pyx"):
                # Construimos la ruta completa (ej: controllers/login.pyx)
                full_path = os.path.join(root, file)

                # Construimos el nombre del módulo (ej: controllers.login)
                # Esto es CRUCIAL para que los imports funcionen
                module_name = full_path.replace(os.path.sep, ".")[:-4]

                # Creamos la extensión
                ext = Extension(
                    name=module_name,
                    sources=[full_path]
                )
                extensions.append(ext)

# 3. Configuramos la compilación
setup(
    name="Mi App Protegida",
    ext_modules=cythonize(
        extensions,
        language_level=3,  # Asegura compatibilidad con Python 3
        compiler_directives={'always_allow_keywords': True}  # Evita errores con keywords
    ),
)