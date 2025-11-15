from flask import Flask, render_template, request, redirect, url_for, flash, session, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, timedelta
import json
import os
import requests # Necesario para la API de WhatsApp, aunque sea un placeholder
from flask_apscheduler import APScheduler # <--- ¡Nueva Importación!
import webbrowser # Para abrir el enlace de WhatsApp automáticamente

app = Flask(__name__)
app.secret_key = "067861b84dfa59352ff40b9943cf048ca7a401e5a6c21348"

# --- 📢 CONFIGURACIÓN DEL SCHEDULER ---
scheduler = APScheduler()

# --- FUNCIONES DE MANEJO DE DATOS (login.json y compras.json) ---

# 1. Función para cargar usuarios para LOGIN y CRUD (usa login.json)
def cargar_usuarios_login():
    nombre_archivo = "login.json"
    if os.path.exists(nombre_archivo):
        try:
            with open(nombre_archivo, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"⚠️ ERROR: El archivo {nombre_archivo} tiene un formato JSON incorrecto.")
            return []
    print(f"❌ ERROR: El archivo {nombre_archivo} no fue encontrado en la ruta: {os.getcwd()}") 
    return []

# 2. Función para guardar usuarios para LOGIN y CRUD (usa login.json)
def guardar_usuarios_login(usuarios):
    with open("login.json", "w", encoding="utf-8") as f:
        json.dump(usuarios, f, indent=4, ensure_ascii=False)

