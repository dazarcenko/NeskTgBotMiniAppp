import asyncio
import json
import os
import secrets
from pathlib import Path

import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message, WebAppInfo
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

UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True
)

init_db()


# =========================
# TELEGRAM BOT
# =========================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def start_handler(message: Message):

    keyboard = InlineKeyboardBuilder()

    keyboard.button(
        text="🛍 Открыть магазин",
        web_app=WebAppInfo(
            url=WEBAPP_URL
        )
    )

    await message.answer(
        "👋 Добро пожаловать!\n\n"
        "Нажми кнопку ниже, чтобы открыть магазин.",
        reply_markup=keyboard.as_markup()
    )


# =========================
# FASTAPI
# =========================

app = FastAPI(
    title="Telegram Mini App"
)


app.mount(
    "/static",
    StaticFiles(
        directory=WEB_DIR
    ),
    name="static"
)


app.mount(
    "/uploads",
    StaticFiles(
        directory=UPLOAD_DIR
    ),
    name="uploads"
)


@app.get(
    "/",
    response_class=HTMLResponse
)
async def index():

    file = WEB_DIR / "index.html"

    if not file.exists():

        return HTMLResponse(
            "web/index.html не найден",
            status_code=500
        )

    return file.read_text(
        encoding="utf-8"
    )


# =========================
# CATEGORIES
# =========================

@app.get("/api/categories")
async def categories():

    db = get_db()

    rows = db.execute(
        """
        SELECT *
        FROM categories
        ORDER BY id
        """
    ).fetchall()

    db.close()

    return [
        dict(row)
        for row in rows
    ]


# =========================
# PRODUCTS
# =========================

@app.get("/api/products")
async def products(
    category_id: int | None = None
):

    db = get_db()

    if category_id:

        rows = db.execute(
            """
            SELECT *
            FROM products
            WHERE category_id = ?
            AND available = 1
            ORDER BY id DESC
            """,
            (category_id,)
        ).fetchall()

    else:

        rows = db.execute(
            """
            SELECT *
            FROM products
            WHERE available = 1
            ORDER BY id DESC
            """
        ).fetchall()

    db.close()

    return [
        dict(row)
        for row in rows
    ]


# =========================
# CREATE ORDER
# =========================

@app.post("/api/orders")
async def create_order(
    request: Request
):

    data = await request.json()

    user = data.get(
        "user",
        {}
    )

    items = data.get(
        "items",
        []
    )

    delivery = data.get(
        "delivery",
        "Не указано"
    )

    if not items:

        return JSONResponse(
            {
                "ok": False,
                "error": "Корзина пустая"
            },
            status_code=400
        )


    total = 0

    for item in items:

        price = float(
            item.get("price", 0)
        )

        quantity = int(
            item.get("quantity", 1)
        )

        total += price * quantity


    telegram_id = user.get("id")
    username = user.get(
        "username",
        ""
    )
    first_name = user.get(
        "first_name",
        ""
    )


    db = get_db()

    cursor = db.execute(
        """
        INSERT INTO orders
        (
            telegram_id,
            username,
            first_name,
            items,
            total,
            delivery
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            telegram_id,
            username,
            first_name,
            json.dumps(
                items,
                ensure_ascii=False
            ),
            total,
            delivery
        )
    )

    order_id = cursor.lastrowid

    db.commit()
    db.close()


    await send_order_to_admin(
        order_id,
        username,
        first_name,
        telegram_id,
        items,
        total,
        delivery
    )


    return {
        "ok": True,
        "order_id": order_id
    }


# =========================
# SEND ORDER TO ADMIN
# =========================

async def send_order_to_admin(
    order_id,
    username,
    first_name,
    telegram_id,
    items,
    total,
    delivery
):

    username_text = (
        f"@{username}"
        if username
        else "не указан"
    )


    text = (
        f"🔔 <b>НОВЫЙ ЗАКАЗ #{order_id}</b>\n\n"
        f"👤 Имя: {first_name or 'не указано'}\n"
        f"🔗 Username: {username_text}\n"
        f"🆔 ID: <code>{telegram_id}</code>\n\n"
        f"📦 <b>Товары:</b>\n"
    )


    for item in items:

        name = item.get(
            "name",
            "Товар"
        )

        quantity = item.get(
            "quantity",
            1
        )

        price = float(
            item.get(
                "price",
                0
            )
        )

        text += (
            f"• {name} × {quantity} "
            f"— {price * quantity:.2f} ₽\n"
        )


    text += (
        f"\n💰 <b>Итого:</b> "
        f"{total:.2f} ₽\n"
        f"📍 <b>Получение:</b> "
        f"{delivery}"
    )


    try:

        await bot.send_message(
            chat_id=int(ADMIN_ID),
            text=text,
            parse_mode="HTML"
        )

    except Exception as error:

        print(
            "Ошибка отправки админу:",
            error
        )


# =========================
# ADMIN
# =========================

def check_password(
    password: str
):

    return secrets.compare_digest(
        password,
        ADMIN_PASSWORD
    )


@app.get(
    "/admin",
    response_class=HTMLResponse
)
async def admin():

    return HTMLResponse(
        """
        <h1>⚙️ Админка</h1>

        <p>
        Админка будет доступна по этому адресу.
        </p>

        <p>
        Здесь позже можно будет добавлять,
        изменять и удалять товары.
        </p>
        """
    )


# =========================
# ADMIN ADD PRODUCT
# =========================

@app.post(
    "/admin/products"
)
async def add_product(

    password: str = Form(...),

    name: str = Form(...),

    description: str = Form(""),

    price: float = Form(...),

    category_id: int = Form(...),

    image: UploadFile | None = File(None)

):

    if not check_password(
        password
    ):

        return {
            "ok": False,
            "error": "Неверный пароль"
        }


    image_url = ""


    if image:

        extension = Path(
            image.filename or ""
        ).suffix.lower()


        allowed = [
            ".jpg",
            ".jpeg",
            ".png",
            ".webp"
        ]


        if extension not in allowed:

            return {
                "ok": False,
                "error":
                    "Разрешены JPG, PNG и WEBP"
            }


        filename = (
            secrets.token_hex(12)
            + extension
        )


        file_path = (
            UPLOAD_DIR / filename
        )


        content = await image.read()

        file_path.write_bytes(
            content
        )


        image_url = (
            f"/uploads/{filename}"
        )


    db = get_db()

    db.execute(
        """
        INSERT INTO products
        (
            category_id,
            name,
            description,
            price,
            image,
            available
        )
        VALUES (?, ?, ?, ?, ?, 1)
        """,
        (
            category_id,
            name,
            description,
            price,
            image_url
        )
    )

    db.commit()
    db.close()


    return {
        "ok": True
    }


# =========================
# START EVERYTHING
# =========================

async def run_bot():

    print("🤖 Telegram bot started")

    await dp.start_polling(
        bot
    )


async def run_server():

    port = int(
        os.getenv(
            "PORT",
            "8000"
        )
    )

    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )

    server = uvicorn.Server(
        config
    )

    print(
        f"🌐 Server started on port {port}"
    )

    await server.serve()


async def main():

    await asyncio.gather(
        run_bot(),
        run_server()
    )


if __name__ == "__main__":

    try:

        asyncio.run(main())

    except KeyboardInterrupt:

        print(
            "Приложение остановлено"
        )