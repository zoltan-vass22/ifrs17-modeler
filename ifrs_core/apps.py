from django.apps import AppConfig

class IfrsCoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ifrs_core"   # the Python package path
    label = "core"       # keep the original app label so migrations still match
