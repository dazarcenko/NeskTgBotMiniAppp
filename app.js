const tg = window.Telegram.WebApp;

tg.ready();
tg.expand();


let cart = [];


const categoriesSection =
    document.getElementById(
        "categoriesSection"
    );


const productsSection =
    document.getElementById(
        "productsSection"
    );


const categoriesElement =
    document.getElementById(
        "categories"
    );


const productsElement =
    document.getElementById(
        "products"
    );


const categoryTitle =
    document.getElementById(
        "categoryTitle"
    );


const cartPage =
    document.getElementById(
        "cartPage"
    );


const checkoutPage =
    document.getElementById(
        "checkoutPage"
    );


const cartElement =
    document.getElementById(
        "cart"
    );


const cartButton =
    document.getElementById(
        "cartButton"
    );


const cartCount =
    document.getElementById(
        "cartCount"
    );


const totalElement =
    document.getElementById(
        "total"
    );


// =========================
// КАТЕГОРИИ
// =========================

async function loadCategories() {

    try {

        const response =
            await fetch(
                "/api/categories"
            );

        const categories =
            await response.json();


        categoriesElement.innerHTML = "";


        categories.forEach(
            category => {

                const button =
                    document.createElement(
                        "button"
                    );

                button.className =
                    "category";

                button.innerHTML =
                    `📦 ${escapeHtml(
                        category.name
                    )}`;


                button.onclick =
                    () => {

                        loadProducts(
                            category.id,
                            category.name
                        );

                    };


                categoriesElement.appendChild(
                    button
                );
            }
        );

    } catch (error) {

        console.error(error);

        categoriesElement.innerHTML =
            "<p>Не удалось загрузить категории.</p>";
    }
}


// =========================
// ТОВАРЫ
// =========================

async function loadProducts(
    categoryId,
    categoryName
) {

    categoriesSection.classList.add(
        "hidden"
    );

    productsSection.classList.remove(
        "hidden"
    );

    cartPage.classList.add(
        "hidden"
    );

    checkoutPage.classList.add(
        "hidden"
    );


    categoryTitle.textContent =
        categoryName;


    try {

        const response =
            await fetch(
                `/api/products?category_id=${categoryId}`
            );


        const products =
            await response.json();


        productsElement.innerHTML = "";


        if (products.length === 0) {

            productsElement.innerHTML =
                "<p>Товаров пока нет.</p>";

            return;
        }


        products.forEach(
            product => {

                const element =
                    document.createElement(
                        "div"
                    );

                element.className =
                    "product";


                element.innerHTML = `

                    ${
                        product.image
                        ?
                        `
                        <img
                            src="${product.image}"
                            alt=""
                        >
                        `
                        :
                        ""
                    }

                    <div class="product-content">

                        <h3>
                            ${escapeHtml(
                                product.name
                            )}
                        </h3>

                        <p class="description">
                            ${escapeHtml(
                                product.description || ""
                            )}
                        </p>

                        <div class="price">
                            ${Number(
                                product.price
                            ).toFixed(2)} ₽
                        </div>

                        <button
                            class="add-button"
                        >
                            Добавить в корзину
                        </button>

                    </div>
                `;


                const addButton =
                    element.querySelector(
                        ".add-button"
                    );


                addButton.onclick =
                    () => {

                        addToCart(
                            product
                        );

                    };


                productsElement.appendChild(
                    element
                );

            }
        );

    } catch (error) {

        console.error(error);

        productsElement.innerHTML =
            "<p>Не удалось загрузить товары.</p>";
    }
}


// =========================
// ДОБАВЛЕНИЕ В КОРЗИНУ
// =========================

function addToCart(product) {

    const existing =
        cart.find(
            item =>
                item.id === product.id
        );


    if (existing) {

        existing.quantity++;

    } else {

        cart.push({

            id: product.id,

            name: product.name,

            price: Number(
                product.price
            ),

            quantity: 1
        });
    }


    updateCart();


    if (
        tg.HapticFeedback
    ) {

        tg.HapticFeedback
            .impactOccurred(
                "light"
            );
    }
}


// =========================
// КОЛИЧЕСТВО
// =========================

function changeQuantity(
    id,
    delta
) {

    const item =
        cart.find(
            item =>
                item.id === id
        );


    if (!item) {
        return;
    }


    item.quantity += delta;


    if (
        item.quantity <= 0
    ) {

        cart =
            cart.filter(
                item =>
                    item.id !== id
            );
    }


    updateCart();
}


// =========================
// КОРЗИНА
// =========================

