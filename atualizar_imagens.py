from app import app, db, Item

with app.app_context():

    itens = Item.query.all()

    for item in itens:

        if ".png" in item.imagem:

            item.imagem = item.imagem.replace(".png", ".webp")

            print(item.nome, "->", item.imagem)

    db.session.commit()

print("imagens atualizadas")
