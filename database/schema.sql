CREATE TABLE IF NOT EXISTS Users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    login TEXT NOT NULL UNIQUE CHECK(length(login) >= 6),
    password TEXT NOT NULL CHECK(length(password) >= 8),
    full_name TEXT NOT NULL,
    birth_date DATE,
    phone TEXT,
    email TEXT
);

CREATE TABLE IF NOT EXISTS Transport (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL CHECK(name IN ('Катер', 'Круизный лайнер', 'Яхта')),
    image_path TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS Applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    transport_id INTEGER NOT NULL,
    start_date DATE NOT NULL,
    payment_method TEXT NOT NULL,
    status TEXT DEFAULT 'Новая',
    FOREIGN KEY(user_id) REFERENCES Users(id),
    FOREIGN KEY(transport_id) REFERENCES Transport(id)
);

CREATE TABLE IF NOT EXISTS Reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    text TEXT NOT NULL,
    rating INTEGER CHECK(rating >= 1 AND rating <= 5),
    FOREIGN KEY(user_id) REFERENCES Users(id)
);
