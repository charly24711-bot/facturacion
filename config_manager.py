from database import SessionLocal
import models

class ConfigManager:
    _instance = None
    _config = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance.load_config()
        return cls._instance

    def load_config(self):
        db = SessionLocal()
        settings = db.query(models.CompanySettings).first()
        if not settings:
            # Si no hay, crear una por defecto
            settings = models.CompanySettings(nombre="Mi Empresa")
            db.add(settings)
            db.commit()
            
        self._config = {
            "ui_show_multicurrency": getattr(settings, 'ui_show_multicurrency', True),
            "ui_show_price_channels": getattr(settings, 'ui_show_price_channels', True),
            "mod_inventory_fifo": getattr(settings, 'mod_inventory_fifo', True),
            "mod_budgets": getattr(settings, 'mod_budgets', True),
            "pos_strict_cash": getattr(settings, 'pos_strict_cash', True)
        }
        db.close()

    @classmethod
    def is_enabled(cls, key: str) -> bool:
        if cls._instance is None:
            cls()
        return cls._instance._config.get(key, True)

    @classmethod
    def set_enabled(cls, key: str, value: bool):
        if cls._instance is None:
            cls()
        cls._instance._config[key] = value

    @classmethod
    def save_to_db(cls):
        db = SessionLocal()
        settings = db.query(models.CompanySettings).first()
        if settings:
            for k, v in cls._instance._config.items():
                if hasattr(settings, k):
                    setattr(settings, k, v)
            db.commit()
        db.close()
