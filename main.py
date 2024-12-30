import sys
import json
import asyncio
import aiohttp
import aiofiles
import random
import string
import os
from typing import List, Optional
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QLabel, QTextEdit, 
                           QListWidget, QListWidgetItem, QSplitter, QToolTip,
                           QMessageBox, QDialog)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QPoint, QRect, QMetaObject, QUrl, QSize
from PyQt6.QtGui import QClipboard, QIcon
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEngineSettings
from pathlib import Path
from win10toast import ToastNotifier
from winotify import Notification, audio
import threading
from datetime import datetime
import shutil
import requests
import re
import webbrowser

API = 'https://www.1secmail.com/api/v1/'
domain_list = [
    "1secmail.com", "1secmail.org", "1secmail.net",
    "wwjmp.com", "esiix.com", "xojxe.com", "yoggm.com"
]

# Изменяем структуру папок
BASE_FOLDER = Path.home() / "Documents" / "TempMail"
SETTINGS_FOLDER = BASE_FOLDER / "TempMailSettings"
MAIL_FOLDER = BASE_FOLDER / "TempMailMessages"

# Добавим функцию для получения пути к ресурсам
def resource_path(relative_path):
    """Получает абсолютный путь к ресурсу"""
    try:
        # PyInstaller создает временную папку и хранит путь в _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

class AsyncHelper(QObject):
    finished = pyqtSignal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self.thread.start()
    
    def _run_event_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()
    
    def run_async(self, coro):
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return future

