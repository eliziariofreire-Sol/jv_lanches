from flask import Flask, render_template, request, jsonify, session, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
import os

# ====================== BASE ======================
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)

app.secret_key = "sol-lanches-2026-secret"

# ====================== BANCO ======================
instance_path = os.path.join(BASE_DIR, "instance")
os.makedirs(instance_path, exist_ok=True)

app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(instance_path, 'sollanches.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ====================== MODELOS ======================
class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    categoria = db.Column(db.String(50))
    preco = db.Column(db.Float)
    descricao = db.Column(db.Text)
    imagem = db.Column(db.String(300))

class Pedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.DateTime, default=datetime.utcnow)
    itens = db.Column(db.Text)
    total = db.Column(db.Float)
    status = db.Column(db.String(30), default="Recebido")
    nome_cliente = db.Column(db.String(100))
    telefone = db.Column(db.String(30))
    endereco = db.Column(db.Text)
    forma_pagamento = db.Column(db.String(30))

# ====================== CONTADOR CARRINHO ======================
@app.context_processor
def cart_count():
    carrinho = session.get("carrinho", [])
    total = sum(i.get("quantidade", 1) for i in carrinho)
    return {"total_itens_carrinho": total}

# ====================== HOME ======================
@app.route("/")
def home():
    return render_template("home.html")

# ====================== CARDÁPIO ======================
@app.route("/cardapio")
def cardapio():
    itens = Item.query.all()
    return render_template("cardapio.html", itens=itens)

# ====================== CARRINHO ======================
@app.route("/carrinho")
def carrinho():
    carrinho = session.get("carrinho", [])
    total = sum(i["preco"] * i["quantidade"] for i in carrinho)
    return render_template("carrinho.html", carrinho=carrinho, total=total)

# ====================== ADICIONAR ======================
@app.route("/api/adicionar", methods=["POST"])
def adicionar():
    data = request.get_json()
    item = Item.query.get(data["item_id"])

    if not item:
        return jsonify({"erro": "Item não encontrado"}), 404

    carrinho = session.get("carrinho", [])

    for i in carrinho:
        if i["id"] == item.id:
            i["quantidade"] += 1
            break
    else:
        carrinho.append({
            "id": item.id,
            "nome": item.nome,
            "preco": item.preco,
            "quantidade": 1
        })

    session["carrinho"] = carrinho
    session.modified = True

    return jsonify({"ok": True})

# ====================== ATUALIZAR ======================
@app.route("/api/atualizar", methods=["POST"])
def atualizar():
    data = request.get_json()
    carrinho = session.get("carrinho", [])

    for i in carrinho:
        if i["id"] == data["item_id"]:
            i["quantidade"] += data["quantidade"]

            if i["quantidade"] <= 0:
                carrinho.remove(i)
            break

    session["carrinho"] = carrinho
    session.modified = True

    return jsonify({"ok": True})

# ====================== REMOVER ======================
@app.route("/api/remover", methods=["POST"])
def remover():
    data = request.get_json()
    carrinho = session.get("carrinho", [])

    carrinho = [i for i in carrinho if i["id"] != data["item_id"]]

    session["carrinho"] = carrinho
    session.modified = True

    return jsonify({"ok": True})

# ====================== CHECKOUT ======================
@app.route("/checkout")
def checkout():
    carrinho = session.get("carrinho", [])
    if not carrinho:
        return redirect("/cardapio")

    total = sum(i["preco"] * i["quantidade"] for i in carrinho)
    return render_template("checkout.html", carrinho=carrinho, total=total)

# ====================== FINALIZAR ======================
@app.route("/finalizar", methods=["POST"])
def finalizar():
    carrinho = session.get("carrinho", [])

    total = sum(i["preco"] * i["quantidade"] for i in carrinho)

    pedido = Pedido(
        itens=json.dumps(carrinho),
        total=total,
        nome_cliente=request.form.get("nome"),
        telefone=request.form.get("telefone"),
        endereco=request.form.get("endereco"),
        forma_pagamento=request.form.get("pagamento")
    )

    db.session.add(pedido)
    db.session.commit()

    session.pop("carrinho", None)

    return render_template("sucesso.html", pedido_id=pedido.id, total=total)

# ====================== ADMIN ======================
@app.route("/admin")
def admin():
    return render_template("admin_login.html")

@app.route("/admin/login", methods=["POST"])
def admin_login():
    if request.form["usuario"] == "admin" and request.form["senha"] == "sol123":
        session["admin"] = True
        return redirect("/admin/dashboard")
    return redirect("/admin")

@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin"):
        return redirect("/admin")

    pedidos = Pedido.query.order_by(Pedido.data.desc()).all()

    return render_template(
        "admin_dashboard.html",
        pedidos=pedidos,
        total_vendas=sum(p.total for p in pedidos),
        total_pedidos=len(pedidos)
    )

# ====================== COZINHA ======================
@app.route("/cozinha")
def cozinha():
    return render_template("cozinha_login.html")

@app.route("/cozinha/login", methods=["POST"])
def cozinha_login():
    if request.form["usuario"] == "cozinha" and request.form["senha"] == "cozinha123":
        session["cozinha"] = True
        return redirect("/cozinha/dashboard")
    return redirect("/cozinha")

@app.route("/cozinha/dashboard")
def cozinha_dashboard():
    if not session.get("cozinha"):
        return redirect("/cozinha")

    pedidos = Pedido.query.filter(Pedido.status != "Finalizado").all()
    return render_template("cozinha_dashboard.html", pedidos=pedidos)

# ====================== STATUS ======================
@app.route("/api/status", methods=["POST"])
def status():
    data = request.get_json()

    pedido = Pedido.query.get(data["pedido_id"])
    pedido.status = data["status"]

    db.session.commit()

    return jsonify({"ok": True})

# ====================== INIT DB ======================
with app.app_context():
    db.create_all()

    if Item.query.count() == 0:
        itens = [
            ("Bauru", "Lanches", 9.0, "Bauru clássico", "/static/images/hamburgers/bauru_old.webp"),
            ("X-Bacon", "Lanches", 13.0, "Bacon e queijo", "/static/images/hamburgers/x-bacon.webp"),
            ("X-Egg Bacon", "Lanches", 14.0, "Bacon e ovo", "/static/images/hamburgers/x-egg-bacon.webp"),
            ("X-Tudo", "Lanches", 20.0, "Completo", "/static/images/hamburgers/x-tudo.webp"),
            ("X-Sol", "Lanches", 25.0, "Especial da casa", "/static/images/hamburgers/xsol.webp"),
        ]

        for i in itens:
            db.session.add(Item(nome=i[0], categoria=i[1], preco=i[2], descricao=i[3], imagem=i[4]))

        db.session.commit()

# ====================== START ======================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