# 🟢 3. Nueva función para cargar los registros de COMPRAS (usa compras.json)
def cargar_compras():
    nombre_archivo = "compras.json"
    if os.path.exists(nombre_archivo):
        try:
            with open(nombre_archivo, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []

# 🟢 4. Nueva función para guardar los registros de COMPRAS (usa compras.json)
def guardar_compras(compras):
    with open("compras.json", "w", encoding="utf-8") as f:
        json.dump(compras, f, indent=4, ensure_ascii=False)


# --- FUNCIÓN DE VERIFICACIÓN DE ESTADO POR TIEMPO ---
def verificar_estado_usuario(usuario):
    # ... (Tu función existente, sin cambios) ...
    """Verifica si el tiempo de activación del usuario ha expirado."""
    
    if usuario.get("estado") == "Inactivo":
        return "Inactivo"
    
    fecha_activacion_str = usuario.get("fecha_activacion")
    duracion_dias = usuario.get("duracion_dias", 0)

    if fecha_activacion_str and duracion_dias > 0:
        try:
            fecha_activacion = datetime.strptime(fecha_activacion_str, "%Y-%m-%d %H:%M:%S")
            fecha_expiracion = fecha_activacion + timedelta(days=duracion_dias)
            
            if datetime.now() > fecha_expiracion:
                # ⚠️ Opcional: Podrías aquí cambiar el estado en el JSON, pero lo dejamos 
                # en 'Activo' para que la función de verificación lo detecte.
                return "Inactivo"
        except ValueError:
            pass
            
    return usuario.get("estado", "Inactivo")


# --- FUNCIONES DE ENVÍO DE MENSAJES (SIMULADO) ---
# 💡 ACTUALIZADO: Función para automatizar la apertura del enlace de WhatsApp
def enviar_whatsapp(numero, mensaje):
    """
    Simula el envío y automatiza la apertura del enlace de WhatsApp en el navegador.
    """
    # Codifica el mensaje para la URL (reemplazando espacios, saltos de línea y quitando asteriscos)
    mensaje_codificado = mensaje.replace(' ', '%20').replace('\n', '%0A').replace('*', '')
    
    # Crea el enlace de WhatsApp Web
    whatsapp_link = f"https://wa.me/{numero}?text={mensaje_codificado}"
    
    # 1. Abre el enlace automáticamente en una nueva pestaña del navegador
    try:
        webbrowser.open_new_tab(whatsapp_link)
        print(f"--- 📱 WHATSAPP AUTOMATIZADO ---")
        print(f"Abriendo enlace en navegador para: {numero}")
        print(f"ENLACE: {whatsapp_link}")
        print(f"---------------------------------")
        return True
    except Exception as e:
        print(f"⚠️ ERROR: No se pudo abrir el navegador. Verifica la configuración: {e}")
        print(f"ENLACE DE PRUEBA MANUAL: {whatsapp_link}")
        return False

def send_whatsapp_message_api(numero, mensaje):
    """
    Wrapper que simula una llamada a una API para enviar mensajes por WhatsApp.
    Actualmente reutiliza 'enviar_whatsapp' que abre el enlace en el navegador,
    pero puede reemplazarse por una integración real con una API (requests) si es necesario.
    """
    try:
        return enviar_whatsapp(numero, mensaje)
    except Exception as e:
        print(f"⚠️ ERROR en send_whatsapp_message_api: {e}")
        return False

# --- 🗓️ TAREA PROGRAMADA (JOB) ---
def check_notifications_and_send():
    """
    Tarea programada para verificar vencimientos de compras y enviar notificaciones.
    Se ejecuta una vez al día.
    """
    # ⚠️ Ajusta los días antes de notificar
    DIAS_ANTES_NOTIFICACION = 3 # Ejemplo: Notificar 3 días antes del vencimiento.
    
    print(f"--- ⏱️ Tarea programada: Revisando vencimientos para notificar ({DIAS_ANTES_NOTIFICACION} días antes)... ---")
    
    compras = cargar_compras()
    usuarios = cargar_usuarios_login()
    
    hoy = datetime.now().date()

    for compra in compras:
        try:
            # Si ya se envió el aviso, se salta el registro
            if compra.get("aviso_enviado"):
                continue

            fecha_vencimiento = datetime.strptime(compra["fecha_vencimiento"], "%Y-%m-%d").date()
            fecha_notificacion = fecha_vencimiento - timedelta(days=DIAS_ANTES_NOTIFICACION)
            
            # Revisar si HOY es el día de notificación
            if hoy == fecha_notificacion:
                
                # 1. Obtener datos de contacto del usuario
                usuario = next((u for u in usuarios if u["id"] == compra["usuario_id"]), None)
                
                if usuario and usuario.get("numero"):
                    
                    # 2. Construir el mensaje solicitado con TODOS los detalles
                    fecha_vencimiento_str = fecha_vencimiento.strftime("%d de %B del %Y")
                    
                    mensaje = (
                        f"¡Hola {usuario['nombre']}! 👋\n\n"
                        f"Tu servicio de {compra['plataforma']} vence en {DIAS_ANTES_NOTIFICACION} días, el {fecha_vencimiento_str}.\n\n"
                        f"Detalles de la cuenta:\n"
                        f"CORREO: {compra['correo_cuenta']}\n"
                        f"CONTRASEÑA: {compra['contrasena_cuenta']}\n"
                        f"PERFIL/PIN: {compra.get('perfil_pin', 'No aplica')}\n\n"
                        f"⚠️ ¡Renueva hoy mismo para evitar la interrupción del servicio! ⚠️\n"
                        f"FULL ENTRETENIMIENTO."
                    )
                    
                    # 3. Llamar a la función de envío API (simulada)
                    if send_whatsapp_message_api(usuario["numero"], mensaje):
                        # 4. Marcar la compra como notificada y guardar
                        compra["aviso_enviado"] = True
                        guardar_compras(compras)
                        print(f"✅ Notificación de vencimiento enviada con éxito al ID {usuario['id']}.")

        except Exception as e:
            print(f"❌ Error crítico al procesar la compra ID {compra.get('id', 'N/A')}: {e}")
            pass


# --- DECORADORES ---
def login_required(f):
    # ... (Tu decorador sin cambios) ...
    """Solo permite el acceso si hay sesión iniciada y controla el caché."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "logged_in" not in session:
            flash("Por favor inicia sesión primero.", "warning")
            return redirect(url_for("login"))
        
        response = make_response(f(*args, **kwargs))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    return wrapper


def admin_required(f):
    # ... (Tu decorador sin cambios) ...
    """Solo el admin puede acceder."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            flash("Por favor inicia sesión.", "warning")
            return redirect(url_for("login"))

        if session.get("correo") != "admin@gmail.com":
            flash("Acceso restringido: solo el administrador puede entrar aquí.", "danger")
            return redirect(url_for("index"))

        return f(*args, **kwargs)
    return wrapper


# --- RUTAS PRINCIPALES (login, logout, administracion, etc. - sin cambios funcionales) ---

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        correo = request.form.get("correo", "").strip().lower()
        password = request.form.get("password", "").strip()
        usuarios = cargar_usuarios_login()
        print("Usuarios cargados:", usuarios)
        print("Correo recibido (limpio):", correo)

        usuario = next((u for u in usuarios if u["correo"].strip().lower() == correo), None)
        if usuario is None:
            flash("Correo no registrado.", "danger")
            return render_template("login.html")
        password_db = usuario.get("password", "")
        login_exitoso = False

        if password_db and ('$' in password_db or password_db.startswith("pbkdf2") or password_db.startswith("scrypt")):
            if check_password_hash(password_db, password):
                login_exitoso = True
        else:
            if password_db == password:
                login_exitoso = True

        if not login_exitoso:
            flash("Contraseña incorrecta.", "danger")
            return render_template("login.html")

        estado_actual = verificar_estado_usuario(usuario)
        if estado_actual == "Inactivo":
            flash("Tu cuenta está inactiva o expiró.", "danger")
            return render_template("login.html")

        session["logged_in"] = True
        session["correo"] = usuario["correo"]
        session["nombre"] = usuario["nombre"]
        flash(f"Bienvenido {usuario['nombre']}!", "success")
        if usuario["correo"].strip().lower() == "admin@gmail.com":
            return redirect(url_for("administracion"))
        else:
            return redirect(url_for("index"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    # ... (Tu ruta logout sin cambios) ...
    session.clear()
    flash("Sesión cerrada correctamente.", "info")
    return redirect(url_for("login"))


@app.route("/administracion")
@admin_required
def administracion():
    # ... (Tu ruta administracion sin cambios funcionales) ...
    filtro = request.args.get("filtro")
    valor = request.args.get("valor")

    todos_los_usuarios = cargar_usuarios_login() 
    usuarios_a_mostrar = []
    
    if filtro == "mostrar_todo":
        usuarios_a_mostrar = todos_los_usuarios
    elif filtro and valor:
        usuarios_a_mostrar = [
            u for u in todos_los_usuarios 
            if valor.lower() in str(u.get(filtro, "")).lower()
        ]
    
    for u in usuarios_a_mostrar:
        u["estado_actual"] = verificar_estado_usuario(u)
        
        if u.get("fecha_activacion") and u.get("duracion_dias", 0) > 0:
            try:
                fecha_activacion = datetime.strptime(u["fecha_activacion"], "%Y-%m-%d %H:%M:%S")
                fecha_expiracion = fecha_activacion + timedelta(days=u["duracion_dias"])
                u["expiracion_str"] = fecha_expiracion.strftime("%Y-%m-%d")
            except ValueError:
                u["expiracion_str"] = "Error de fecha"
        else:
            u["expiracion_str"] = "Permanente"
            
    return render_template("administracion.html", usuarios=usuarios_a_mostrar)


@app.route("/verificar_vencimientos")
@admin_required
def verificar_vencimientos():
    # ... (Tu ruta verificar_vencimientos sin cambios) ...
    flash("Estados de vencimiento verificados. La tabla se ha recargado.", "info")
    return redirect(url_for("administracion"))


# --- CRUD USUARIOS (agregar, editar, inactivar - sin cambios funcionales) ---

@app.route("/agregar_usuario", methods=["POST"])
@admin_required
def agregar_usuario():
    # ... (Tu ruta agregar_usuario sin cambios funcionales) ...
    usuarios = cargar_usuarios_login()
    nuevo_id = max([u["id"] for u in usuarios], default=0) + 1

    nuevo_usuario = {
        "id": nuevo_id,
        "nombre": request.form["nombre"],
        "apellidos": request.form["apellidos"],
        "nacionalidad": request.form["nacionalidad"],
        "cedula": request.form["cedula"],
        "genero": request.form["genero"],
        "numero": request.form["numero"],
        "direccion": request.form["direccion"],
        "correo": request.form["correo"],
        "password": generate_password_hash(request.form.get("password", "12345")),
        "estado": "Activo",
        "fecha_activacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "duracion_dias": 0
    }

    usuarios.append(nuevo_usuario)
    guardar_usuarios_login(usuarios)
    flash("Usuario agregado correctamente.", "success")
    return redirect(url_for("administracion"))


@app.route("/editar_usuario/<int:id>", methods=["GET", "POST"])
@admin_required
def editar_usuario(id):
    usuarios = cargar_usuarios_login()
    usuario = next((u for u in usuarios if u["id"] == id), None)

    if not usuario:
        flash("Usuario no encontrado.", "danger")
        return redirect(url_for("administracion"))

    if request.method == "POST":
        usuario.update({
            "nombre": request.form["nombre"],
            "apellidos": request.form["apellidos"],
            "cedula": request.form["cedula"],
            "genero": request.form["genero"],
            "nacionalidad": request.form["nacionalidad"],
            "numero": request.form["numero"],
            "direccion": request.form["direccion"],
            "correo": request.form["correo"]
        })

        guardar_usuarios_login(usuarios)
        flash("Usuario actualizado correctamente.", "success")
        return redirect(url_for("administracion"))

    # Si entra por GET, muestra el formulario con los datos actuales
    return render_template("editar_usuario.html", usuario=usuario)



@app.route("/inactivar_usuario/<int:id>", methods=["POST"])
@admin_required
def inactivar_usuario(id):
    # ... (Tu ruta inactivar_usuario sin cambios funcionales) ...
    usuarios = cargar_usuarios_login()
    usuario = next((u for u in usuarios if u["id"] == id), None)

    if not usuario:
        flash("Usuario no encontrado.", "danger")
        return redirect(url_for("administracion"))
        
    accion = request.form.get("accion")

    if accion == "activar":
        try:
            duracion_dias = int(request.form.get("duracion_dias", 0))
        except ValueError:
            duracion_dias = 0

        usuario["estado"] = "Activo"
        usuario["fecha_activacion"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        usuario["duracion_dias"] = duracion_dias
        
        if duracion_dias > 0:
            fecha_exp = (datetime.now() + timedelta(days=duracion_dias)).strftime('%Y-%m-%d')
            flash(f"Usuario activado por {duracion_dias} días. Expira el {fecha_exp}.", "success")
        else:
            flash("Usuario activado permanentemente.", "success")
            
    elif accion == "inactivar":
        usuario["estado"] = "Inactivo"
        usuario["fecha_activacion"] = None 
        usuario["duracion_dias"] = 0
        flash("Usuario inactivado permanentemente.", "info")
    else:
        flash("Acción de activación/inactivación inválida.", "warning")
    
    guardar_usuarios_login(usuarios)
    return redirect(url_for("administracion"))

# 🟢 RUTA CORREGIDA: Registrar Compra/Servicio con automatización y envío inmediato
@app.route("/registrar_compra/<int:id>", methods=["POST"])
@admin_required
def registrar_compra(id):
    # Cargar usuarios para obtener el nombre y número de teléfono
    usuarios = cargar_usuarios_login()
    usuario = next((u for u in usuarios if u["id"] == id), None)

    if not usuario:
        flash("Usuario no encontrado.", "danger")
        return redirect(url_for("administracion"))

    compras = cargar_compras()
    
    # 1. Calcular la fecha de vencimiento
    fecha_compra_str = request.form["fecha_compra"] # 'YYYY-MM-DD'
    duracion_dias = int(request.form.get("duracion_dias", 0))
    
    try:
        fecha_compra = datetime.strptime(fecha_compra_str, "%Y-%m-%d")
        fecha_vencimiento = fecha_compra + timedelta(days=duracion_dias)
        fecha_vencimiento_str = fecha_vencimiento.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        flash("Error en el formato de fecha o duración.", "danger")
        return redirect(url_for("administracion"))
        
    
    nueva_data_compra = {
        "usuario_id": id,
        "plataforma": request.form["plataforma"],
        "fecha_compra": fecha_compra_str,
        "duracion_dias": duracion_dias,
        "fecha_vencimiento": fecha_vencimiento_str, # Clave para el scheduler
        "correo_cuenta": request.form["correo_cuenta"],
        "contrasena_cuenta": request.form["contrasena_cuenta"],
        "perfil_pin": request.form.get("perfil_pin", "N/A"),
        "aviso_enviado": False # Reiniciar el aviso para la nueva compra
    }

    # Lógica de guardado/actualización
    ultima_compra = next((c for c in compras if c["usuario_id"] == id), None)
    if ultima_compra:
        ultima_compra.update(nueva_data_compra)
        mensaje_flash = f"Compra del usuario {usuario['nombre']} actualizada."
    else:
        nueva_data_compra["id"] = max([c.get("id", 0) for c in compras], default=0) + 1
        compras.append(nueva_data_compra)
        mensaje_flash = f"Nueva compra registrada."

    guardar_compras(compras)

    # 2. 🚀 AUTOMATIZACIÓN INMEDIATA DEL ENVÍO DE BIENVENIDA (MOVIDO AL FINAL)
    try:
        mensaje_confirmacion = (
            f"🎉 ¡Bienvenido, *{usuario['nombre']}*! 🎉\n"
            f"Hemos registrado tu compra de *{nueva_data_compra['plataforma']}*.\n\n"
            f"Tus datos de acceso son:\n"
            f"Correo: {nueva_data_compra['correo_cuenta']}\n"
            f"Contraseña: {nueva_data_compra['contrasena_cuenta']}\n"
            f"Perfil/PIN: {nueva_data_compra['perfil_pin']}\n\n"
            f"Tu suscripción expira el: *{fecha_vencimiento_str}*.\n"
            f"¡Disfruta!"
        )
        
        # Llama a la función que abre el navegador
        enviar_whatsapp(usuario["numero"], mensaje_confirmacion)
        mensaje_flash += " Notificación de bienvenida automatizada."
        
    except Exception as e:
        print(f"⚠️ Error al intentar automatizar el envío de WhatsApp: {e}")
        mensaje_flash += " Error al enviar notificación."

    # 3. Finalizar (RETURN ÚNICO)
    flash(mensaje_flash, "success")
    return redirect(url_for("administracion"))

# 🟢 NUEVA RUTA: Obtener Compras por Usuario (para cargar en el modal)
@app.route("/obtener_compras_usuario/<int:id>")
@admin_required
def obtener_compras_usuario(id):
    # Carga todas las compras registradas
    compras_usuario = [c for c in cargar_compras() if c["usuario_id"] == id]
    
    # Prepara los datos para la plantilla (calcula el estado)
    hoy = datetime.now().date()
    for compra in compras_usuario:
        try:
            fecha_vencimiento = datetime.strptime(compra["fecha_vencimiento"], "%Y-%m-%d").date()
            dias_restantes = (fecha_vencimiento - hoy).days
            
            if dias_restantes < 0:
                compra["estado_actual"] = "VENCIDO"
            elif dias_restantes <= 5: 
                compra["estado_actual"] = f"Por vencer en {dias_restantes} días"
            else:
                compra["estado_actual"] = "Activo"
        except Exception:
            compra["estado_actual"] = "Error de fecha"

    # Renderiza un fragmento HTML (necesitarás crear este archivo)
    return render_template("_tabla_compras_modal.html", compras=compras_usuario)
    
# 🟢 RUTA CORREGIDA: Ver TODAS las Compras
# El endpoint es 'ver_todas_compras' y la URL es '/ver_todas_compras'
@app.route("/ver_todas_compras") 
@admin_required
def ver_todas_compras(): 
    """
    Carga todos los registros de compras para mostrarlos en una tabla general.
    """
    compras_registradas = cargar_compras()
    usuarios = cargar_usuarios_login()
    hoy = datetime.now().date()
    
    # Prepara la lista final de compras con datos de usuario y estado
    compras_a_mostrar = []
    
    for compra in compras_registradas:
        # 1. Obtener el nombre del usuario
        usuario = next((u for u in usuarios if u["id"] == compra["usuario_id"]), None)
        
        # 2. Determinar el estado actual de la compra
        compra_info = compra.copy()
        
        try:
            fecha_vencimiento = datetime.strptime(compra["fecha_vencimiento"], "%Y-%m-%d").date()
            dias_restantes = (fecha_vencimiento - hoy).days
            
            if dias_restantes < 0:
                compra_info["estado_actual"] = "VENCIDO"
            elif dias_restantes <= 5: 
                compra_info["estado_actual"] = f"Por vencer en {dias_restantes} días"
            else:
                compra_info["estado_actual"] = "Activo"
                
            compra_info["dias_restantes"] = dias_restantes
        except Exception:
            compra_info["estado_actual"] = "Error de fecha"
            compra_info["dias_restantes"] = -999

        # 3. Agregar información del usuario
        if usuario:
            compra_info["nombre_usuario"] = f"{usuario['nombre']} {usuario['apellidos']}"
            compra_info["correo_usuario"] = usuario["correo"]
        else:
            compra_info["nombre_usuario"] = "Usuario Eliminado"
            compra_info["correo_usuario"] = "N/A"
            
        compras_a_mostrar.append(compra_info)
        
    # Ordenar por fecha de vencimiento (los más próximos o vencidos primero)
    compras_a_mostrar.sort(key=lambda c: c.get("fecha_vencimiento", "9999-12-31"))

    # Renderiza una plantilla llamada "compras_generales.html" (necesitarás crearla)
    return render_template("compras_generales.html", compras=compras_a_mostrar)


# --- INICIO (sin cambios) ---
@app.route("/")
def index():
    # ... (Tu ruta index sin cambios) ...
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    return render_template("index.html")


# --- Crear hash manual (sin cambios) ---
@app.route("/create_hash/<password>")
def create_hash(password):
    # ... (Tu ruta create_hash sin cambios) ...
    return generate_password_hash(password)


# --- CONTACTO (sin cambios) ---
@app.route("/contacto")
def contacto():
    # ... (Tu ruta contacto sin cambios) ...
    return render_template("contacto.html") 




if __name__ == "__main__":
    # 1. Agregamos el job (tarea) al scheduler.
    scheduler.add_job(
        id='check_notifications', 
        func=check_notifications_and_send, 
        trigger='cron', 
        hour=9, # Ejecutar todos los días a las 9:00 AM
        minute=0, 
        timezone='America/Bogota' # ¡Ajusta tu zona horaria!
    )
    
    # 2. Iniciamos el scheduler con la instancia de la aplicación
    scheduler.init_app(app)
    scheduler.start()
    
    # 3. Correr Flask (use_reloader=False es necesario con el scheduler)
    app.run(debug=True, use_reloader=False)