from flask import Flask, redirect, request, session, url_for, render_template
import requests
import os

app = Flask(__name__)
# Clave secreta para firmar las cookies de sesión de Flask
app.secret_key = os.getenv('FLASK_SECRET_KEY')
if not app.secret_key:
    raise ValueError("Falta la clave secreta para Flask")

# ==========================================
# CONFIGURACIÓN DEL SSO
# ==========================================
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
    raise ValueError("Faltan variables de configuración")

AUTHORIZATION_ENDPOINT = f"{KEYCLOAK_SERVER}/realms/{REALM_NAME}/protocol/openid-connect/auth"
TOKEN_ENDPOINT = f"{KEYCLOAK_SERVER}/realms/{REALM_NAME}/protocol/openid-connect/token"
USERINFO_ENDPOINT = f"{KEYCLOAK_SERVER}/realms/{REALM_NAME}/protocol/openid-connect/userinfo"
LOGOUT_ENDPOINT = f"{KEYCLOAK_SERVER}/realms/{REALM_NAME}/protocol/openid-connect/logout"

# ==========================================
# RUTAS DE LA APLICACIÓN
# ==========================================

@app.route('/')
def index():
    if 'userinfo' in session:
        return render_template('index.html', user_info=session['userinfo'])
    return render_template('login.html')

@app.route('/login')
def login():
    redirect_uri = REDIRECT_URI
    auth_url = (
        f"{AUTHORIZATION_ENDPOINT}?client_id={CLIENT_ID}"
        f"&response_type=code"
        f"&scope=openid email profile"
        f"&redirect_uri={redirect_uri}"
    )
    return redirect(auth_url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        print("[SSO] Error: Keycloak no ha devuelto ningún código.", flush=True)
        return redirect('/')

    # 1. Intercambio del Código por el Token
    token_data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    }
    
    token_response = requests.post(TOKEN_ENDPOINT, data=token_data, verify=False)
    
    # --- NUEVA DEFENSA: Comprobamos si ha fallado antes de convertir a JSON ---
    try:
        token_json = token_response.json()
    except requests.exceptions.JSONDecodeError:
        print(f"[CRÍTICO] Fallo HTTP {token_response.status_code} en Token Endpoint", flush=True)
        print(f"Respuesta del servidor: {token_response.text}", flush=True)
        return f"Error interno en Token. Revisa la terminal de Docker.", 500

    if 'access_token' not in token_json:
        print(f"[SSO] Error al obtener Token: {token_json}", flush=True)
        return redirect('/')

    # 2. Petición de la información del usuario
    headers = {
        'Authorization': f"Bearer {token_json['access_token']}"
    }
    
    userinfo_response = requests.get(USERINFO_ENDPOINT, headers=headers, verify=False)
    
    # --- NUEVA DEFENSA: Comprobamos el UserInfo ---
    try:
        userinfo_json = userinfo_response.json()
    except requests.exceptions.JSONDecodeError:
        print(f"[CRÍTICO] Fallo HTTP {userinfo_response.status_code} en UserInfo Endpoint", flush=True)
        print(f"Respuesta del servidor: {userinfo_response.text}", flush=True)
        return f"Error interno en UserInfo. Revisa la terminal de Docker.", 500
    
    if 'error' in userinfo_json:
         print(f"[SSO] Error en UserInfo: {userinfo_json}", flush=True)
         return redirect('/')

    # ¡Éxito! Guardamos en sesión
    print(f"[SSO] ¡Identidad confirmada! Datos: {userinfo_json}", flush=True)
    session['userinfo'] = userinfo_json

    return redirect('/')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(f"{LOGOUT_ENDPOINT}?client_id={CLIENT_ID}&post_logout_redirect_uri=http://localhost:5000/")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)