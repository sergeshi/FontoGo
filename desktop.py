#!/usr/bin/env python3
"""Native Qt desktop shell for FontoGo with SVG clipboard and context menus."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QUrl, Qt, Slot
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QApplication, QMainWindow, QMenu, QMessageBox
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel

ROOT = Path(__file__).resolve().parent


class Bridge:
    """Small, explicit bridge from the native clipboard to the web editor."""
    def __init__(self, window: "FontoGoWindow"):
        self.window = window

    @Slot()
    def pasteVector(self):
        self.window.paste_vector()


class FontoGoPage(QWebEnginePage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.window = None

    def createStandardContextMenu(self):
        menu = QMenu(self.view())
        window = self.window
        if window is None:
            return menu
        for label, callback, shortcut in [
            ("Вставить вектор из буфера", window.paste_vector, QKeySequence.Paste),
            ("Копировать текст", lambda: self.triggerAction(QWebEnginePage.WebAction.Copy), QKeySequence.Copy),
            ("Выделить всё", lambda: self.triggerAction(QWebEnginePage.WebAction.SelectAll), QKeySequence.SelectAll),
        ]:
            action = QAction(label, menu)
            action.setShortcut(shortcut)
            action.triggered.connect(callback)
            menu.addAction(action)
        menu.addSeparator()
        reload_action = QAction("Перезагрузить интерфейс", menu)
        reload_action.triggered.connect(self.window.reload_app)
        menu.addAction(reload_action)
        return menu


class FontoGoWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FontoGo — Font Studio")
        self.resize(1440, 920)
        self.view = QWebEngineView(self)
        self.page = FontoGoPage(self.view)
        self.page.window = self
        self.view.setPage(self.page)
        self.setCentralWidget(self.view)
        self.bridge = Bridge(self)
        self.channel = QWebChannel(self.page)
        self.channel.registerObject("fontogoBridge", self.bridge)
        self.page.setWebChannel(self.channel)
        self.view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self.show_context_menu)
        self.view.loadFinished.connect(self._install_bridge)
        self.view.load(QUrl.fromLocalFile(str(ROOT / "index.html")))
        self._add_native_actions()

    def _add_native_actions(self):
        paste = QAction("Вставить вектор", self)
        paste.setShortcut(QKeySequence.Paste)
        paste.triggered.connect(self.paste_vector)
        self.addAction(paste)
        reload_action = QAction("Перезагрузить", self)
        reload_action.setShortcut(QKeySequence.Refresh)
        reload_action.triggered.connect(self.reload_app)
        self.addAction(reload_action)

    @Slot()
    def _install_bridge(self, ok=True):
        # QWebChannel is available to the page; the clipboard action itself stays native.
        self.page.runJavaScript(
            "window.fontogoDesktop = { pasteVector: function(){"
            "if (window.qt && window.QWebChannel) {"
            "new QWebChannel(qt.webChannelTransport, function(c){"
            "c.objects.fontogoBridge.pasteVector();});}}};"
        )

    @Slot()
    def paste_vector(self):
        clipboard = QApplication.clipboard()
        mime = clipboard.mimeData()
        candidates = []
        if mime.hasFormat("image/svg+xml"):
            candidates.append(bytes(mime.data("image/svg+xml")).decode("utf-8", "replace"))
        if mime.hasText():
            candidates.append(mime.text())
        for candidate in candidates:
            if "<svg" in candidate.lower():
                import json
                self.page.runJavaScript("window.fontogoPasteVector(" + json.dumps(candidate) + ");")
                return
        QMessageBox.information(
            self, "Вставка вектора",
            "В буфере обмена не найден SVG. В Illustrator или Inkscape скопируйте векторный объект; "
            "если приложение предлагает выбор формата, используйте SVG или векторный текст. "
            "Обычный растровый скриншот нельзя превратить в контур этой командой."
        )

    def show_context_menu(self, position):
        menu = self.page.createStandardContextMenu()
        menu.exec(self.view.mapToGlobal(position))

    @Slot()
    def reload_app(self):
        self.view.reload()


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("FontoGo")
    window = FontoGoWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
