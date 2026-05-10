kfrom flask import Flask, render_template, request, jsonify, session, redirect
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

instance_path = os.path.join(BASE_DIR, "instance")
os.makedirs(instance_path, exist_ok=True)

app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(instance_path, 'sollanches.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ====================== TREE (DEBUG) ======================
@app.route("/tree")
def tree():
    base = BASE_DIR
    result = []

    for root, dirs, files in os.walk(base):
        level = root.replace(base, "").count(os.sep)
        if level > 2:
            continue

        indent = "  " * level
        result.append(f"{indent}{os.path.basename(root)}/")

        subindent = "  " * (level + 1)
        for f in files:
            result.append(f"{subindent}{f}")

    return "<pre>" + "\n".join(result) + "</pre>"

# ====================== MODELOS ======================
class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    categoria = db.Column(db.String(50))
    preco = db.Column(db.Float, nullable=False)
    descricao = db.Column(db.Text)
    imagem = db.Column(db.String(400))

class Pedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.DateTime, default=datetime.utcnow)
    itens = db.Column(db.Text)
    total = db.Column(db.Float)
    status = db.Column(db.String(30), default="Recebido")

# ====================== CONTEXT ======================
@app.context_processor
def inject_cart():
    carrinho = session.get("carrinho", [])
    total = sum(i.get("quantidade", 1) for i in carrinho)
    return {"total_itens_carrinho": total}

# ====================== HOME ======================
@app.route("/")
def home():
    return render_template("home.html")

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

# ====================== ADD ITEM ======================
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

# ====================== ATUALIZAR QUANTIDADE ======================
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
        total=total
    )

    db.session.add(pedido)
    db.session.commit()

    session.pop("carrinho", None)

    return render_template("sucesso.html", pedido_id=pedido.id, total=total)

# ====================== INIT DB ======================
def init_db():
    db.create_all()

    if Item.query.count() == 0:
        itens = [
            ("Bauru", 9, "/static/images/hamburgers/bauru_old.webp"),
            ("X-Bacon", 13, "/static/images/hamburgers/x-bacon.webp"),
            ("X-Egg Bacon", 14, "/static/images/hamburgers/x-egg-bacon.webp"),
            ("X-Tudo", 20, "/static/images/hamburgers/x-tudo.webp"),
            ("X-Sol", 25, "/static/images/hamburgers/xsol.webp"),
        ]

        for nome, preco, img in itens:
            db.session.add(Item(nome=nome, preco=preco, imagem=img))

        db.session.commit()

# ====================== START ======================
with app.app_context():
    init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
