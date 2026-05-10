from flask import Flask, render_template, request, jsonify, session, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)

app.secret_key = "sollanches-2026-super-secret-key"

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/sollanches.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ====================== MODELOS ======================
class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    categoria = db.Column(db.String(50), nullable=False)
    preco = db.Column(db.Float, nullable=False)
    descricao = db.Column(db.Text)
    imagem = db.Column(db.String(400))

class Pedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.DateTime, default=datetime.utcnow)
    itens = db.Column(db.Text, nullable=False)
    total = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(30), default="Recebido")
    nome_cliente = db.Column(db.String(100))
    telefone = db.Column(db.String(20))
    endereco = db.Column(db.Text)
    forma_pagamento = db.Column(db.String(30))

# ====================== CONTEXT PROCESSOR ======================
@app.context_processor
def inject_cart_count():
    carrinho = session.get("carrinho", [])
    total_itens = sum(item.get("quantidade", 1) for item in carrinho)
    return {"total_itens_carrinho": total_itens}

# ====================== ROTAS PRINCIPAIS ======================
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/cardapio")
def cardapio():
    itens = Item.query.all()
    return render_template("cardapio.html", itens=itens)

@app.route("/carrinho")
def ver_carrinho():
    carrinho = session.get("carrinho", [])
    total = sum(item["preco"] * item["quantidade"] for item in carrinho)
    return render_template("carrinho.html", carrinho=carrinho, total=total)

@app.route("/checkout")
def checkout():
    carrinho = session.get("carrinho", [])
    if not carrinho:
        return redirect("/carrinho")
    total = sum(item["preco"] * item["quantidade"] for item in carrinho)
    return render_template("checkout.html", carrinho=carrinho, total=total)

@app.route("/item/<int:item_id>")
def item_detail(item_id):
    item = Item.query.get_or_404(item_id)
    return render_template("item_detail.html", item=item)

# ====================== API CARRINHO ======================
@app.route("/api/adicionar", methods=["POST"])
def adicionar():
    data = request.get_json()
    item_id = data.get("item_id")

    item = Item.query.get(item_id)
    if not item:
        return jsonify({"erro": "Item não encontrado"}), 404

    if "carrinho" not in session:
        session["carrinho"] = []

    carrinho = session["carrinho"]

    for produto in carrinho:
        if produto["id"] == item.id:
            produto["quantidade"] += 1
            break
    else:
        carrinho.append({
            "id": item.id,
            "nome": item.nome,
            "preco": item.preco,
            "quantidade": 1
        })

    session.modified = True
    total_itens = sum(item["quantidade"] for item in carrinho)

    return jsonify({
        "sucesso": True,
        "total_itens": total_itens
    })

@app.route("/api/remover", methods=["POST"])
def remover_do_carrinho():
    data = request.get_json()
    item_id = data.get("item_id")
    
    carrinho = session.get("carrinho", [])
    session["carrinho"] = [item for item in carrinho if item["id"] != item_id]
    session.modified = True
    return jsonify({"sucesso": True})

@app.route("/api/atualizar", methods=["POST"])
def atualizar_quantidade():
    data = request.get_json()
    item_id = data.get("item_id")
    quantidade = int(data.get("quantidade", 1))
    
    carrinho = session.get("carrinho", [])
    for item in carrinho:
        if item["id"] == item_id:
            item["quantidade"] = quantidade if quantidade > 0 else 1
            break
    session.modified = True
    return jsonify({"sucesso": True})

# ====================== FINALIZAR PEDIDO ======================
@app.route("/finalizar", methods=["POST"])
def finalizar_pedido():
    carrinho = session.get("carrinho", [])
    if not carrinho:
        return redirect("/cardapio")

    total = sum(item["preco"] * item["quantidade"] for item in carrinho)

    pedido = Pedido(
        itens=json.dumps(carrinho),
        total=total,
        nome_cliente=request.form.get("nome"),
        telefone=request.form.get("telefone"),
        endereco=request.form.get("endereco"),
        forma_pagamento=request.form.get("pagamento", "Dinheiro")
    )

    db.session.add(pedido)
    db.session.commit()

    session.pop("carrinho", None)

    return render_template(
        "sucesso.html",
        pedido_id=pedido.id,
        total=total,
        nome=request.form.get("nome")
    )

