from flask import Flask, render_template, request, jsonify, session, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
import os

# ====================== CONFIGURAÇÃO DE PASTAS ======================
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)

app.secret_key = "sollanches-2026-super-secret-key"

# ====================== BANCO DE DADOS (CORRIGIDO) ======================
instance_path = os.path.join(BASE_DIR, "instance")
os.makedirs(instance_path, exist_ok=True)

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(instance_path, "sollanches.db")}'
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
    item = Item.query.get(data.get("item_id"))
    if not item:
        return jsonify({"erro": "Item não encontrado"}), 404

    if "carrinho" not in session:
        session["carrinho"] = []

    carrinho = session["carrinho"]
    for p in carrinho:
        if p["id"] == item.id:
            p["quantidade"] += 1
            break
    else:
        carrinho.append({
            "id": item.id,
            "nome": item.nome,
            "preco": item.preco,
            "quantidade": 1
        })

    session.modified = True
    return jsonify({"sucesso": True, "total_itens": sum(i["quantidade"] for i in carrinho)})

# ====================== FINALIZAR ======================
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

    return render_template("sucesso.html", pedido_id=pedido.id, total=total, nome=request.form.get("nome"))

# ====================== ADMIN ======================
@app.route("/admin")
def admin_login():
    return render_template("admin_login.html")

@app.route("/admin/login", methods=["POST"])
def admin_login_post():
    if request.form.get("usuario") == "admin" and request.form.get("senha") == "sol123":
        session["admin"] = True
        return redirect("/admin/dashboard")
    return render_template("admin_login.html", erro="Credenciais inválidas")

@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin"):
        return redirect("/admin")
    pedidos = Pedido.query.order_by(Pedido.data.desc()).all()
    return render_template("admin_dashboard.html", 
                         pedidos=pedidos, 
                         total_vendas=round(sum(p.total for p in pedidos), 2),
                         total_pedidos=len(pedidos))

# ====================== COZINHA ======================
@app.route("/cozinha")
def cozinha_login():
    return render_template("cozinha_login.html")

@app.route("/cozinha/login", methods=["POST"])
def cozinha_login_post():
    if request.form.get("usuario") == "cozinha" and request.form.get("senha") == "cozinha123":
        session["cozinha"] = True
        return redirect("/cozinha/dashboard")
    return render_template("cozinha_login.html", erro="Credenciais inválidas")

@app.route("/cozinha/dashboard")
def cozinha_dashboard():
    if not session.get("cozinha"):
        return redirect("/cozinha")
    pedidos = Pedido.query.filter(Pedido.status.in_(["Recebido", "Preparando"])).order_by(Pedido.data.desc()).all()
    return render_template("cozinha_dashboard.html", pedidos=pedidos)

# ====================== ATUALIZAR STATUS ======================
@app.route("/api/atualizar_status", methods=["POST"])
def atualizar_status():
    if not (session.get("cozinha") or session.get("admin")):
        return jsonify({"erro": "Sem permissão"}), 403
    data = request.get_json()
    pedido = Pedido.query.get_or_404(data.get("pedido_id"))
    pedido.status = data.get("status")
    db.session.commit()
    return jsonify({"sucesso": True})

# ====================== LOGOUT ======================
@app.route("/admin/logout")
@app.route("/cozinha/logout")
def logout():
    session.pop("admin", None)
    session.pop("cozinha", None)
    return redirect("/")

# ====================== INICIALIZAR BANCO ======================
def iniciar_banco():
    os.makedirs(instance_path, exist_ok=True)
    db.create_all()

    if Item.query.count() == 0:
        print("📋 Criando cardápio inicial...")
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
        print("✅ Cardápio criado!")

# ====================== START ======================
with app.app_context():
    iniciar_banco()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
