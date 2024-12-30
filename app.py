from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import os
from reportlab.pdfgen import canvas
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
import os
print(f"Ruta absoluta de templates: {os.path.abspath('templates')}")


app = Flask(__name__)
app.secret_key = "clave_secreta_para_sesiones"  # Cambia esta clave para mayor seguridad

# Crear la base de datos y las tablas (si no existen)
def init_db():
    conn = sqlite3.connect('propiedades.db')
    cursor = conn.cursor()

    # Tabla de usuarios
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')

    # Tabla de propiedades
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS propiedades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            rol TEXT NOT NULL,
            fojas TEXT NOT NULL,
            numero TEXT NOT NULL,
            anio INTEGER NOT NULL,
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        )
    ''')

    # Tabla de pagos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pagos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            documentos TEXT NOT NULL,
            costo_total INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        )
    ''')

    conn.commit()
    conn.close()

# Inicializar la base de datos
init_db()

# Página de inicio
@app.route('/')
def index():
    if 'user_id' in session:
        # Si el usuario está autenticado, muestra la página principal con su nombre
        conn = sqlite3.connect('propiedades.db')
        cursor = conn.cursor()
        cursor.execute('SELECT username FROM usuarios WHERE id = ?', (session['user_id'],))
        user = cursor.fetchone()
        conn.close()

        return render_template('index.html', user=user[0] if user else None)
    # Si no está autenticado, simplemente carga la página de inicio
    return render_template('index.html', user=None)

# Registro de usuario
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)

        conn = sqlite3.connect('propiedades.db')
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO usuarios (username, password) VALUES (?, ?)', (username, hashed_password))
            conn.commit()
        except sqlite3.IntegrityError:
            return "El nombre de usuario ya existe. Por favor, elige otro.", 400
        finally:
            conn.close()

        return redirect('/')
    return render_template('registro.html')

# Inicio de sesión
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    conn = sqlite3.connect('propiedades.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, password FROM usuarios WHERE username = ?', (username,))
    user = cursor.fetchone()
    conn.close()

    if user and check_password_hash(user[1], password):
        session['user_id'] = user[0]
        return redirect('/')
    return "Usuario o contraseña incorrectos", 401

# Cerrar sesión
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect('/')

# Página de ingreso de datos de la propiedad
@app.route('/propiedad')
def propiedad():
    if 'user_id' not in session:
        return redirect('/')
    return render_template('propiedad.html')

# Procesar datos de la propiedad
@app.route('/procesar_propiedad', methods=['POST'])
def procesar_propiedad():
    if 'user_id' not in session:
        return redirect('/')
    
    usuario_id = session['user_id']
    rol = request.form['rol']
    fojas = request.form['fojas']
    numero = request.form['numero']
    anio = request.form['anio']

    conn = sqlite3.connect('propiedades.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO propiedades (usuario_id, rol, fojas, numero, anio) VALUES (?, ?, ?, ?, ?)',
                   (usuario_id, rol, fojas, numero, anio))
    conn.commit()
    conn.close()

    return redirect(url_for('seleccionar_documentos'))

# Página para seleccionar documentos
@app.route('/seleccionar_documentos')
def seleccionar_documentos():
    if 'user_id' not in session:
        return redirect('/')
    
    documentos = [
        {'nombre': 'Rol de Avalúo Fiscal', 'precio': 5000},
        {'nombre': 'Certificado de Número', 'precio': 4000},
        {'nombre': 'Certificado de No Expropiación Municipal', 'precio': 3000},
        {'nombre': 'Certificado de No Expropiación SERVIU', 'precio': 3000},
        {'nombre': 'Dominio Vigente', 'precio': 6000},
        {'nombre': 'Certificado de Hipotecas y Gravámenes', 'precio': 7000},
        {'nombre': 'Certificado de Matrimonio', 'precio': 2000},
        {'nombre': 'Certificado de Pago de Contribuciones', 'precio': 4000},
        {'nombre': 'Certificado de Movimiento de Contribuciones', 'precio': 3000},
        {'nombre': 'Certificado de Deuda de Contribuciones', 'precio': 3500},
    ]
    return render_template('seleccionar_documentos.html', documentos=documentos)

# Procesar documentos seleccionados
@app.route('/procesar_documentos', methods=['POST'])
def procesar_documentos():
    if 'user_id' not in session:
        return redirect('/')
    
    usuario_id = session['user_id']
    documentos_seleccionados = request.form.getlist('documentos')
    precios = {
        'Rol de Avalúo Fiscal': 5000,
        'Certificado de Número': 4000,
        'Certificado de No Expropiación Municipal': 3000,
        'Certificado de No Expropiación SERVIU': 3000,
        'Dominio Vigente': 6000,
        'Certificado de Hipotecas y Gravámenes': 7000,
        'Certificado de Matrimonio': 2000,
        'Certificado de Pago de Contribuciones': 4000,
        'Certificado de Movimiento de Contribuciones': 3000,
        'Certificado de Deuda de Contribuciones': 3500,
    }

    costo_total = sum(precios[doc] for doc in documentos_seleccionados)
    global datos_pago
    datos_pago = {
        'usuario_id': usuario_id,
        'documentos': documentos_seleccionados,
        'costo_total': costo_total
    }

    return redirect(url_for('pago'))

# Página de pago
@app.route('/pago')
def pago():
    if 'user_id' not in session or not datos_pago:
        return redirect('/')
    return render_template('pago.html', datos=datos_pago)

# Confirmar pago
@app.route('/confirmar_pago', methods=['POST'])
def confirmar_pago():
    if 'user_id' not in session or not datos_pago:
        return redirect('/')
    
    usuario_id = session['user_id']
    if not os.path.exists('generated_documents'):
        os.makedirs('generated_documents')

    documentos_generados = []
    for documento in datos_pago['documentos']:
        file_path = f"generated_documents/{documento.replace(' ', '_')}.pdf"
        c = canvas.Canvas(file_path)
        c.drawString(100, 750, f"Documento: {documento}")
        c.drawString(100, 730, f"Generado el: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        c.save()
        documentos_generados.append(file_path)

    conn = sqlite3.connect('propiedades.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO pagos (usuario_id, documentos, costo_total, fecha) VALUES (?, ?, ?, ?)', 
                   (usuario_id, ', '.join(datos_pago['documentos']), datos_pago['costo_total'], datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()

    datos_pago.clear()
    return render_template('descargar_documentos.html', documentos=documentos_generados)

# Servir documentos generados
@app.route('/generated_documents/<path:filename>')
def download_document(filename):
    return send_from_directory('generated_documents', filename, as_attachment=True)

# Mostrar propiedades guardadas
@app.route('/ver_propiedades')
def ver_propiedades():
    if 'user_id' not in session:
        return redirect('/')

    usuario_id = session['user_id']
    conn = sqlite3.connect('propiedades.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM propiedades WHERE usuario_id = ?', (usuario_id,))
    propiedades = cursor.fetchall()
    conn.close()

    return render_template('ver_propiedades.html', propiedades=propiedades)

# Mostrar pagos registrados
@app.route('/ver_pagos')
def ver_pagos():
    if 'user_id' not in session:
        return redirect('/')

    usuario_id = session['user_id']
    conn = sqlite3.connect('propiedades.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM pagos WHERE usuario_id = ?', (usuario_id,))
    pagos = cursor.fetchall()
    conn.close()

    return render_template('ver_pagos.html', pagos=pagos)

if __name__ == '__main__':
    import os

port = int(os.environ.get("PORT", 5000))  # Usa el puerto de Render o el 5000 por defecto
app.run(host="0.0.0.0", port=5000, debug=True)


