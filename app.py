from flask import Flask, render_template, request, jsonify, session, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
import os

# ====================== CONFIG ======================
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)

app.secret_key = "sollanches-2026-super-secret-key"

# ====================== BANCO ======================
instance_path = os.path.join(BASE_DIR, "instance")
os.makedirs(instance_path, exist_ok=True)

app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(instance_path, 'sollanches.db')}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ====================== MODELOS ======================
class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    categoria = db.Column(db.String(50))
    preco = db.Column(db.Float, nullable=False)
    descricao = db.Column(db.Text)
    imagem = db.Column(db.String(300))

class Pedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.DateTime, default=datetime.utcnow)
    itens = db.Column(db.Text)
    total = db.Column(db.Float)
    status = db.Column(db.String(30), default="Recebido")

# ====================== CARRINHO ======================
@app.context_processor
def cart_count():
    carrinho = session.get("carrinho", [])
    total = sum(i.get("quantidade", 1) for i in carrinho)
    return {"total_itens_carrinho": total}

# ====================== ROTAS ======================
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/cardapio")
def cardapio():
    itens = Item.query.all()
    return render_template("cardapio.html", itens=itens)

@app.route("/carrinho")
def carrinho():
    carrinho = session.get("carrinho", [])
    total = sum(i["preco"] * i["quantidade"] for i in carrinho)
    return render_template("carrinho.html", carrinho=carrinho, total=total)

@app.route("/checkout")
def checkout():
    carrinho = session.get("carrinho", [])
    if not carrinho:
        return redirect("/cardapio")

    total = sum(i["preco"] * i["quantidade"] for i in carrinho)
    return render_template("checkout.html", carrinho=carrinho, total=total)

# ====================== API CARRINHO ======================
@app.route("/api/adicionar", methods=["POST"])
def adicionar():
    data = request.get_json()
    item = Item.query.get(data.get("item_id"))

    if not item:
        return jsonify({"erro": "Item não encontrado"}), 404

    if "carrinho" not in session:
        session["carrinho"] = []

    carrinho = session["carrinho"]

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

    return jsonify({
        "ok": True,
        "total_itens": sum(i["quantidade"] for i in carrinho)
    })

# ====================== FINALIZAR ======================
@app.route("/finalizar", methods=["POST"])
def finalizar():
    carrinho = session.get("carrinho", [])

    if not carrinho:
        return redirect("/cardapio")

    total = sum(i["preco"] * i["quantidade"] for i in carrinho)

    pedido = Pedido(
        itens=json.dumps(carrinho),
        total=total
    )

    db.session.add(pedido)
    db.session.commit()

    session.pop("carrinho", None)

    return render_template("sucesso.html", pedido_id=pedido.id, total=total)

# ====================== ADMIN ======================
@app.route("/admin")
def admin():
    pedidos = Pedido.query.order_by(Pedido.data.desc()).all()
    total_vendas = sum(p.total for p in pedidos)

    return render_template(
        "admin_dashboard.html",
        pedidos=pedidos,
        total_vendas=total_vendas,
        total_pedidos=len(pedidos)
    )

# ====================== FIX IMAGENS (IMPORTANTE) ======================
@app.route("/fix-imagens")
def fix_imagens():
    itens = Item.query.all()

    for i in itens:
        if not i.imagem.startswith("/static/"):
            i.imagem = "/static/images/hamburgers/" + i.imagem

    db.session.commit()
    return "Imagens corrigidas com sucesso"

# ====================== INIT DB ======================
def init_db():
    db.create_all()

    if Item.query.count() == 0:
        itens = [
            ("Bauru", 9.0, "bauru_old.webp"),
            ("X-Bacon", 13.0, "x-bacon.webp"),
            ("X-Egg Bacon", 14.0, "x-egg-bacon.webp"),
            ("X-Tudo", 20.0, "x-tudo.webp"),
            ("X-Sol", 25.0, "xsol.webp"),
        ]

        for nome, preco, img in itens:
            db.session.add(Item(
                nome=nome,
                categoria="Lanches",
                preco=preco,
                descricao=nome,
                imagem=f"/static/images/hamburgers/{img}"
            ))

        db.session.commit()

# ====================== START ======================
with app.app_context():
    init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
