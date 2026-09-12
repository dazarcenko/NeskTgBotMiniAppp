import asyncio
import json
import os
import secrets
from pathlib import Path

import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import WebAppInfo, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from database import get_db, init_db

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
WEBAPP_URL = os.getenv("WEBAPP_URL")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не указан")
if not ADMIN_ID:
    raise RuntimeError("ADMIN_ID не указан")
if not WEBAPP_URL:
    raise RuntimeError("WEBAPP_URL не указан")

BASE_DIR = Path(__file__).parent
WEB_DIR = BASE_DIR / "web"
UPLOAD_DIR = WEB_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

init_db()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def start_handler(message: Message):
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="🛍 Открыть магазин", web_app=WebAppInfo(url=WEBAPP_URL))
    await message.answer(
        "👋 Добро пожаловать!\n\nНажми кнопку ниже, чтобы открыть магазин.",
        reply_markup=keyboard.as_markup(),
    )


app = FastAPI(title="Telegram Mini App")
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.get("/", response_class=HTMLResponse)
async def index():
    file = WEB_DIR / "index.html"
    if not file.exists():
        return HTMLResponse("web/index.html не найден", status_code=500)
    return file.read_text(encoding="utf-8")


@app.get("/api/categories")
async def categories():
    db = get_db()
    rows = db.execute("SELECT * FROM categories ORDER BY id").fetchall()
    db.close()
    return [dict(row) for row in rows]


@app.get("/api/products")
async def products(category_id: int | None = None):
    db = get_db()
    if category_id:
        rows = db.execute(
            "SELECT * FROM products WHERE category_id = ? AND available = 1 ORDER BY id DESC",
            (category_id,),
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM products WHERE available = 1 ORDER BY id DESC"
        ).fetchall()
    db.close()
    return [dict(row) for row in rows]


