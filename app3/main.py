from flask import Flask, redirect, request, session, render_template
import requests
import os
from requests.exceptions import HTTPError, RequestException

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')

app.config['SESSION_COOKIE_NAME'] = 'app3_critical_session'

if not app.secret_key:
    raise ValueError("Falta la clave secreta para Flask en App 3")


# CONFIGURACIÓN DEL SSO 
KEYCLOAK_SERVER = os.getenv('KEYCLOAK_SERVER')

REALM_NAME = os.getenv('REALM_NAME')
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
REDIRECT_URI = os.getenv('REDIRECT_URI')

config_vars = {
    'KEYCLOAK_SERVER': KEYCLOAK_SERVER,
    'REALM_NAME': REALM_NAME,
    'CLIENT_ID': CLIENT_ID,
    'CLIENT_SECRET': CLIENT_SECRET,
    'REDIRECT_URI': REDIRECT_URI,
}
if not all(config_vars.values()):
    raise ValueError("Faltan variables de configuración en el entorno de la App 3")

AUTHORIZATION_ENDPOINT = f"{KEYCLOAK_SERVER}/realms/{REALM_NAME}/protocol/openid-connect/auth"
LOGOUT_ENDPOINT = f"{KEYCLOAK_SERVER}/realms/{REALM_NAME}/protocol/openid-connect/logout"
TOKEN_ENDPOINT = f"{KEYCLOAK_SERVER}/realms/{REALM_NAME}/protocol/openid-connect/token"
USERINFO_ENDPOINT = f"{KEYCLOAK_SERVER}/realms/{REALM_NAME}/protocol/openid-connect/userinfo"



# RUTAS DE ACCESO CONDICIONAL
@app.route('/')
def index():
    if 'userinfo' in session:
        return render_template('index.html', user_info=session['userinfo'])
    return render_template('login.html')

@app.route('/login')
def login():
    auth_url = (
        f"{AUTHORIZATION_ENDPOINT}?client_id={CLIENT_ID}"
        f"&response_type=code"
        f"&scope=openid%20email%20profile"
        f"&redirect_uri={REDIRECT_URI}"
        f"&prompt=login"
    )
    return redirect(auth_url)

import logging
from requests.exceptions import HTTPError, RequestException

# Asegúrate de tener configurado el logger en tu app de Flask
# app.logger.setLevel(logging.INFO)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        app.logger.warning("[SSO App 3] Intento de acceso sin código de autorización.")
        return redirect('/')

    token_data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    }
    
    try:
        # 1. Intercambio de Código por Token (Back-Channel)
        # Nota: verify=False se mantiene por el uso de CA local en laboratorio
        token_response = requests.post(TOKEN_ENDPOINT, data=token_data, verify=False)
        token_response.raise_for_status()  # Lanza una excepción si el HTTP status es 4xx o 5xx
        
        token_json = token_response.json()
        if 'access_token' not in token_json:
            app.logger.error(f"[SSO App 3] Intercambio fallido, JSON sin access_token: {token_json}")
            return redirect('/')

        # 2. Extracción del Perfil de Usuario (UserInfo)
        headers = {'Authorization': f"Bearer {token_json['access_token']}"}
        userinfo_response = requests.get(USERINFO_ENDPOINT, headers=headers, verify=False)
        userinfo_response.raise_for_status()

        # 3. Establecimiento de la Sesión
        session['userinfo'] = userinfo_response.json()
        app.logger.info(f"[SSO App 3] Autenticación mTLS exitosa para usuario: {session['userinfo'].get('preferred_username')}")
        return redirect('/')

    # Manejo estructurado de errores
    except HTTPError as http_err:
        app.logger.critical(f"[SSO Error Red] Fallo en la comunicación con Keycloak: {http_err}")
        app.logger.critical(f"Detalle devuelto por el servidor: {http_err.response.text}")
        # En producción, aquí se renderizaría un template (ej. render_template('error.html', code=500))
        return "Error 500: Fallo de comunicación segura con el Proveedor de Identidad.", 500
        
    except ValueError as json_err:
        app.logger.critical(f"[SSO Error Datos] La respuesta de Keycloak no es un JSON válido: {json_err}")
        return "Error 500: Formato de respuesta no válido.", 500
        
    except RequestException as req_err:
        app.logger.critical(f"[SSO Error Sistema] No se pudo alcanzar Keycloak: {req_err}")
        return "Error 500: El servicio de autenticación no está disponible.", 500

@app.route('/logout')
def logout():
    session.clear()
    # Redirección externa tras el cierre de sesión al puerto 5002 visible en el navegador
    return redirect(f"{LOGOUT_ENDPOINT}?client_id={CLIENT_ID}&post_logout_redirect_uri=http://localhost:5002/")

if __name__ == '__main__':
    # Ejecución interna en puerto 5000 acorde al puente de Docker
    app.run(host='0.0.0.0', port=5000, debug=True)