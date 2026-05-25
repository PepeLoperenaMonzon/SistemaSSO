from flask import Flask, redirect, request, session, render_template
import requests
import os

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')

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
    )
    return redirect(auth_url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        print("[SSO App 3] Error: Código ausente.", flush=True)
        return redirect('/')

    token_data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    }
    
    token_response = requests.post(TOKEN_ENDPOINT, data=token_data, verify=False)
    
    try:
        token_json = token_response.json()
    except Exception as e:
        print(f"[CRÍTICO] Fallo HTTP en Token Endpoint", flush=True)
        print(f"Código de estado: {token_response.status_code}", flush=True)
        print(f"Respuesta de la red: {token_response.text}", flush=True)
        return f"Error de red interno. Revisa la terminal de Docker: {token_response.text}", 500

    if 'access_token' not in token_json:
        print(f"[SSO App 3] Error en intercambio de token: {token_json}", flush=True)
        return redirect('/')

    headers = {'Authorization': f"Bearer {token_json['access_token']}"}
    userinfo_response = requests.get(USERINFO_ENDPOINT, headers=headers, verify=False)
    
    if userinfo_response.status_code != 200:
        html_error = f"""
        <h1>¡Cazado! Error en UserInfo</h1>
        <h3>Código de Estado HTTP: {userinfo_response.status_code}</h3>
        <p><b>Lo que está devolviendo el servidor en lugar de un JSON es esto:</b></p>
        <div style='background:#eee; padding:15px; border:1px solid #ccc;'>
            {userinfo_response.text}
        </div>
        """
        return html_error, 500\

    session['userinfo'] = userinfo_response.json()
    return redirect('/')

@app.route('/logout')
def logout():
    session.clear()
    # Redirección externa tras el cierre de sesión al puerto 5002 visible en el navegador
    return redirect(f"{LOGOUT_ENDPOINT}?client_id={CLIENT_ID}&post_logout_redirect_uri=http://localhost:5002/")

if __name__ == '__main__':
    # Ejecución interna en puerto 5000 acorde al puente de Docker
    app.run(host='0.0.0.0', port=5000, debug=True)