import sqlite3
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_name='accounts_bot.db'):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.init_database()

    def init_database(self):
        """Инициализация всех таблиц в базе данных"""

        # Таблица пользователей
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance REAL DEFAULT 0,
            is_admin INTEGER DEFAULT 0,
            registered_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Таблица промокодов (с улучшенной структурой)
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS promocodes (
            code TEXT PRIMARY KEY,
            amount REAL,
            used_count INTEGER DEFAULT 0,
            use_limit INTEGER DEFAULT 1,
            valid_until TIMESTAMP DEFAULT NULL,
            created_by INTEGER,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Таблица использования промокодов пользователями
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS promocode_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            promocode TEXT NOT NULL,
            used_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, promocode)
        )
        ''')

        # Таблица покупок
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            games TEXT,
            price REAL,
            account_id INTEGER,
            account_data TEXT,
            status TEXT DEFAULT 'completed',
            purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Таблица аккаунтов
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            password TEXT NOT NULL,
            games TEXT DEFAULT '',
            price REAL DEFAULT 400,
            added_by INTEGER,
            added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Таблица логов
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            details TEXT,
            log_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        self.conn.commit()
        logger.info("База данных инициализирована")

    # ========== Пользователи ==========
    def add_user(self, user_id, username):
        """Добавление пользователя"""
        self.cursor.execute(
            "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
            (user_id, username)
        )
        self.conn.commit()

    def get_user(self, user_id):
        """Получение данных пользователя"""
        self.cursor.execute(
            "SELECT username, balance, is_admin FROM users WHERE user_id = ?",
            (user_id,)
        )
        return self.cursor.fetchone()

    def get_all_users(self):
        """Получение всех пользователей"""
        self.cursor.execute(
            "SELECT user_id, username FROM users"
        )
        return self.cursor.fetchall()

    def get_users_count(self):
        """Получение количества пользователей"""
        self.cursor.execute("SELECT COUNT(*) FROM users")
        return self.cursor.fetchone()[0]

    def update_user_balance(self, user_id, amount):
        """Обновление баланса пользователя"""
        self.cursor.execute(
            "UPDATE users SET balance = balance + ? WHERE user_id = ?",
            (amount, user_id)
        )
        self.conn.commit()

    def set_user_balance(self, user_id, amount):
        """Установка баланса пользователя"""
        self.cursor.execute(
            "UPDATE users SET balance = ? WHERE user_id = ?",
            (amount, user_id)
        )
        self.conn.commit()

    def set_user_admin(self, user_id, is_admin=True):
        """Установка статуса админа"""
        self.cursor.execute(
            "UPDATE users SET is_admin = ? WHERE user_id = ?",
            (1 if is_admin else 0, user_id)
        )
        self.conn.commit()

    # ========== Промокоды (улучшенные) ==========
    def add_promocode(self, code, amount, created_by, use_limit=1, valid_until=None):
        """Добавление промокода с лимитом использования"""
        self.cursor.execute(
            "INSERT INTO promocodes (code, amount, created_by, use_limit, valid_until) VALUES (?, ?, ?, ?, ?)",
            (code, amount, created_by, use_limit, valid_until)
        )
        self.conn.commit()

    def get_promocode(self, code):
        """Получение промокода с проверкой валидности"""
        self.cursor.execute(
            "SELECT amount, used_count, use_limit, valid_until FROM promocodes WHERE code = ?",
            (code,)
        )
        return self.cursor.fetchone()

    def check_promocode_validity(self, code, user_id):
        """Проверка валидности промокода для конкретного пользователя"""
        promocode = self.get_promocode(code)
        if not promocode:
            return False, "Промокод не найден"

        amount, used_count, use_limit, valid_until = promocode

        # Проверяем, использовал ли уже этот пользователь данный промокод
        if self.has_user_used_promocode(user_id, code):
            return False, "Вы уже использовали этот промокод ранее"

        # Проверка лимита использования промокода (общего)
        if use_limit > 0 and used_count >= use_limit:
            return False, "Лимит использования промокода исчерпан"

        # Проверка срока действия
        if valid_until:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            if current_time > valid_until:
                return False, "Срок действия промокода истек"

        return True, f"Промокод действителен. Сумма: {amount} руб."

    def has_user_used_promocode(self, user_id, code):
        """Проверяет, использовал ли пользователь данный промокод"""
        self.cursor.execute(
            "SELECT id FROM promocode_usage WHERE user_id = ? AND promocode = ?",
            (user_id, code)
        )
        return self.cursor.fetchone() is not None

    def use_promocode(self, code, user_id):
        """Использование промокода пользователем"""
        # Проверяем валидность промокода для пользователя
        is_valid, message = self.check_promocode_validity(code, user_id)
        if not is_valid:
            return False, message

        # Получаем данные промокода
        promocode_data = self.get_promocode(code)
        if not promocode_data:
            return False, "Промокод не найден"

        amount, used_count, use_limit, valid_until = promocode_data

        # Начинаем транзакцию
        try:
            # Увеличиваем общий счетчик использования промокода
            self.cursor.execute(
                "UPDATE promocodes SET used_count = used_count + 1 WHERE code = ?",
                (code,)
            )

            # Записываем, что пользователь использовал промокод
            self.cursor.execute(
                "INSERT INTO promocode_usage (user_id, promocode) VALUES (?, ?)",
                (user_id, code)
            )

            self.conn.commit()
            return True, amount

        except sqlite3.IntegrityError:
            # Пользователь уже использовал промокод (unique constraint violation)
            self.conn.rollback()
            return False, "Вы уже использовали этот промокод"
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Ошибка при использовании промокода: {e}")
            return False, "Ошибка при обработке промокода"

    def get_user_promocode_history(self, user_id, limit=10):
        """Получить историю использования промокодов пользователем"""
        self.cursor.execute("""
            SELECT pu.promocode, p.amount, pu.used_date
            FROM promocode_usage pu
            JOIN promocodes p ON pu.promocode = p.code
            WHERE pu.user_id = ?
            ORDER BY pu.used_date DESC
            LIMIT ?
        """, (user_id, limit))
        return self.cursor.fetchall()

    def get_promocode_users(self, code, limit=20):
        """Получить список пользователей, использовавших промокод"""
        self.cursor.execute("""
            SELECT pu.user_id, u.username, pu.used_date
            FROM promocode_usage pu
            LEFT JOIN users u ON pu.user_id = u.user_id
            WHERE pu.promocode = ?
            ORDER BY pu.used_date DESC
            LIMIT ?
        """, (code, limit))
        return self.cursor.fetchall()

    def get_all_promocodes(self):
        """Получение всех промокодов"""
        self.cursor.execute("""
            SELECT code, amount, used_count, use_limit, valid_until, created_by, created_date 
            FROM promocodes 
            ORDER BY created_date DESC
        """)
        return self.cursor.fetchall()

    def delete_promocode(self, code):
        """Удаление промокода"""
        # Сначала удаляем записи об использовании промокода
        self.cursor.execute(
            "DELETE FROM promocode_usage WHERE promocode = ?",
            (code,)
        )
        # Затем удаляем сам промокод
        self.cursor.execute(
            "DELETE FROM promocodes WHERE code = ?",
            (code,)
        )
        self.conn.commit()
        return self.cursor.rowcount > 0

    # ========== Аккаунты ==========
    def add_account(self, email, password, games, added_by):
        """Добавление аккаунта"""
        self.cursor.execute(
            "INSERT INTO accounts (email, password, games, added_by) VALUES (?, ?, ?, ?)",
            (email, password, games, added_by)
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def get_random_account(self, games=None):
        """Получение случайного аккаунта"""
        if games:
            self.cursor.execute(
                "SELECT id, email, password, games FROM accounts WHERE games LIKE ? ORDER BY RANDOM() LIMIT 1",
                (f'%{games}%',)
            )
        else:
            self.cursor.execute(
                "SELECT id, email, password, games FROM accounts ORDER BY RANDOM() LIMIT 1"
            )
        return self.cursor.fetchone()

    def get_account(self, account_id):
        """Получение аккаунта по ID"""
        self.cursor.execute(
            "SELECT email, password, games FROM accounts WHERE id = ?",
            (account_id,)
        )
        return self.cursor.fetchone()

    def get_all_accounts(self, limit=50):
        """Получение всех аккаунтов"""
        self.cursor.execute(
            "SELECT id, email, games FROM accounts ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        return self.cursor.fetchall()

    def delete_account(self, account_id):
        """Удаление аккаунта"""
        self.cursor.execute(
            "DELETE FROM accounts WHERE id = ?",
            (account_id,)
        )
        self.conn.commit()
        return self.cursor.rowcount > 0

    # ========== Покупки ==========
    def add_purchase(self, user_id, games, price, account_id, account_data):
        """Добавление покупки"""
        self.cursor.execute(
            "INSERT INTO purchases (user_id, games, price, account_id, account_data) VALUES (?, ?, ?, ?, ?)",
            (user_id, games, price, account_id, account_data)
        )
        self.conn.commit()

    def get_recent_purchases(self, limit=10):
        """Получение последних покупок"""
        self.cursor.execute("""
            SELECT p.id, u.username, p.games, a.email, p.price, p.purchase_date, p.account_data
            FROM purchases p
            JOIN users u ON p.user_id = u.user_id
            LEFT JOIN accounts a ON p.account_id = a.id
            WHERE p.status = 'completed'
            ORDER BY p.purchase_date DESC
            LIMIT ?
        """, (limit,))
        return self.cursor.fetchall()

    # ========== Логи ==========
    def add_log(self, user_id, action, details=""):
        """Добавление лога"""
        self.cursor.execute(
            "INSERT INTO logs (user_id, action, details) VALUES (?, ?, ?)",
            (user_id, action, details)
        )
        self.conn.commit()

    def get_recent_logs(self, limit=15):
        """Получение последних логов"""
        self.cursor.execute("""
            SELECT l.action, l.details, u.username, u.user_id, l.log_date 
            FROM logs l
            LEFT JOIN users u ON l.user_id = u.user_id
            ORDER BY l.log_date DESC
            LIMIT ?
        """, (limit,))
        return self.cursor.fetchall()

    # ========== Статистика ==========
    def get_statistics(self):
        """Получение статистики"""
        stats = {}

        # Всего пользователей
        self.cursor.execute("SELECT COUNT(*) FROM users")
        stats['total_users'] = self.cursor.fetchone()[0]

        # Всего покупок
        self.cursor.execute("SELECT COUNT(*) FROM purchases WHERE status = 'completed'")
        stats['total_purchases'] = self.cursor.fetchone()[0]

        # Общая выручка
        self.cursor.execute("SELECT SUM(price) FROM purchases WHERE status = 'completed'")
        stats['total_revenue'] = self.cursor.fetchone()[0] or 0

        # Количество админов
        self.cursor.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1")
        stats['total_admins'] = self.cursor.fetchone()[0]

        # Всего аккаунтов
        self.cursor.execute("SELECT COUNT(*) FROM accounts")
        stats['total_accounts'] = self.cursor.fetchone()[0]

        # Всего промокодов
        self.cursor.execute("SELECT COUNT(*) FROM promocodes")
        stats['total_promocodes'] = self.cursor.fetchone()[0]

        # Активных промокодов
        self.cursor.execute("""
            SELECT COUNT(*) FROM promocodes 
            WHERE (use_limit <= 0 OR used_count < use_limit) 
            AND (valid_until IS NULL OR valid_until > datetime('now'))
        """)
        stats['active_promocodes'] = self.cursor.fetchone()[0]

        # Всего активаций промокодов
        self.cursor.execute("SELECT SUM(used_count) FROM promocodes")
        stats['total_promo_activations'] = self.cursor.fetchone()[0] or 0

        return stats

    def get_admins(self):
        """Получение всех админов"""
        self.cursor.execute("SELECT user_id, username FROM users WHERE is_admin = 1")
        return self.cursor.fetchall()

    def close(self):
        """Закрытие соединения с базой данных"""
        self.conn.close()