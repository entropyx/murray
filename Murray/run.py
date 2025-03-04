import os
import sys
import subprocess

def main():
    app_path = os.path.join(os.path.dirname(__file__), "app.py")

    if not os.path.exists(app_path):
        print(f"Error: No se encontró app.py en {app_path}")
        sys.exit(1)

    # Ejecutar Streamlit con subprocess
    subprocess.run(["streamlit", "run", app_path])

if __name__ == "__main__":
    main()
