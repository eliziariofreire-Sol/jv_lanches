from flask import Flask, render_template, request, jsonify, session, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
import os

app = Flask(__name__)

# ====================== CRIA PASTA INSTANCE ======================
os.makedirs("instance", exist_ok=True)

app.secret_key = "jvlanches-2026-super-secret"

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///jvlanches.db'
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

    total = sum(
        item["preco"] * item["quantidade"]
        for item in carrinho
    )

    return render_template(
        "checkout.html",
        carrinho=carrinho,
        total=total
    )

# ====================== ITEM ======================
@app.route("/item/<int:item_id>")
def item_detail(item_id):
    item = Item.query.get_or_404(item_id)

    return render_template(
        "item_detail.html",
        item=item
    )

# ====================== API ADICIONAR ======================
@app.route("/api/adicionar", methods=["POST"])
def adicionar():
    data = request.get_json()

    item_id = data.get("item_id")

    item = db.session.get(Item, item_id)

    if not item:
        return jsonify({
            "erro": "Item não encontrado"
        }), 404

    if "carrinho" not in session:
        session["carrinho"] = []

    session["carrinho"].append({
        "id": item.id,
        "nome": item.nome,
        "preco": item.preco,
        "quantidade": 1
    })

    session.modified = True

    total_itens = len(session["carrinho"])

    return jsonify({
        "sucesso": True,
        "total_itens": total_itens
    })

# ====================== CHECKOUT ======================
@app.route("/checkout")
def checkout():
    carrinho = session.get("carrinho", [])

    if not carrinho:
        return redirect("/cardapio")

    total = sum(
        item["preco"] * item["quantidade"]
        for item in carrinho
    )

    return render_template(
        "checkout.html",
        carrinho=carrinho,
        total=total
    )

# ====================== FINALIZAR ======================
@app.route("/finalizar", methods=["POST"])
def finalizar_pedido():
    carrinho = session.get("carrinho", [])

    if not carrinho:
        return redirect("/cardapio")

    total = sum(
        item["preco"] * item["quantidade"]
        for item in carrinho
    )

    pedido = Pedido(
        itens=json.dumps(carrinho),
        total=total,
        nome_cliente=request.form.get("nome"),
        telefone=request.form.get("telefone"),
        endereco=request.form.get("endereco"),
        forma_pagamento=request.form.get(
            "pagamento",
            "Dinheiro"
        )
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

    if usuario == "admin" and senha == "jv123":
        session["admin"] = True
        return redirect("/admin/dashboard")

    return render_template(
        "admin_login.html",
        erro="Credenciais inválidas"
    )

# ====================== DASHBOARD ======================
@app.route("/admin/dashboard")
def admin_dashboard():

    if not session.get("admin"):
        return redirect("/admin")

    hoje = datetime.now().date()

    pedidos = Pedido.query.filter(
        db.func.date(Pedido.data) == hoje
    ).order_by(
        Pedido.data.desc()
    ).all()

    total_vendas = sum(
        pedido.total
        for pedido in pedidos
    )

    total_pedidos = len(pedidos)

    return render_template(
        "admin_dashboard.html",
        pedidos=pedidos,
        total_vendas=round(total_vendas, 2),
        total_pedidos=total_pedidos
    )

# ====================== LOGOUT ======================
@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect("/admin")

# ====================== BANCO ======================
def iniciar_banco():

    db.create_all()

    if Item.query.count() == 0:

        cardapio = [

            (
                "Bauru",
                "Lanches",
                9.00,
                "Pão, bife, ovo, frango",
                "/static/images/hamburgers/bauru_old.png"
            ),

            (
                "X-Bacon",
                "Lanches",
                13.00,
                "Pão, bife, bacon, queijo",
                "/static/images/hamburgers/x-bacon.png"
            ),

            (
                "X-Egg Bacon",
                "Lanches",
                14.00,
                "Pão, bacon, ovo",
                "/static/images/hamburgers/x-egg-bacon.png"
            ),

            (
                "X-Tudo",
                "Lanches",
                20.00,
                "Completo da casa",
                "/static/images/hamburgers/x-tudo.png"
            ),

            (
                "X-Sol",
                "Lanches",
                25.00,
                "Especial da casa",
                "/static/images/hamburgers/xsol.png"
            ),
        ]

        for nome, cat, preco, desc, img in cardapio:

            db.session.add(
                Item(
                    nome=nome,
                    categoria=cat,
                    preco=preco,
                    descricao=desc,
                    imagem=img
                )
            )

        db.session.commit()

# ====================== START ======================
with app.app_context():
    iniciar_banco()

if __name__ == "__main__":

    port = int(
        os.environ.get("PORT", 5000)
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