class TempMailApp(QMainWindow):
    def __init__(self):
        super().__init__()
        # Оптимизация веб-движка
        self.setup_web_engine()
        
        # Кэш для уже загруженных сообщений
        self.message_cache = {}
        
        # Определяем welcome_html как атрибут класса
        self.welcome_html = '''
        <html>
        <head>
            <style>
                body {
                    font-family: 'Segoe UI', Arial, sans-serif;
                    background-color: #1e1e1e;
                    color: #ffffff;
                    margin: 0;
                    padding: 40px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    min-height: calc(100vh - 80px);
                }
                .welcome-container {
                    text-align: center;
                    max-width: 800px;
                }
                .icon-container {
                    margin-bottom: 35px;
                }
                .icon-container img {
                    width: 90px;
                    height: 90px;
                    filter: drop-shadow(0 0 15px rgba(0, 120, 215, 0.3));
                }
                h2 {
                    color: #ffffff;
                    font-size: 26px;
                    font-weight: 400;
                    margin: 0 0 15px 0;
                }
                .subtitle {
                    color: #a0a0a0;
                    font-size: 15px;
                    margin-bottom: 40px;
                    line-height: 1.5;
                }
                .features-grid {
                    display: grid;
                    grid-template-columns: repeat(3, 1fr);
                    gap: 20px;
                    margin-bottom: 30px;
                }
                .feature {
                    background-color: #252526;
                    padding: 25px 20px;
                    border-radius: 8px;
                    text-align: left;
                    display: flex;
                    align-items: flex-start;
                    border: 1px solid #333333;
                    transition: transform 0.2s, box-shadow 0.2s;
                }
                .feature:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
                }
                .feature img {
                    width: 32px;
                    height: 32px;
                    margin-right: 15px;
                    filter: drop-shadow(0 0 5px rgba(0, 120, 215, 0.2));
                }
                .feature-text {
                    flex: 1;
                }
                .feature-title {
                    color: #ffffff;
                    font-size: 15px;
                    margin-bottom: 6px;
                    font-weight: 500;
                }
                .feature-desc {
                    color: #a0a0a0;
                    font-size: 13px;
                    line-height: 1.4;
                }
                .guide {
                    background-color: #252526;
                    border: 1px solid #333333;
                    border-radius: 8px;
                    padding: 25px;
                    margin-top: 30px;
                    text-align: center;
                }
                .guide h3 {
                    color: #ffffff;
                    font-size: 16px;
                    margin: 0 0 20px 0;
                    text-align: center;
                }
                .guide ul {
                    margin: 0;
                    padding-left: 0;
                    color: #a0a0a0;
                    list-style-position: inside;
                    display: inline-block;
                    text-align: left;
                }
                .guide li {
                    margin-bottom: 10px;
                    font-size: 14px;
                    line-height: 1.5;
                }
                .guide li strong {
                    color: #0078d4;
                }
            </style>
        </head>
        <body>
            <div class="welcome-container">
                <div class="icon-container">
                    <img src="https://cdn-icons-png.flaticon.com/512/9293/9293648.png" alt="Email">
                </div>
                <h2>Добро пожаловать в Временную Почту</h2>
                <div class="subtitle">
                    Безопасный и удобный сервис для получения временных электронных писем
                </div>
                <div class="features-grid">
                    <div class="feature">
                        <img src="https://cdn-icons-png.flaticon.com/512/6195/6195699.png" alt="Security">
                        <div class="feature-text">
                            <div class="feature-title">Безопасность</div>
                            <div class="feature-desc">Защита основной почты от спама и нежелательных рассылок</div>
                        </div>
                    </div>
                    <div class="feature">
                        <img src="https://cdn-icons-png.flaticon.com/512/9473/9473778.png" alt="Speed">
                        <div class="feature-text">
                            <div class="feature-title">Быстрый доступ</div>
                            <div class="feature-desc">Мгновенное получение и просмотр писем</div>
                        </div>
                    </div>
                    <div class="feature">
                        <img src="https://cdn-icons-png.flaticon.com/512/8832/8832119.png" alt="Auto">
                        <div class="feature-text">
                            <div class="feature-title">Автообновление</div>
                            <div class="feature-desc">Автоматическая проверка новых писем каждые 7 секунд</div>
                        </div>
                    </div>
                </div>
                <div class="guide">
                    <h3>📝 Как пользоваться:</h3>
                    <ul>
                        <li>Нажмите кнопку <strong>Новый адрес</strong> для создания нового почтового ящика</li>
                        <li>Используйте кнопку <strong>📋</strong> чтобы скопировать адрес в буфер обмена</li>
                        <li>Кнопка <strong>Обновить</strong> принудительно проверяет наличие новых писем</li>
                        <li>Все входящие письма автоматически появляются в списке слева</li>
                        <li>Нажмите на письмо в списке, чтобы прочитать его содержимое</li>
                        <li>Все письма автоматически сохраняются на вашем компьютере</li>
                        <li>При получении новых писем появляются уведомления</li>
                    </ul>
                </div>
            </div>
        </body>
        </html>
        '''
        
        self.setWindowTitle("Временная Почта")
        self.setGeometry(100, 100, 1200, 800)
        # Устанавливаем минимальный размер окна
        self.setMinimumSize(1000, 600)
        
        # Устанавливаем флаги окна, разрешающие разворачивание
        self.setWindowFlags(
            Qt.WindowType.Window |  # Обычное окно
            Qt.WindowType.WindowMinimizeButtonHint |  # Кнопка сворачивания
            Qt.WindowType.WindowMaximizeButtonHint |  # Кнопка разворачивания
            Qt.WindowType.WindowCloseButtonHint  # Кнопка закрытия
        )
        
        # Устанавливаем иконку приложения
        icon = QIcon(resource_path("appicon.png"))
        self.setWindowIcon(icon)
        QApplication.setWindowIcon(icon)
        
        # Инициализация переменных
        self.current_mail = ""
        self.session = None
        self.async_helper = AsyncHelper(self)
        
        # Обновляем пути к папкам
        self.base_folder = BASE_FOLDER
        self.settings_path = SETTINGS_FOLDER
        self.settings_file = self.settings_path / "settings.json"
        self.mail_folder = MAIL_FOLDER
        
        self.last_message_count = 0
        self.is_windows = sys.platform.startswith('win')
        
        # Определяем, работаем ли мы в Windows
        self.is_windows = sys.platform.startswith('win')
        
        # Получаем абсолютный путь к иконке
        self.icon_path = resource_path("appicon.png")  # Возвращаем .png
        
        # Создание структуры папок
        self.create_folder_structure()
        
        # Остальная инициализация...
        self.init_ui()
        self.async_helper.run_async(self.init_session())
        self.load_settings()
        self.check_mail()
        
        # Запуск таймера
        self.check_timer = QTimer()
        self.check_timer.timeout.connect(self.auto_check_mail)
        self.check_timer.start(7000)  # Изменяем на 7 секунд
        self.last_message_count = 0  # Для отслеживания новых писем

    def create_folder_structure(self):
        """Создает необходимую структуру папок"""
        try:
            # Создаем основную папку
            self.base_folder.mkdir(parents=True, exist_ok=True)
            
            # Создаем подпапки
            self.settings_path.mkdir(parents=True, exist_ok=True)
            self.mail_folder.mkdir(parents=True, exist_ok=True)
            
            print("Структура папок создана успешно")
        except Exception as e:
            print(f"Ошибка при создании структуры папок: {e}")

    def init_ui(self):
        # Обновляем стили, добавляем стиль для писем в списке
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
                font-size: 13px;
            }
            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                color: #ffffff;
                padding: 8px 15px;
                border-radius: 4px;
                font-size: 13px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
                border: 1px solid #4d4d4d;
            }
            QPushButton:pressed {
                background-color: #4d4d4d;
            }
            QListWidget {
                background-color: #252526;
                border: none;
                border-radius: 4px;
                color: #ffffff;
                font-size: 13px;
                padding: 5px;
                outline: none;
            }
            QListWidget::item {
                padding: 10px;
                margin: 3px 5px;
                border-radius: 6px;
                background-color: #2a2a2a;
                border-left: 3px solid transparent;
            }
            QListWidget::item:selected {
                background-color: #323232;
                color: #ffffff;
                border-left: 3px solid #0078d4;
                padding-left: 7px;
            }
            QListWidget::item:hover:!selected {
                background-color: #2d2d2d;
                border-left: 3px solid #404040;
            }
            QListWidget::item:selected:hover {
                background-color: #383838;
                border-left: 3px solid #0078d4;
            }
            QListWidget:focus {
                outline: none;
            }
            QSplitter::handle {
                background-color: #2d2d2d;
                margin: 1px;
            }
            QToolTip {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 5px;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Верхняя панель
        top_widget = QWidget()
        top_widget.setFixedHeight(50)  # Уменьшаем высоту
        top_widget.setStyleSheet("""
            QWidget {
                background-color: #252526;
                border-radius: 6px;
            }
        """)
        
        top_panel = QHBoxLayout(top_widget)
        top_panel.setContentsMargins(10, 0, 10, 0)  # Уменьшаем вертикальные отступы
        top_panel.setSpacing(10)
        
        # Контейнер для адреса
        address_container = QWidget()
        address_layout = QHBoxLayout(address_container)
        address_layout.setContentsMargins(0, 0, 0, 0)
        address_layout.setSpacing(8)
        
        self.mail_label = QLabel("Текущий адрес:")
        self.mail_label.setStyleSheet("""
            QLabel {
                color: #a0a0a0;
                font-size: 12px;
            }
        """)
        
        self.mail_address = QLabel("")
        # Стили для кнопок (добавим в начало метода init_ui)
        button_height = "32px"  # Общая высота для всех элементов
        
        self.mail_address.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 13px;
                font-family: 'Consolas', monospace;
                padding: 0 10px;  /* Уменьшаем вертикальные отступы */
                background-color: #252526;
                border-radius: 4px;
                border: 1px solid #3d3d3d;
                min-height: %s;  /* Фиксированная высота */
                max-height: %s;  /* Фиксированная высота */
                line-height: %s;  /* Центрирование текста по вертикали */
            }
        """ % (button_height, button_height, button_height))
        
        self.copy_btn = QPushButton()
        self.copy_btn.setToolTip("Копировать адрес")
        self.copy_btn.setFixedSize(32, 32)
        self.copy_btn.setIcon(QIcon(resource_path("icon-copy.png")))
        self.copy_btn.setIconSize(QSize(18, 18))
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
                border: 1px solid #4d4d4d;
            }
            QPushButton:pressed {
                background-color: #1e1e1e;
                padding: 7px 5px 5px 7px;
            }
        """)
        
        address_layout.addWidget(self.mail_label)
        address_layout.addWidget(self.mail_address, 1)  # Растягиваем адрес
        address_layout.addWidget(self.copy_btn)
        
        # Кнопки управления
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(8)
        
        self.new_mail_btn = QPushButton("Новый адрес")
        self.refresh_btn = QPushButton("Обновить")
        
        for btn in [self.new_mail_btn, self.refresh_btn]:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    border: 1px solid #3d3d3d;
                    padding: 6px 12px;
                    border-radius: 4px;
                    font-size: 12px;
                    min-width: 90px;
                }
                QPushButton:hover {
                    background-color: #3d3d3d;
                    border: 1px solid #4d4d4d;
                }
                QPushButton:pressed {
                    background-color: #1e1e1e;
                }
            """)
        
        button_layout.addWidget(self.new_mail_btn)
        button_layout.addWidget(self.refresh_btn)
        
        about_btn = QPushButton()
        about_btn.setToolTip("О программе")
        about_btn.setFixedSize(32, 32)
        about_btn.setIcon(QIcon(resource_path("suicon.png")))
        about_btn.setIconSize(QSize(18, 18))
        about_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
                border: 1px solid #4d4d4d;
            }
            QPushButton:pressed {
                background-color: #1e1e1e;
                padding: 7px 5px 5px 7px;
            }
        """)
        about_btn.clicked.connect(self.show_about)
        button_layout.addWidget(about_btn)
        
        # Добавляем все в верхнюю панель
        top_panel.addWidget(address_container, 7)
        top_panel.addWidget(button_container, 3)
        
        # Добавляем верхнюю панель в основной layout
        layout.addWidget(top_widget)
        
        # Основной контейнер для списка писем и просмотра
        main_container = QWidget()
        main_layout = QVBoxLayout(main_container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Сплиттер и список писем
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("""
            QSplitter::handle {
                width: 1px;  /* Тонкая линия */
                background-color: #3d3d3d;  /* Цвет линии */
            }
        """)
        
        # Левая панель с письмами
        mail_container = QWidget()
        mail_container.setStyleSheet("""
            QWidget {
                background-color: transparent;  /* Убираем фон контейнера */
                border: none;  /* Убираем рамку */
            }
        """)
        mail_layout = QVBoxLayout(mail_container)
        mail_layout.setContentsMargins(0, 0, 0, 0)
        mail_layout.setSpacing(10)
        
        mail_header = QLabel("📥 Входящие сообщения")
        mail_header.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #ffffff;
                padding: 5px 0;
            }
        """)
        
        self.mail_list = QListWidget()
        self.mail_list.setFixedWidth(350)  # Фиксированная ширина
        
        mail_layout.addWidget(mail_header)
        mail_layout.addWidget(self.mail_list)
        
        # Правая панель с просмотром письма
        view_container = QWidget()
        view_container.setStyleSheet("""
            QWidget {
                background-color: #252526;
                border-radius: 4px;
                padding: 10px;
            }
        """)
        view_layout = QVBoxLayout(view_container)
        view_layout.setContentsMargins(0, 0, 0, 0)
        
        self.web_view = QWebEngineView()
        self.web_view.setMinimumWidth(500)
        
        # Начальное содержимое веб-представления
        self.web_view.setHtml(self.welcome_html, QUrl())
        
        view_layout.addWidget(self.web_view)
        
        # Добавляем виджеты в сплиттер
        splitter.addWidget(mail_container)
        splitter.addWidget(view_container)
        
        # Блокируем возможность изменения размера
        splitter.setCollapsible(0, False)  # Блокируем левую панель
        splitter.setCollapsible(1, False)  # Блокируем правую панель
        splitter.handle(1).setEnabled(False)  # Отключаем handle сплиттера
        
        # Устанавливаем начальные размеры сплиттера (30% : 70%)
        splitter.setSizes([300, 700])
        
        main_layout.addWidget(splitter)
        
        # Добавляем виджеты в главный layout
        layout.addWidget(main_container, stretch=1)  # Растягиваем основной контейнер
        
        # Подключение сигналов
        self.new_mail_btn.clicked.connect(self.create_new_mail)
        self.refresh_btn.clicked.connect(self.check_mail)
        self.mail_list.itemClicked.connect(self.show_message)
        self.copy_btn.clicked.connect(self.copy_address_to_clipboard)

        # Обновляем настройки для mail_list и web_view
        self.mail_list.setMinimumWidth(300)
        self.mail_list.setMaximumWidth(500)
        self.web_view.setMinimumWidth(400)
        
        # Настраиваем существующий сплиттер
        splitter.setChildrenCollapsible(False)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        splitter.handle(1).setEnabled(True)
        
        # Устанавливаем пропорции
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        # Устанавливаем начальные размеры (30% : 70%)
        total_width = self.width()
        splitter.setSizes([int(total_width * 0.3), int(total_width * 0.7)])

    def show_about(self):
        about_html = '''
            <html>
            <body style="
                background-color: #1e1e1e;
                color: #ffffff;
                font-family: 'Segoe UI', Arial, sans-serif;
                margin: 0;
                padding: 20px;
            ">
                <div style="
                    background-color: #252526;
                    border-radius: 6px;  /* Уменьшаем закругление */
                    padding: 25px;
                    text-align: center;
                    border: 1px solid #3d3d3d;
                ">
                    <h2 style="margin-top: 0; color: #ffffff;">О программе</h2>
                    <p style="color: #e0e0e0; line-height: 1.6;">
                        Временная Почта - это удобный инструмент для создания временных email-адресов.
                        Программа помогает защитить вашу основную почту от спама и нежелательных рассылок.
                    </p>
                    <div style="margin: 25px 0;">
                        <h3 style="color: #ffffff;">Основные возможности:</h3>
                        <ul style="
                            text-align: left;
                            color: #e0e0e0;
                            line-height: 1.6;
                            list-style-type: none;
                            padding: 0;
                        ">
                            <li>✓ Мгновенное создание временного адреса</li>
                            <li>✓ Автоматическое обновление входящих писем</li>
                            <li>✓ Уведомления о новых сообщениях</li>
                            <li>✓ Сохранение писем на компьютере</li>
                        </ul>
                    </div>
                    <div style="
                        background-color: #2d2d2d;
                        border-radius: 8px;
                        padding: 20px;
                        margin-top: 20px;
                        border: 1px solid #3d3d3d;
                    ">
                        <p style="margin: 0 0 15px 0; color: #e0e0e0;">
                            Есть вопросы или предложения?<br>
                            Свяжитесь с разработчиком:
                        </p>
                        <a href="https://t.me/elijah_5456" style="
                            display: inline-block;
                            background-color: #0088cc;
                            color: white;
                            text-decoration: none;
                            padding: 10px 20px;
                            border-radius: 5px;
                            font-weight: 500;
                        ">
                            Telegram
                        </a>
                    </div>
                </div>
            </body>
            </html>
        '''
        
        dialog = QDialog(self)
        dialog.setWindowTitle("О программе")
        dialog.setFixedSize(400, 500)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)
        
        web_view = QWebEngineView()
        web_view.setHtml(about_html)
        
        layout.addWidget(web_view)
        dialog.exec()

    async def init_session(self):
        try:
            if self.session is None or self.session.closed:
                self.session = aiohttp.ClientSession()
        except Exception as e:
            print(f"Ошибка инициализации сессии: {e}")
            self.session = aiohttp.ClientSession()

    def load_settings(self):
        try:
            self.settings_path.mkdir(parents=True, exist_ok=True)
            if self.settings_file.exists():
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                    loaded_mail = settings.get('current_mail', '')
                    if loaded_mail:
                        self.current_mail = loaded_mail
                        self.mail_address.setText(self.current_mail)
                        # Проверяем существование папки для текущей почты
                        mail_folder = self.mail_folder / self.current_mail
                        if not mail_folder.exists():
                            mail_folder.mkdir(parents=True, exist_ok=True)
                        # Загружаем сохраненные письма
                        self.load_saved_messages()
                    else:
                        # Если адрес пустой, создаем новый
                        self.create_new_mail()
            else:
                # Если файла нет, создаем новый адрес
                self.create_new_mail()
        except Exception as e:
            print(f"Ошибка загрузки настроек: {e}")
            # В случае ошибки создаем новый адрес
            self.create_new_mail()

    def save_settings(self):
        try:
            # Создаем временный файл
            temp_file = self.settings_file.with_suffix('.tmp')
            settings = {
                'current_mail': self.current_mail
            }
            
            # Сначала записываем во временный файл
            with open(temp_file, 'w') as f:
                json.dump(settings, f)
                
            # Затем безопасно заменяем основной файл
            if temp_file.exists():
                temp_file.replace(self.settings_file)
                
        except Exception as e:
            print(f"Ошибка сохранения настроек: {e}")
            # В случае ошибки пытаемся восстановить из бэкапа
            if self.settings_file.exists():
                self.load_settings()

    def create_new_mail(self):
        try:
            # Создаем и настраиваем диалог подтверждения
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle('Подтверждение')
            msg_box.setText('Создать новый почтовый адрес?\n\nВнимание: все сообщения текущего адреса будут удалены!')
            msg_box.setIcon(QMessageBox.Icon.Question)
            
            # Создаем кнопки на русском
            yes_button = msg_box.addButton('Да', QMessageBox.ButtonRole.YesRole)
            no_button = msg_box.addButton('Нет', QMessageBox.ButtonRole.NoRole)
            msg_box.setDefaultButton(no_button)  # Нет - кнопка по умолчанию
            
            # Показываем диалог
            msg_box.exec()
            
            # Проверяем, какая кнопка была нажата
            if msg_box.clickedButton() == yes_button:
                url = f'{API}?action=genRandomMailbox&count=1'
                response = requests.get(url)
                
                if response.status_code == 200:
                    email = response.json()
                    if email and isinstance(email, list) and len(email) > 0:
                        new_mail = email[0]
                        
                        # Сначала удаляем старую папку, если есть
                        if self.current_mail:
                            old_folder = self.mail_folder / self.current_mail
                            if old_folder.exists():
                                shutil.rmtree(old_folder)
                                print(f"Удалена папка старой почты: {self.current_mail}")
                        
                        # Сохраняем новый адрес
                        self.current_mail = new_mail
                        self.save_settings()
                        
                        # Обновляем интерфейс
                        self.update_mail_address(self.current_mail)
                        self.clear_mail_list()
                        self.clear_web_view()
                        
                        # Отображаем приветственный экран
                        self.web_view.setHtml(self.welcome_html, QUrl())
                        
                        # Создаем новую папку
                        new_folder = self.mail_folder / new_mail
                        new_folder.mkdir(parents=True, exist_ok=True)
                        
                        # Запускаем проверку почты
                        self.check_mail()
                        
                        # Показываем уведомление об успехе
                        success_box = QMessageBox(self)
                        success_box.setWindowTitle('Успех')
                        success_box.setText(f'Создан новый адрес: {new_mail}')
                        success_box.setIcon(QMessageBox.Icon.Information)
                        success_box.addButton('ОК', QMessageBox.ButtonRole.AcceptRole)
                        success_box.exec()
                    
        except Exception as e:
            print(f"Ошибка создания нового адреса: {e}")
            error_box = QMessageBox(self)
            error_box.setWindowTitle('Ошибка')
            error_box.setText(f'Не удалось создать новый адрес: {str(e)}')
            error_box.setIcon(QMessageBox.Icon.Critical)
            error_box.addButton('ОК', QMessageBox.ButtonRole.AcceptRole)
            error_box.exec()
            # В случае ошибки восстанавливаем старый адрес
            self.load_settings()

    async def _check_mail_async(self):
        try:
            if not self.current_mail:
                return
            
            # Получаем список уже добавленных писем
            existing_messages = set()
            for index in range(self.mail_list.count()):
                item = self.mail_list.item(index)
                msg_id = item.data(Qt.ItemDataRole.UserRole)
                existing_messages.add(msg_id)
            
            # Получаем письма с сервера
            login, domain = self.current_mail.split("@")
            url = f'{API}?action=getMessages&login={login}&domain={domain}'
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        messages = await response.json()
                        
                        # Проверяем новые письма
                        new_messages = []
                        for msg in messages:
                            if msg['id'] not in existing_messages:
                                new_messages.append(msg)
                        
                        # Показываем уведомление только если есть новые письма и это не первый запуск
                        if new_messages and self.last_message_count > 0:
                            self.show_notification(len(new_messages))
                        
                        # Обновляем список только если есть изменения
                        if new_messages:
                            # Сохраняем текущую позицию прокрутки
                            current_row = self.mail_list.currentRow()
                            
                            # Добавляем новые письма в начало списка
                            for msg in reversed(new_messages):
                                date = msg.get('date', '').split(' ')[0]
                                subject = msg.get('subject', '(Без темы)')
                                sender = msg.get('from', 'Unknown')
                                
                                if len(subject) > 30:
                                    subject = subject[:30] + "..."
                                if len(sender) > 30:
                                    sender = sender[:30] + "..."
                                
                                item_text = f"От: {sender}\nТема: {subject}\nДата: {date}"
                                
                                # Добавляем новое письмо в начало списка
                                item = QListWidgetItem(item_text)
                                item.setData(Qt.ItemDataRole.UserRole, msg['id'])
                                self.mail_list.insertItem(0, item)
                            
                            # Восстанавливаем выбранный элемент
                            if current_row >= 0:
                                self.mail_list.setCurrentRow(current_row + len(new_messages))
                        
                        self.last_message_count = len(messages)
                        
            QApplication.processEvents()
                    
        except Exception as e:
            print(f"Ошибка при асинхронной проверке почты: {e}")

    def auto_check_mail(self):
        asyncio.run_coroutine_threadsafe(self._check_mail_async(), self.async_helper.loop)

    def show_notification(self, count: int):
        """Показывает уведомление о новых письмах"""
        try:
            if self.is_windows:
                title = "Временная Почта"
                msg = f"Получено {count} новых {'письмо' if count == 1 else 'письма' if 1 < count < 5 else 'писем'}"
                
                # Используем PNG файл вместо ICO
                icon_path = os.path.abspath("appicon.png")
                
                # Создаем уведомление
                toast = Notification(
                    app_id="Временная Почта",
                    title=title,
                    msg=msg,
                    icon=icon_path,
                    duration="short"
                )
                
                # Добавляем звук уведомления
                toast.set_audio(audio.Mail, loop=False)
                
                # Показываем уведомление
                toast.show()
                
        except Exception as e:
            print(f"Ошибка отправки уведомления: {e}")

    def check_mail(self):
        """Метод для ручной проверки почты"""
        self.auto_check_mail()  # Используем тот же метод для обновления

    def add_mail_item(self, text, msg_id):
        """Добавляет элемент в список писем с предварительной загрузкой"""
        item = QListWidgetItem(text)
        item.setData(Qt.ItemDataRole.UserRole, msg_id)
        self.mail_list.addItem(item)
        
        # Запускаем предварительную загрузку в фоновом режиме
        if self.mail_list.count() == 1:  # Если это первое письмо
            threading.Thread(target=lambda: self.preload_message(msg_id), daemon=True).start()

    def show_message(self, item):
        if not item:
            return
            
        try:
            msg_id = item.data(Qt.ItemDataRole.UserRole)
            
            self.web_view.setHtml("")
            QApplication.processEvents()

            # Сначала получаем письмо с сервера и сохраняем его
            if isinstance(msg_id, int):  # Если это новое письмо с сервера
                msg_data = self.get_message_from_server(msg_id)
                if msg_data:
                    # Сохраняем письмо и получаем имя файла
                    filename = self.save_message(msg_data)
                    if filename:
                        msg_id = filename  # Теперь будем использовать локальный файл
            
            # Теперь читаем сохраненное письмо
            if isinstance(msg_id, str):  # Читаем локальный файл
                msg_data = self.read_local_message(msg_id)
                if not msg_data:
                    return

            html_content = msg_data.get('htmlBody', '')
            text_content = msg_data.get('textBody', '')
            
            email_info = f'''
                <div style="
                    background: #f5f5f5;
                    padding: 15px 20px;
                    margin-bottom: 20px;
                    border-radius: 4px;
                ">
                    <p style="margin: 5px 0;"><b>От:</b> {msg_data.get('from', 'Unknown')}</p>
                    <p style="margin: 5px 0;"><b>Тема:</b> {msg_data.get('subject', '(Без темы)')}</p>
                    <p style="margin: 5px 0;"><b>Дата:</b> {msg_data.get('date', '')}</p>
                </div>
            '''

            if html_content:
                base_html = f'''
                    <html>
                    <head>
                        <meta charset="UTF-8">
                        <meta name="viewport" content="width=device-width, initial-scale=1.0">
                        <style>
                            body {{
                                margin: 0;
                                padding: 20px;
                                background: #fff;
                            }}
                            .email-info {{
                                font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                            }}
                            .email-content {{
                                img {{
                                    max-width: 100%;
                                    height: auto;
                                }}
                            }}
                        </style>
                    </head>
                    <body>
                        <div class="email-info">{email_info}</div>
                        <div class="email-content">{html_content}</div>
                    </body>
                    </html>
                '''
            else:
                base_html = f'''
                    <html>
                    <head>
                        <meta charset="UTF-8">
                        <meta name="viewport" content="width=device-width, initial-scale=1.0">
                        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500&display=swap" rel="stylesheet">
                        <style>
                            body {{
                                margin: 0;
                                padding: 20px 40px;
                                background: #fff;
                                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                                font-size: 16px;
                                line-height: 1.7;
                                color: #2c353d;
                                max-width: 800px;
                                margin: 0 auto;
                            }}
                            .text-content {{
                                letter-spacing: -0.003em;
                                font-weight: 400;
                            }}
                            .text-content p {{
                                margin: 1.2em 0;
                            }}
                            .text-content a {{
                                color: #0066cc;
                                text-decoration: none;
                            }}
                            .text-content a:hover {{
                                text-decoration: underline;
                            }}
                        </style>
                    </head>
                    <body>
                        {email_info}
                        <div class="text-content">{text_content.replace(chr(10), '<br>')}</div>
                    </body>
                    </html>
                '''

            settings = self.web_view.settings()
            settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, True)
            
            base_url = QUrl.fromLocalFile(os.path.abspath("."))
            self.web_view.setHtml(base_html, base_url)
                
        except Exception as e:
            print(f"Ошибка при отображении сообщения: {e}")
            self.web_view.setHtml(f'<div style="color:red">Ошибка: {str(e)}</div>')

    def get_message_from_server(self, msg_id: int) -> dict:
        """Получение сообщения с сервера"""
        try:
            future = asyncio.run_coroutine_threadsafe(
                self._read_message_async(msg_id), 
                self.async_helper.loop
            )
            return future.result()
        except Exception as e:
            print(f"Ошибка получения сообщения с сервера: {e}")
            return None

    def read_local_message(self, filename: str) -> dict:
        """Чтение сообщения из локального файла"""
        try:
            mail_folder = self.mail_folder / self.current_mail
            file_path = mail_folder / f"{filename}.html"
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Извлекаем метаданные из имени файла
                    try:
                        date_str = filename.split('_')[0]
                        date = datetime.strptime(date_str, '%Y%m%d%H%M%S').strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        date = datetime.fromtimestamp(file_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                    
                    return {
                        'from': self.current_mail,
                        'subject': ' '.join(filename.split('_')[1:]),
                        'date': date,
                        'htmlBody': content
                    }
        except Exception as e:
            print(f"Ошибка чтения локального файла: {e}")
        return None

    def save_message(self, msg_data: dict) -> str:
        """Сохранение сообщения в файл и возврат имени файла"""
        try:
            if not self.current_mail or not msg_data:
                return None

            mail_folder = self.mail_folder / self.current_mail
            mail_folder.mkdir(parents=True, exist_ok=True)

            try:
                date_str = datetime.strptime(msg_data.get('date', ''), '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M%S')
            except ValueError:
                date_str = datetime.now().strftime('%Y%m%d%H%M%S')

            subject = msg_data.get('subject', 'no_subject')
            subject = "".join(c for c in subject if c.isalnum() or c in (' ', '-', '_'))[:50]
            filename = f"{date_str}_{subject}"
            
            file_path = mail_folder / f"{filename}.html"

            html_content = msg_data.get('htmlBody', '')
            text_content = msg_data.get('textBody', '')
            
            content = html_content if html_content else f'<pre style="white-space:pre-wrap">{text_content}</pre>'
            
            full_html = f'''
            <html>
            <head>
                <meta charset="UTF-8">
            </head>
            <body>
                {content}
            </body>
            </html>
            '''

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(full_html)

            return filename

        except Exception as e:
            print(f"Ошибка сохранения письма: {e}")
            return None

    # Добавляем метод для предварительной загрузки сообщений
    def preload_message(self, msg_id):
        """Предварительная загрузка сообщения"""
        try:
            if msg_id not in self.message_cache:
                if isinstance(msg_id, int):
                    msg_data = self.get_message_from_server(msg_id)
                else:
                    msg_data = self.read_local_message(msg_id)
                
                if msg_data:
                    self.message_cache[msg_id] = msg_data
        except Exception as e:
            print(f"Ошибка предзагрузки: {e}")

    def setup_web_engine(self):
        """Настройка оптимизации веб-движка"""
        profile = QWebEngineProfile.defaultProfile()
        settings = profile.settings()
        
        # Добавляем разрешения для загрузки контента
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.AutoLoadImages, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        
        # Настройки кэширования
        profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
        profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies)
        profile.setCachePath(str(Path.home() / "AppData" / "Local" / "TempMail" / "cache"))
        profile.setPersistentStoragePath(str(Path.home() / "AppData" / "Local" / "TempMail" / "storage"))

    def closeEvent(self, event):
        try:
            self.save_settings()
            self.check_timer.stop()
            if hasattr(self, 'toaster') and self.toaster:
                self.toaster = None  # Освобождаем уведомления
            if self.session and not self.session.closed:
                self.async_helper.run_async(self.session.close())
            event.accept()
        except Exception as e:
            print(f"Ошибка при закрытии приложения: {e}")
            event.accept()

    def copy_address_to_clipboard(self):
        if self.current_mail:
            clipboard = QApplication.clipboard()
            clipboard.setText(self.current_mail)
            
            # Показываем всплывающее уведомление
            QToolTip.showText(
                self.copy_btn.mapToGlobal(QPoint(0, self.copy_btn.height())),
                "Адрес скопирован!",
                self.copy_btn,
                QRect(),
                2000
            )

    async def create_mailbox(self, username: str, domain: str) -> bool:
        await self.init_session()
        url = f'{API}?action=genRandomMailbox&count=1'
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    return True
        except Exception as e:
            print(f"Ошибка создания почтового ящика: {e}")
        return False

    def update_mail_address(self, address):
        self.mail_address.setText(address)

    def clear_mail_list(self):
        self.mail_list.clear()

    def clear_web_view(self):
        self.web_view.setHtml(self.welcome_html, QUrl())

    async def safe_request(self, coro):
        try:
            return await coro
        except aiohttp.ClientError as e:
            print(f"Ошибка сети: {e}")
            return None
        except Exception as e:
            print(f"Неожиданная ошибка: {e}")
            return None

    async def _read_message_async(self, msg_id: int) -> dict:
        try:
            if not self.current_mail:
                return {}
            
            login, domain = self.current_mail.split("@")
            url = f'{API}?action=readMessage&login={login}&domain={domain}&id={msg_id}'
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
            return {}
            
        except Exception as e:
            print(f"Ошибка чтения сообщения: {e}")
            return {}

    def load_saved_messages(self):
        """Загружает сохраненные письма из папки"""
        try:
            if not self.current_mail:
                return
            
            mail_folder = self.mail_folder / self.current_mail
            if not mail_folder.exists():
                return
            
            # Получаем список всех .html файлов
            saved_messages = list(mail_folder.glob('*.html'))
            
            # Сортируем по дате создания (новые первыми)
            saved_messages.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            for msg_path in saved_messages:
                try:
                    # Получаем имя файла без расширения
                    msg_id = msg_path.stem
                    
                    # Читаем сообщение
                    msg_data = self.read_local_message(msg_id)
                    if msg_data:
                        date = msg_data.get('date', '')
                        subject = msg_data.get('subject', '(Без темы)')
                        sender = msg_data.get('from', 'Unknown')
                        
                        if len(subject) > 30:
                            subject = subject[:30] + "..."
                        if len(sender) > 30:
                            sender = sender[:30] + "..."
                        
                        item_text = f"От: {sender}\nТема: {subject}\nДата: {date}"
                        
                        item = QListWidgetItem(item_text)
                        item.setData(Qt.ItemDataRole.UserRole, msg_id)
                        self.mail_list.addItem(item)
                        
                except Exception as e:
                    print(f"Ошибка загрузки сообщения {msg_path}: {e}")
                
        except Exception as e:
            print(f"Ошибка загрузки сохраненных писем: {e}")

def main():
    app = QApplication(sys.argv)
    window = TempMailApp()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()