function updateCart() {

    const count =
        cart.reduce(
            (sum, item) =>
                sum + item.quantity,
            0
        );


    cartCount.textContent =
        count;


    if (count > 0) {

        cartButton.classList.remove(
            "hidden"
        );

    } else {

        cartButton.classList.add(
            "hidden"
        );
    }


    renderCart();
}


function renderCart() {

    if (cart.length === 0) {

        cartElement.innerHTML =
            "<p>Корзина пустая.</p>";

        totalElement.textContent =
            "0 ₽";

        return;
    }


    let total = 0;


    cartElement.innerHTML = "";


    cart.forEach(
        item => {

            const sum =
                item.price *
                item.quantity;


            total += sum;


            const element =
                document.createElement(
                    "div"
                );


            element.className =
                "cart-item";


            element.innerHTML = `

                <div>

                    <strong>
                        ${escapeHtml(
                            item.name
                        )}
                    </strong>

                    <div>
                        ${item.price.toFixed(2)} ₽
                    </div>

                </div>


                <div class="quantity">

                    <button>
                        −
                    </button>

                    <span>
                        ${item.quantity}
                    </span>

                    <button>
                        +
                    </button>

                </div>
            `;


            const buttons =
                element.querySelectorAll(
                    ".quantity button"
                );


            buttons[0].onclick =
                () =>
                    changeQuantity(
                        item.id,
                        -1
                    );


            buttons[1].onclick =
                () =>
                    changeQuantity(
                        item.id,
                        1
                    );


            cartElement.appendChild(
                element
            );

        }
    );


    totalElement.textContent =
        `${total.toFixed(2)} ₽`;
}


// =========================
// ОТКРЫТЬ КОРЗИНУ
// =========================

function openCart() {

    categoriesSection.classList.add(
        "hidden"
    );

    productsSection.classList.add(
        "hidden"
    );

    checkoutPage.classList.add(
        "hidden"
    );

    cartPage.classList.remove(
        "hidden"
    );


    window.scrollTo({
        top: 0,
        behavior: "smooth"
    });
}


// =========================
// НАЗАД В КАТАЛОГ
// =========================

function showCategories() {

    productsSection.classList.add(
        "hidden"
    );

    cartPage.classList.add(
        "hidden"
    );

    checkoutPage.classList.add(
        "hidden"
    );

    categoriesSection.classList.remove(
        "hidden"
    );


    window.scrollTo({
        top: 0,
        behavior: "smooth"
    });
}


// =========================
// ОФОРМЛЕНИЕ
// =========================

function checkout() {

    if (cart.length === 0) {

        tg.showAlert(
            "Корзина пустая"
        );

        return;
    }


    cartPage.classList.add(
        "hidden"
    );

    checkoutPage.classList.remove(
        "hidden"
    );


    window.scrollTo({
        top: 0,
        behavior: "smooth"
    });
}


// =========================
// ОТПРАВИТЬ ЗАКАЗ
// =========================

async function sendOrder() {

    if (cart.length === 0) {

        tg.showAlert(
            "Корзина пустая"
        );

        return;
    }


    const delivery =
        document.getElementById(
            "delivery"
        ).value;


    const user =
        tg.initDataUnsafe?.user || {};


    try {

        const response =
            await fetch(
                "/api/orders",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({

                        user: user,

                        items: cart,

                        delivery: delivery

                    })
                }
            );


        const result =
            await response.json();


        if (!result.ok) {

            tg.showAlert(
                result.error ||
                "Ошибка создания заказа"
            );

            return;
        }


        cart = [];

        updateCart();


        tg.showPopup({

            title:
                "Заказ оформлен",

            message:
                `Номер заказа: #${result.order_id}`,

            buttons: [
                {
                    type: "ok"
                }
            ]

        });


        checkoutPage.classList.add(
            "hidden"
        );

        categoriesSection.classList.remove(
            "hidden"
        );

    } catch (error) {

        console.error(error);

        tg.showAlert(
            "Не удалось отправить заказ"
        );
    }
}


// =========================
// ЗАЩИТА HTML
// =========================

function escapeHtml(
    value
) {

    return String(value)

        .replaceAll(
            "&",
            "&amp;"
        )

        .replaceAll(
            "<",
            "&lt;"
        )

        .replaceAll(
            ">",
            "&gt;"
        )

        .replaceAll(
            '"',
            "&quot;"
        )

        .replaceAll(
            "'",
            "&#039;"
        );
}


// =========================
// ЗАПУСК
// =========================

loadCategories();

updateCart();