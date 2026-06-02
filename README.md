# PoC: Sistema SSO Centralizado con Step-Up Authentication (mTLS)

Este repositorio contiene el código fuente y la infraestructura como código (IaC) del Trabajo Final de Máster: **Diseño e Implementación de un Sistema SSO Centralizado**. 

El proyecto demuestra una arquitectura *Zero Trust* segregada en zonas lógicas (DMZ y LAN Segura) utilizando contenedores Docker. Implementa Single Sign-On mediante OpenID Connect (OIDC) y escalada de privilegios (*Step-Up Authentication*) exigiendo certificados digitales X.509 (mTLS) para el acceso a recursos críticos.

## Arquitectura Tecnológica
* **Proxy Inverso (DMZ):** Nginx (Terminación SSL y validación mTLS).
* **Proveedor de Identidad (IdP):** Keycloak (Cluster HA).
* **Base de Datos:** PostgreSQL (Estado compartido).
* **Proveedores de Servicio (SP):** Aplicaciones web desarrolladas en Python (Flask).

## Requisitos Previos
Para ejecutar este entorno localmente, necesitas tener instalado:
* [Docker](https://docs.docker.com/get-docker/) y [Docker Compose](https://docs.docker.com/compose/install/)
* [OpenSSL](https://www.openssl.org/) (para la generación de certificados locales de prueba)
* Un navegador web moderno (Chrome/Firefox)

## Despliegue del Entorno (Setup)

### 1. Variables de Entorno
Crea un archivo `.env` en el directorio raíz (puedes copiar el archivo `.env.example` proporcionado). Asegúrate de configurar las credenciales básicas. Por defecto, el entorno espera las siguientes credenciales para la base de datos y la administración de Keycloak:

```ini
# Ejemplo de .env
DB_USER=admin
DB_PASSWORD=super_secret_password
DB_NAME=keycloak_db
KEYCLOAK_ADMIN=admin
KEYCLOAK_ADMIN_PASSWORD=admin
FLASK_CLIENT_SECRET_APP1=tu_secreto_aqui
FLASK_CLIENT_SECRET_APP2=tu_secreto_aqui
FLASK_CLIENT_SECRET_APP3=tu_secreto_aqui
```
# 2. Generacion de certificados (mTLS)
Antes de levantar los servicios, es necesario generar la Autoridad Certificadora (CA) raíz local y los certificados de cliente para la App 3. Ejecuta el script de preparación o los siguientes comandos OpenSSL en la carpeta /certs

```bash
# 1. Generar Root CA
openssl req -x509 -newkey rsa:4096 -keyout rootCA.key -out rootCA.crt -days 365 -nodes

# 2. Generar certificado de cliente (Empleado)
openssl req -newkey rsa:2048 -keyout empleado.key -out empleado.csr -nodes
openssl x509 -req -in empleado.csr -CA rootCA.crt -CAkey rootCA.key -CAcreateserial -out empleado.crt -days 365

# 3. Empaquetar en formato PKCS#12 para importar en el navegador
openssl pkcs12 -export -out empleado.p12 -inkey empleado.key -in empleado.crt -certfile rootCA.crt
```
Nota: Importa el archivo empleado.p12 en el almacén de certificados de tu navegador web antes de realizar las pruebas.

# 3. Ejecucion de la infraestructura 

Una vez configurado el .env y generados los certificados, levanta la infraestructura completa con Docker Compose:

```bash
docker-compose up -d --build
```
Este comando construirá las imágenes de Flask, descargará las de Nginx/Keycloak/PostgreSQL, creará las redes segregadas y levantará los contenedores en segundo plano.

## Uso y pruebas
Para comprobar la correcta delegación de identidades y la autenticación adaptativa, asegúrate de haber importado el Realm de prueba (tfm_realm.json) en Keycloak.

Añade las siguientes entradas a tu archivo hosts (/etc/hosts en Linux/Mac o C:\Windows\System32\drivers\etc\hosts en Windows) para la resolución local de DNS:

```plain
127.0.0.1 sso.tfm.local
127.0.0.1 mtls.sso.tfm.local
```

Accede a los siguientes portales para validar los flujos:

App 1 (Portal Base): http://localhost:5000 (Inicia sesión estándar en Keycloak).

App 2 (Navegación SSO): http://localhost:5001 (Acceso transparente mediante cookie de sesión global).

App 3 (Alta Seguridad): https://mtls.sso.tfm.local:5002 (Intercepción del proxy y solicitud del certificado X.509 al navegador).

## Detener el entorno 
Para detener todos los servicios y eliminar los contenedores y redes creadas:
```bash
docker-compose down
```
Si deseas eliminar los volúmenes persistentes (base de datos de PostgreSQL):
```bash
docker-compose down -v
```