# ====================== ADMIN ======================
@app.route("/admin")
def admin_login():
    return render_template("admin_login.html")

@app.route("/admin/login", methods=["POST"])
def admin_login_post():
    usuario = request.form.get("usuario")
    senha = request.form.get("senha")

    if usuario == "admin" and senha == "sol123":
        session["admin"] = True
        return redirect("/admin/dashboard")
    return render_template("admin_login.html", erro="Credenciais inválidas")

@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin"):
        return redirect("/admin")

    pedidos = Pedido.query.order_by(Pedido.data.desc()).all()

    total_vendas = sum(pedido.total for pedido in pedidos)
    total_pedidos = len(pedidos)

    return render_template(
        "admin_dashboard.html",
        pedidos=pedidos,
        total_vendas=round(total_vendas, 2),
        total_pedidos=total_pedidos
    )

# ====================== COZINHA ======================
@app.route("/cozinha")
def cozinha_login():
    return render_template("cozinha_login.html")

@app.route("/cozinha/login", methods=["POST"])
def cozinha_login_post():
    usuario = request.form.get("usuario")
    senha = request.form.get("senha")

    if usuario == "cozinha" and senha == "cozinha123":
        session["cozinha"] = True
        return redirect("/cozinha/dashboard")
    return render_template("cozinha_login.html", erro="Credenciais inválidas")

@app.route("/cozinha/dashboard")
def cozinha_dashboard():
    if not session.get("cozinha"):
        return redirect("/cozinha")

    pedidos = Pedido.query.filter(
        Pedido.status.in_(["Recebido", "Preparando"])
    ).order_by(Pedido.data.desc()).all()

    return render_template("cozinha_dashboard.html", pedidos=pedidos)

# ====================== API STATUS ======================
@app.route("/api/atualizar_status", methods=["POST"])
def atualizar_status():
    if not session.get("cozinha") and not session.get("admin"):
        return jsonify({"erro": "Sem permissão"}), 403

    data = request.get_json()
    pedido_id = data.get("pedido_id")
    novo_status = data.get("status")

    pedido = Pedido.query.get_or_404(pedido_id)
    pedido.status = novo_status
    db.session.commit()
    return jsonify({"sucesso": True, "status": novo_status})

# ====================== LOGOUT ======================
@app.route("/admin/logout")
@app.route("/cozinha/logout")
def logout():
    session.pop("admin", None)
    session.pop("cozinha", None)
    return redirect("/")

# ====================== INICIALIZAR BANCO ======================
def iniciar_banco():
    db.create_all()

    if Item.query.count() == 0:
        cardapio = [
            ("Bauru", "Lanches", 9.00, "Pão, bife, ovo, frango", "/static/images/hamburgers/bauru_old.webp"),
            ("X-Bacon", "Lanches", 13.00, "Pão, bife, bacon, queijo", "/static/images/hamburgers/x-bacon.webp"),
            ("X-Egg Bacon", "Lanches", 14.00, "Pão, bacon, ovo", "/static/images/hamburgers/x-egg-bacon.webp"),
            ("X-Tudo", "Lanches", 20.00, "Completo da casa", "/static/images/hamburgers/x-tudo.webp"),
            ("X-Sol", "Lanches", 25.00, "Especial da casa", "/static/images/hamburgers/xsol.webp"),
        ]

        for nome, cat, preco, desc, img in cardapio:
            db.session.add(Item(nome=nome, categoria=cat, preco=preco, descricao=desc, imagem=img))
        db.session.commit()

# ====================== START ======================
with app.app_context():
    iniciar_banco()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
