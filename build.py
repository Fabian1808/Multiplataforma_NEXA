import subprocess
import sys
import os
import shutil
from pathlib import Path

def main():
    print("Iniciando proceso de construcción (Build)...")
    
    # 1. Instalar dependencias si faltan
    print("Instalando dependencias de construcción...")
    subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
    
    # 2. Limpiar build previa si existe
    dist_dir = Path("dist")
    build_dir = Path("build")
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    if build_dir.exists():
        shutil.rmtree(build_dir)
        
    # 3. Compilar
    print("Compilando ejecutable con PyInstaller...")
    result = subprocess.run([
        sys.executable, "-m", "PyInstaller", "--noconfirm", "nexa_hub.spec"
    ])
    
    if result.returncode == 0:
        print("\n=======================================================")
        print(f"¡CONSTRUCCIÓN EXITOSA!")
        print(f"El ejecutable se encuentra en: {dist_dir.resolve()} / NEXA Hub")
        print("=======================================================\n")
    else:
        print("\nHubo un error durante la construcción.")
        sys.exit(1)

if __name__ == "__main__":
    main()
