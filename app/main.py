from flask import Flask, redirect, request, session, url_for
import requests
import os

app = Flask(__name__)
# Clave secreta para firmar las cookies de sesión de Flask
app.secret_key = os.urandom(24)

# ==========================================
# CONFIGURACIÓN DEL SSO
# ==========================================
KEYCLOAK_SERVER = "https://sso.tfm.local"
REALM_NAME = "tfm_realm"
CLIENT_ID = "app_python"
CLIENT_SECRET = os.getenv('PYTHON_APP_SECRET')

if not CLIENT_SECRET:
    raise ValueError("La clave secreta para la aplicación Python no está definida")

AUTHORIZATION_ENDPOINT = f"{KEYCLOAK_SERVER}/realms/{REALM_NAME}/protocol/openid-connect/auth"
TOKEN_ENDPOINT = f"{KEYCLOAK_SERVER}/realms/{REALM_NAME}/protocol/openid-connect/token"
USERINFO_ENDPOINT = f"{KEYCLOAK_SERVER}/realms/{REALM_NAME}/protocol/openid-connect/userinfo"
LOGOUT_ENDPOINT = f"{KEYCLOAK_SERVER}/realms/{REALM_NAME}/protocol/openid-connect/logout"

# ==========================================
# RUTAS DE LA APLICACIÓN
# ==========================================

@app.route('/')
def index():
    if 'access_token' in session:
        return f"""
        <h1>Área Segura del TFM</h1>
        <p>¡Hola! Has iniciado sesión correctamente mediante SSO.</p>
        <p><b>Tu correo:</b> {session.get('user_email', 'Desconocido')}</p>
        <a href='/logout'><button>Cerrar Sesión</button></a>
        """
    return """
    <h1>Aplicación de Prueba - Zero Trust</h1>
    <p>No estás autenticado.</p>
    <a href='/login'><button>Iniciar Sesión con Keycloak</button></a>
    """

@app.route('/login')
def login():
    redirect_uri = "http://localhost:5000/callback"
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
        return "Error: No se recibió el código", 400

    redirect_uri = "http://localhost:5000/callback"
    token_data = {
        'grant_type': 'authorization_code',
        'code': code,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'redirect_uri': redirect_uri
    }
    
    token_response = requests.post(TOKEN_ENDPOINT, data=token_data, verify=False)
    
    if token_response.status_code == 200:
        tokens = token_response.json()
        session['access_token'] = tokens['access_token']
        
        userinfo_response = requests.get(USERINFO_ENDPOINT, 
                                         headers={'Authorization': f"Bearer {session['access_token']}"}, 
                                         verify=False)
        if userinfo_response.status_code == 200:
            user_data = userinfo_response.json()
            session['user_email'] = user_data.get('email')

        return redirect(url_for('index'))
    else:
        return f"Error al obtener el token: {token_response.text}", 400

@app.route('/logout')
def logout():
    session.clear()
    return redirect(f"{LOGOUT_ENDPOINT}?client_id={CLIENT_ID}&post_logout_redirect_uri=http://localhost:5000/")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)