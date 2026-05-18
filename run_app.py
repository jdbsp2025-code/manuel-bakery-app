import streamlit.web.cli as stcli
import subprocess
import threading
import time
import os
import sys

def abrir_ventana():
    """Esta función espera a que el servidor esté listo y lanza Edge"""
    print("Esperando 5 segundos para que el servidor arranque...")
    time.sleep(5)
    
    url = "http://localhost:8501"
    edge_path = "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
    
    print("Lanzando ventana de COMUNAPP...")
    if os.path.exists(edge_path):
        # El modo --app oculta las barras de herramientas y pestañas
        subprocess.Popen([edge_path, f"--app={url}", "--start-maximized"])
    else:
        import webbrowser
        webbrowser.open(url)

if __name__ == "__main__":
    # 1. Preparamos el hilo que abrirá la ventana DESPUÉS de que arranque el servidor
    hilo_ventana = threading.Thread(target=abrir_ventana)
    hilo_ventana.daemon = True
    hilo_ventana.start()

    # 2. Buscamos el main.py (necesario para el ejecutable)
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    main_path = os.path.join(base_path, "main.py")

    # 3. LANZAMOS STREAMLIT EN EL HILO PRINCIPAL (Aquí se soluciona el error)
    sys.argv = [
        "streamlit", "run", main_path,
        "--server.port=8501",
        "--server.headless=true",
        "--global.developmentMode=false"
    ]
    
    print("Iniciando motor de la panadería...")
    stcli.main()