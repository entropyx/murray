import os
import sys
import streamlit.web.bootstrap

def main():
    # Encuentra la ubicación de `app.py` (que está en la raíz del repo)
    app_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app.py")

    if not os.path.exists(app_path):
        print(f"Error: No se encontró app.py en {app_path}")
        sys.exit(1)

    # Ejecuta la app de Streamlit
    streamlit.web.bootstrap.run(app_path, command_line=[], args=[])

if __name__ == "__main__":
    main()