@app.post("/api/orders")
async def create_order(request: Request):
    data = await request.json()
    user = data.get("user", {})
    items = data.get("items", [])
    delivery = data.get("delivery", "Не указано")
    if not items:
        return JSONResponse({"ok": False, "error": "Корзина пустая"}, status_code=400)

    db = get_db()
    checked_items = []
    total = 0.0
    for item in items:
        try:
            product_id = int(item.get("id"))
            quantity = max(1, int(item.get("quantity", 1)))
        except (TypeError, ValueError):
            db.close()
            return JSONResponse({"ok": False, "error": "Некорректный товар"}, status_code=400)
        row = db.execute(
            "SELECT id, name, price FROM products WHERE id = ? AND available = 1",
            (product_id,),
        ).fetchone()
        if not row:
            db.close()
            return JSONResponse({"ok": False, "error": "Один из товаров недоступен"}, status_code=400)
        price = float(row["price"])
        checked_items.append({"id": row["id"], "name": row["name"], "price": price, "quantity": quantity})
        total += price * quantity

    telegram_id = user.get("id")
    username = user.get("username", "")
    first_name = user.get("first_name", "")
    cursor = db.execute(
        """INSERT INTO orders (telegram_id, username, first_name, items, total, delivery)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (telegram_id, username, first_name, json.dumps(checked_items, ensure_ascii=False), total, delivery),
    )
    order_id = cursor.lastrowid
    db.commit()
    db.close()

    await send_order_to_admin(order_id, username, first_name, telegram_id, checked_items, total, delivery)
    return {"ok": True, "order_id": order_id}


async def send_order_to_admin(order_id, username, first_name, telegram_id, items, total, delivery):
    username_text = f"@{username}" if username else "не указан"
    text = (
        f"🔔 <b>НОВЫЙ ЗАКАЗ #{order_id}</b>\n\n"
        f"👤 Имя: {first_name or 'не указано'}\n"
        f"🔗 Username: {username_text}\n"
        f"🆔 ID: <code>{telegram_id}</code>\n\n"
        f"📦 <b>Товары:</b>\n"
    )
    for item in items:
        text += f"• {item['name']} × {item['quantity']} — {item['price'] * item['quantity']:.2f} ₽\n"
    text += f"\n💰 <b>Итого:</b> {total:.2f} ₽\n📍 <b>Получение:</b> {delivery}"
    try:
        await bot.send_message(chat_id=int(ADMIN_ID), text=text, parse_mode="HTML")
    except Exception as error:
        print("Ошибка отправки админу:", error)


def check_password(password: str) -> bool:
    return secrets.compare_digest(password, ADMIN_PASSWORD)


ADMIN_HTML = r'''<!doctype html>
<html lang="ru"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Админка</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#f4f5f7;color:#151515;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif}.wrap{max-width:1000px;margin:auto;padding:24px 16px 60px}.top{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:20px}.top h1{margin:0}.card{background:#fff;border-radius:18px;padding:20px;margin:14px 0;box-shadow:0 5px 22px #0000000d}.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}@media(max-width:700px){.grid{grid-template-columns:1fr}}input,textarea,select,button{width:100%;padding:12px;border:1px solid #ddd;border-radius:11px;font:inherit}textarea{min-height:90px;resize:vertical}button{background:#111;color:#fff;border:0;cursor:pointer;font-weight:700}button.secondary{background:#eee;color:#111}button.danger{background:#c62828}.row{display:flex;gap:10px;align-items:center}.row>*{flex:1}.muted{color:#777}.product{display:grid;grid-template-columns:90px 1fr auto;gap:14px;align-items:center;border-top:1px solid #eee;padding:14px 0}.product img{width:90px;height:90px;object-fit:cover;border-radius:12px;background:#eee}.product:first-child{border-top:0}.cat{display:flex;gap:10px;align-items:center;padding:10px 0;border-top:1px solid #eee}.cat:first-child{border-top:0}.cat img{width:55px;height:55px;object-fit:cover;border-radius:10px;background:#eee}.hidden{display:none}.msg{padding:10px;border-radius:10px;margin:10px 0;background:#eef7ee}.err{background:#fdecec}
</style></head><body><div class="wrap">
<div class="top"><div><h1>⚙️ Админка магазина</h1><div class="muted">Товары и категории</div></div><button class="secondary" style="max-width:120px" onclick="location.reload()">Обновить</button></div>
<div id="msg"></div>
<div class="card"><h2>🔐 Доступ</h2><input id="password" type="password" placeholder="ADMIN_PASSWORD"><p class="muted">Пароль хранится только в этой вкладке браузера.</p></div>
<div class="card"><h2>📂 Категории</h2><div class="grid"><input id="catName" placeholder="Название категории"><input id="catImage" type="file" accept="image/jpeg,image/png,image/webp"></div><button onclick="addCategory()">Добавить категорию</button><div id="categories"></div></div>
<div class="card"><h2>➕ Новый товар</h2><div class="grid"><input id="name" placeholder="Название товара"><input id="price" type="number" step="0.01" placeholder="Цена"><select id="category"></select><input id="image" type="file" accept="image/jpeg,image/png,image/webp"></div><textarea id="description" placeholder="Описание товара"></textarea><button onclick="addProduct()">Добавить товар</button></div>
<div class="card"><h2>📦 Товары</h2><div id="products">Загрузка...</div></div>
</div><script>
let cats=[];const $=id=>document.getElementById(id);function msg(t,e=false){$('msg').innerHTML='<div class="msg '+(e?'err':'')+'">'+t+'</div>';setTimeout(()=>{$('msg').innerHTML=''},3000)}
function pass(){return $('password').value.trim()}async function api(url,opt={}){const r=await fetch(url,opt);const d=await r.json();if(!r.ok||d.ok===false)throw Error(d.error||'Ошибка');return d}
async function load(){try{cats=await (await fetch('/api/categories')).json();$('category').innerHTML=cats.map(c=>`<option value="${c.id}">${esc(c.name)}</option>`).join('');$('categories').innerHTML=cats.map(c=>`<div class="cat">${c.image?`<img src="${c.image}">`:'<div style="width:55px;height:55px"></div>'}<b>${esc(c.name)}</b><button class="danger" style="max-width:100px" onclick="delCat(${c.id})">Удалить</button></div>`).join('');const ps=await (await fetch('/api/products')).json();$('products').innerHTML=ps.length?ps.map(p=>`<div class="product">${p.image?`<img src="${p.image}">`:'<div></div>'}<div><b>${esc(p.name)}</b><div class="muted">${esc(p.description||'')}</div><strong>${Number(p.price).toFixed(2)} ₽</strong></div><button class="danger" style="max-width:100px" onclick="delProduct(${p.id})">Удалить</button></div>`).join(''):'<p class="muted">Товаров пока нет.</p>'}catch(e){msg(e.message,true)}}
async function addProduct(){try{if(!pass())throw Error('Введи пароль');if(!$('name').value.trim()||!$('price').value)throw Error('Заполни название и цену');const f=new FormData();f.append('password',pass());f.append('name',$('name').value.trim());f.append('description',$('description').value.trim());f.append('price',$('price').value);f.append('category_id',$('category').value);if($('image').files[0])f.append('image',$('image').files[0]);await api('/admin/products',{method:'POST',body:f});msg('Товар добавлен');$('name').value='';$('description').value='';$('price').value='';$('image').value='';load()}catch(e){msg(e.message,true)}}
async function addCategory(){try{if(!pass())throw Error('Введи пароль');if(!$('catName').value.trim())throw Error('Введи название категории');const f=new FormData();f.append('password',pass());f.append('name',$('catName').value.trim());if($('catImage').files[0])f.append('image',$('catImage').files[0]);await api('/admin/categories',{method:'POST',body:f});msg('Категория добавлена');$('catName').value='';$('catImage').value='';load()}catch(e){msg(e.message,true)}}
async function delProduct(id){if(!confirm('Удалить товар?'))return;try{const f=new FormData();f.append('password',pass());f.append('id',id);await api('/admin/products/delete',{method:'POST',body:f});load()}catch(e){msg(e.message,true)}}
async function delCat(id){if(!confirm('Удалить категорию? Товары в ней тоже будут удалены.'))return;try{const f=new FormData();f.append('password',pass());f.append('id',id);await api('/admin/categories/delete',{method:'POST',body:f});load()}catch(e){msg(e.message,true)}}
function esc(v){return String(v).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;')}load();
</script></body></html>'''


@app.get("/admin", response_class=HTMLResponse)
async def admin():
    return HTMLResponse(ADMIN_HTML)


def valid_image(image: UploadFile | None) -> str:
    if not image or not image.filename:
        return ""
    ext = Path(image.filename).suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise ValueError("Можно загружать только JPG, PNG или WEBP")
    return ext


@app.post("/admin/categories")
async def admin_add_category(password: str = Form(...), name: str = Form(...), image: UploadFile | None = File(None)):
    if not check_password(password):
        return {"ok": False, "error": "Неверный пароль"}
    name = name.strip()
    if not name:
        return {"ok": False, "error": "Название категории пустое"}
    try:
        ext = valid_image(image)
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    image_url = ""
    if image and ext:
        filename = secrets.token_hex(12) + ext
        (UPLOAD_DIR / filename).write_bytes(await image.read())
        image_url = f"/uploads/{filename}"
    db = get_db()
    db.execute("INSERT INTO categories (name, image) VALUES (?, ?)", (name, image_url))
    db.commit(); db.close()
    return {"ok": True}


@app.post("/admin/products")
async def add_product(password: str = Form(...), name: str = Form(...), description: str = Form(""), price: float = Form(...), category_id: int = Form(...), image: UploadFile | None = File(None)):
    if not check_password(password):
        return {"ok": False, "error": "Неверный пароль"}
    try:
        ext = valid_image(image)
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    if price < 0:
        return {"ok": False, "error": "Цена не может быть отрицательной"}
    db = get_db()
    cat = db.execute("SELECT id FROM categories WHERE id = ?", (category_id,)).fetchone()
    if not cat:
        db.close(); return {"ok": False, "error": "Категория не найдена"}
    image_url = ""
    if image and ext:
        filename = secrets.token_hex(12) + ext
        (UPLOAD_DIR / filename).write_bytes(await image.read())
        image_url = f"/uploads/{filename}"
    db.execute("INSERT INTO products (category_id,name,description,price,image,available) VALUES (?,?,?,?,?,1)", (category_id,name.strip(),description.strip(),price,image_url))
    db.commit(); db.close()
    return {"ok": True}


@app.post("/admin/products/delete")
async def delete_product(password: str = Form(...), id: int = Form(...)):
    if not check_password(password): return {"ok": False, "error": "Неверный пароль"}
    db=get_db(); db.execute("DELETE FROM products WHERE id=?", (id,)); db.commit(); db.close(); return {"ok": True}


@app.post("/admin/categories/delete")
async def delete_category(password: str = Form(...), id: int = Form(...)):
    if not check_password(password): return {"ok": False, "error": "Неверный пароль"}
    db=get_db(); db.execute("DELETE FROM products WHERE category_id=?", (id,)); db.execute("DELETE FROM categories WHERE id=?", (id,)); db.commit(); db.close(); return {"ok": True}


async def run_bot():
    print("🤖 Telegram bot started")
    await dp.start_polling(bot)


async def run_server():
    port = int(os.getenv("PORT", "8000"))
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    print(f"🌐 Server started on port {port}")
    await server.serve()


async def main():
    await asyncio.gather(run_bot(), run_server())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Приложение остановлено")
