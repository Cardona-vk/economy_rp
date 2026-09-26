from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import database
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET', 'economy_rp_secret_key_123')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    message = None
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        password = request.form.get('password')

        # Usamos la función correcta del módulo database
        success, result = database.iniciar_sesion(usuario, password)
        if success:
            session['user_id'] = result['id_usuario'] if isinstance(result, dict) else result
            session['username'] = usuario
            return redirect(url_for('dashboard'))
        else:
            message = result

    return render_template('login.html', message=message)

@app.route('/register', methods=['GET', 'POST'])
def register():
    message = None
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        correo = request.form.get('correo')
        password = request.form.get('password')

        success, msg = database.registrar_jugador(usuario, correo, password)
        if success:
            return redirect(url_for('login'))
        else:
            message = msg

    return render_template('register.html', message=message)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- VISTAS ---

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', username=session['username'], player_id=session.get('user_id'))

@app.route('/history')
@login_required
def history():
    return render_template('history.html', username=session['username'])

@app.route('/admin')
@login_required
def admin():
    return render_template('admin.html', username=session['username'])

@app.route('/trade')
@login_required
def trade():
    user_id = session.get('user_id')
    if isinstance(user_id, dict):
        user_id = user_id.get('id_usuario') or user_id.get('id_jugador')

    inventario, msg = database.consultar_inventario(user_id)
    return render_template(
        'trade.html',
        username=session.get('username'),
        player_id=user_id,
        inventario=inventario or []
    )
@app.route('/api/dashboard')
@login_required
def api_dashboard():
    user_id = session.get('user_id')
    if isinstance(user_id, dict):
        user_id = user_id.get('id_usuario') or user_id.get('id_jugador')

    saldo, msg_saldo = database.consultar_saldo(user_id)
    inv, msg_inv = database.consultar_inventario(user_id)

    return jsonify({
        "saldo": saldo,
        "inventario": inv or [],
        "error": None if saldo is not None else msg_saldo
    })
@app.route('/api/trades/open', methods=['POST'])
@login_required
def api_open_trade():
    try:
        data = request.json
        user_id = session.get('user_id')

        if isinstance(user_id, dict):
            user_id = user_id.get('id_usuario') or user_id.get('id_jugador')

        try:
            user_id = int(user_id)
        except (TypeError, ValueError):
            return jsonify({"success": False, "message": "Error de sesión: ID de usuario inválido"}), 400

        try:
            destinatario = int(data.get('destinatario'))
        except (TypeError, ValueError):
            return jsonify({"success": False, "message": "ID de destinatario inválido"}), 400

        if user_id == destinatario:
            return jsonify({"success": False, "message": "No puedes iniciar una negociación contigo mismo."})

        success, msg = database.abrir_negociacion(
            user_id,
            destinatario,
            int(data.get('item_j1')) if data.get('item_j1') else None,
            None,
            float(data.get('monto_j1', 0)) if data.get('monto_j1') else 0.0,
            0,
            int(data.get('expiracion', 10))
        )

        return jsonify({"success": success, "message": msg})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error interno: {str(e)}"}), 400

@app.route('/api/trades/active', methods=['GET'])
@login_required
def api_trade_active():
    user_id = session.get('user_id')
    if isinstance(user_id, dict):
        user_id = user_id.get('id_usuario') or user_id.get('id_jugador')

    trade, msg = database.consultar_mesa_activa(user_id)
    if not trade:
        return jsonify({"success": False, "message": msg})

    return jsonify({"success": True, "data": trade})

@app.route('/api/trades/<int:id_trade>/status', methods=['GET'])
@login_required
def api_trade_status(id_trade):
    user_id = session.get('user_id')
    if isinstance(user_id, dict):
        user_id = user_id.get('id_usuario') or user_id.get('id_jugador')

    trade, msg = database.obtener_detalle_trade(id_trade)
    if not trade:
        return jsonify({"success": False, "message": msg}), 404

    return jsonify({
        "success": True,
        "data": trade
    })

@app.route('/api/trades/accept', methods=['POST'])
@login_required
def api_trades_accept():
    data = request.json
    id_trade = data.get('id_trade')
    user_id = session.get('user_id')

    if isinstance(user_id, dict):
        user_id = user_id.get('id_usuario') or user_id.get('id_jugador')

    if not id_trade:
        return jsonify({"success": False, "message": "ID de tradeo faltante"}), 400

    success, msg = database.aceptar_invitacion_trade(id_trade)
    return jsonify({"success": success, "message": msg})

@app.route('/api/trades/update_offer', methods=['POST'])
@login_required
def api_update_offer():
    data = request.json
    user_id = session.get('user_id')
    if isinstance(user_id, dict):
        user_id = user_id.get('id_usuario') or user_id.get('id_jugador')

    id_trade = data.get('id_trade')
    monto = data.get('monto', 0)
    id_item = data.get('id_item')

    success, msg = database.actualizar_oferta_jugador(id_trade, user_id, monto, id_item)
    return jsonify({"success": success, "message": msg})

@app.route('/api/trades/confirm', methods=['POST'])
@login_required
def api_trade_confirm():
    data = request.json
    user_id = session.get('user_id')
    if isinstance(user_id, dict):
        user_id = user_id.get('id_usuario') or user_id.get('id_jugador')

    id_trade = data.get('id_trade')
    success, msg = database.confirmar_oferta_jugador(id_trade, user_id)
    return jsonify({"success": success, "message": msg})

@app.route('/api/trades/cancel', methods=['POST'])
@login_required
def api_trade_cancel():
    data = request.json
    id_trade = data.get('id_trade')
    if not id_trade:
        return jsonify({"success": False, "message": "ID de tradeo faltante"}), 400

    success, msg = database.cancelar_tradeo(id_trade)
    return jsonify({"success": success, "message": msg})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
