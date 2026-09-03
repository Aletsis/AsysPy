#!/usr/bin/env python3
"""Script de empaquetado para generar ejecutables de escritorio de AsistPy.

Uso:
    python scripts/package/build_desktop.py [--onefile] [--driver postgres,mysql]
"""

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Empaquetador de escritorio para AsistPy.")
    parser.add_argument("--onefile", action="store_true", help="Generar un único archivo ejecutable.")
    parser.add_argument("--clean", action="store_true", help="Limpiar directorios de compilación previos.")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent.parent
    spec_path = project_root / "scripts" / "package" / "asistpy.spec"

    print("=" * 60)
    print(" 🚀 Compilando AsistPy Desktop GUI con PyInstaller")
    print(f" Proyecto: {project_root}")
    print(f" Spec:     {spec_path}")
    print("=" * 60)

    # Verificar que PyInstaller esté instalado
    try:
        import PyInstaller
    except ImportError:
        print("❌ Error: PyInstaller no está instalado.")
        print("Instálalo ejecutando: pip install pyinstaller")
        return 1

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        str(spec_path),
        "--distpath",
        str(project_root / "dist"),
        "--workpath",
        str(project_root / "build"),
    ]

    if args.clean:
        cmd.append("--clean")

    print(f"Ejecutando: {' '.join(cmd)}")
    ret = subprocess.run(cmd, cwd=str(project_root))
    if ret.returncode == 0:
        print("\n✅ Compilación completada con éxito.")
        print(f"Ejecutable disponible en: {project_root / 'dist' / 'AsistPy'}")
    else:
        print(f"\n❌ Error durante la compilación. Código de salida: {ret.returncode}")

    return ret.returncode


if __name__ == "__main__":
    sys.exit(main())
