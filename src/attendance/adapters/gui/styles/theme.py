"""Paleta de colores y hojas de estilo (QSS) para la interfaz gráfica de AsistPy.

Colores base especificados por el usuario:
- Fondo Principal: #09091A
- Texto / Alto Contraste: #FFFFFF
- Acento / Acción Primaria: #276EF1
- Neutro / Secundario: #6B6B6B
"""

class Theme:
    # Colores directos del usuario
    BG_MAIN = "#09091A"
    TEXT_MAIN = "#FFFFFF"
    PRIMARY = "#276EF1"
    MUTED = "#6B6B6B"

    # Tonos complementarios calculados para jerarquía visual
    BG_CARD = "#121229"
    BG_CARD_HOVER = "#1A1A3A"
    BG_INPUT = "#0C0C22"
    BORDER = "#222245"
    BORDER_FOCUS = "#276EF1"

    PRIMARY_HOVER = "#3B7DF5"
    PRIMARY_PRESSED = "#1B55C2"

    TEXT_MUTED = "#8E8E9F"
    TEXT_DISABLED = "#4F4F63"

    # Colores semánticos de estado
    SUCCESS = "#10B981"
    SUCCESS_BG = "#063A27"
    WARNING = "#F59E0B"
    WARNING_BG = "#3D2702"
    DANGER = "#EF4444"
    DANGER_BG = "#3D0F12"
    INFO = "#276EF1"
    INFO_BG = "#0A2558"

    @classmethod
    def get_stylesheet(cls) -> str:
        """Retorna la hoja de estilos QSS completa optimizada para Qt 6."""
        return f"""
        /* Estilos Globales de Ventana y Widgets */
        QWidget {{
            background-color: {cls.BG_MAIN};
            color: {cls.TEXT_MAIN};
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            font-size: 13px;
        }}

        QMainWindow {{
            background-color: {cls.BG_MAIN};
        }}

        /* Scrollbars modernas y delgadas */
        QScrollBar:vertical {{
            border: none;
            background: {cls.BG_MAIN};
            width: 8px;
            margin: 0px;
        }}
        QScrollBar::handle:vertical {{
            background: {cls.MUTED};
            min-height: 24px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {cls.PRIMARY};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}

        QScrollBar:horizontal {{
            border: none;
            background: {cls.BG_MAIN};
            height: 8px;
            margin: 0px;
        }}
        QScrollBar::handle:horizontal {{
            background: {cls.MUTED};
            min-width: 24px;
            border-radius: 4px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {cls.PRIMARY};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}

        /* Botones Estándar y Primarios */
        QPushButton {{
            background-color: {cls.BG_CARD};
            color: {cls.TEXT_MAIN};
            border: 1px solid {cls.BORDER};
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: 500;
        }}
        QPushButton:hover {{
            background-color: {cls.BG_CARD_HOVER};
            border-color: {cls.PRIMARY};
        }}
        QPushButton:pressed {{
            background-color: {cls.PRIMARY_PRESSED};
            border-color: {cls.PRIMARY_PRESSED};
        }}
        QPushButton:disabled {{
            background-color: {cls.BG_MAIN};
            color: {cls.TEXT_DISABLED};
            border-color: {cls.BORDER};
        }}

        /* Botón Primario */
        QPushButton#primaryBtn {{
            background-color: {cls.PRIMARY};
            color: #FFFFFF;
            border: 1px solid {cls.PRIMARY};
            font-weight: 600;
        }}
        QPushButton#primaryBtn:hover {{
            background-color: {cls.PRIMARY_HOVER};
            border-color: {cls.PRIMARY_HOVER};
        }}
        QPushButton#primaryBtn:pressed {{
            background-color: {cls.PRIMARY_PRESSED};
            border-color: {cls.PRIMARY_PRESSED};
        }}

        /* Botón Peligro / Eliminar */
        QPushButton#dangerBtn {{
            background-color: {cls.DANGER_BG};
            color: #FFB4B4;
            border: 1px solid {cls.DANGER};
            font-weight: 600;
        }}
        QPushButton#dangerBtn:hover {{
            background-color: {cls.DANGER};
            color: #FFFFFF;
        }}

        /* Campos de Entrada de Texto */
        QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QDateEdit, QTimeEdit {{
            background-color: {cls.BG_INPUT};
            color: {cls.TEXT_MAIN};
            border: 1px solid {cls.BORDER};
            border-radius: 6px;
            padding: 8px 12px;
            selection-background-color: {cls.PRIMARY};
            selection-color: #FFFFFF;
        }}
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QDateEdit:focus {{
            border: 1px solid {cls.PRIMARY};
        }}
        QLineEdit:disabled {{
            color: {cls.TEXT_DISABLED};
            background-color: {cls.BG_MAIN};
        }}

        /* ComboBox / Selectores */
        QComboBox {{
            background-color: {cls.BG_INPUT};
            color: {cls.TEXT_MAIN};
            border: 1px solid {cls.BORDER};
            border-radius: 6px;
            padding: 7px 12px;
        }}
        QComboBox:focus {{
            border-color: {cls.PRIMARY};
        }}
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 28px;
            border-left-width: 0px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {cls.BG_CARD};
            color: {cls.TEXT_MAIN};
            border: 1px solid {cls.BORDER};
            selection-background-color: {cls.PRIMARY};
            selection-color: #FFFFFF;
            padding: 4px;
        }}

        /* Tablas de Datos (QTableWidget, QTableView) */
        QTableView, QTableWidget {{
            background-color: {cls.BG_CARD};
            color: {cls.TEXT_MAIN};
            border: 1px solid {cls.BORDER};
            border-radius: 8px;
            gridline-color: {cls.BORDER};
            selection-background-color: {cls.PRIMARY};
            selection-color: #FFFFFF;
            outline: none;
        }}
        QHeaderView::section {{
            background-color: {cls.BG_MAIN};
            color: {cls.TEXT_MUTED};
            padding: 10px 8px;
            border: none;
            border-bottom: 2px solid {cls.BORDER};
            font-weight: 600;
            font-size: 12px;
            text-transform: uppercase;
        }}
        QTableCornerButton::section {{
            background-color: {cls.BG_MAIN};
            border: none;
        }}

        /* Pestañas / TabBar */
        QTabWidget::pane {{
            border: 1px solid {cls.BORDER};
            border-radius: 8px;
            background-color: {cls.BG_CARD};
            padding: 8px;
        }}
        QTabBar::tab {{
            background-color: {cls.BG_MAIN};
            color: {cls.TEXT_MUTED};
            padding: 10px 20px;
            border: 1px solid {cls.BORDER};
            border-bottom: none;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            margin-right: 4px;
        }}
        QTabBar::tab:selected {{
            background-color: {cls.BG_CARD};
            color: {cls.PRIMARY};
            font-weight: bold;
            border-bottom: 2px solid {cls.PRIMARY};
        }}
        QTabBar::tab:hover:!selected {{
            color: {cls.TEXT_MAIN};
            background-color: {cls.BG_CARD_HOVER};
        }}

        /* Tarjetas y Contenedores */
        QFrame#cardFrame {{
            background-color: {cls.BG_CARD};
            border: 1px solid {cls.BORDER};
            border-radius: 8px;
            padding: 16px;
        }}

        /* Menú y Barra de Estado */
        QMenuBar {{
            background-color: {cls.BG_MAIN};
            color: {cls.TEXT_MAIN};
            border-bottom: 1px solid {cls.BORDER};
        }}
        QMenuBar::item:selected {{
            background-color: {cls.PRIMARY};
        }}
        QMenu {{
            background-color: {cls.BG_CARD};
            color: {cls.TEXT_MAIN};
            border: 1px solid {cls.BORDER};
        }}
        QMenu::item:selected {{
            background-color: {cls.PRIMARY};
            color: #FFFFFF;
        }}
        QStatusBar {{
            background-color: {cls.BG_MAIN};
            color: {cls.TEXT_MUTED};
            border-top: 1px solid {cls.BORDER};
        }}

        /* Etiquetas de Título y Subtítulo */
        QLabel#h1Title {{
            color: {cls.TEXT_MAIN};
            font-size: 20px;
            font-weight: 700;
        }}
        QLabel#h2Title {{
            color: {cls.TEXT_MAIN};
            font-size: 16px;
            font-weight: 600;
        }}
        QLabel#mutedLabel {{
            color: {cls.MUTED};
            font-size: 12px;
        }}
        QLabel#badgeSuccess {{
            background-color: {cls.SUCCESS_BG};
            color: {cls.SUCCESS};
            border: 1px solid {cls.SUCCESS};
            border-radius: 4px;
            padding: 3px 8px;
            font-weight: bold;
            font-size: 11px;
        }}
        QLabel#badgeWarning {{
            background-color: {cls.WARNING_BG};
            color: {cls.WARNING};
            border: 1px solid {cls.WARNING};
            border-radius: 4px;
            padding: 3px 8px;
            font-weight: bold;
            font-size: 11px;
        }}
        QLabel#badgeDanger {{
            background-color: {cls.DANGER_BG};
            color: {cls.DANGER};
            border: 1px solid {cls.DANGER};
            border-radius: 4px;
            padding: 3px 8px;
            font-weight: bold;
            font-size: 11px;
        }}
        """
