"""
from django.apps import AppConfig

# can maybe be used to build agents at startup (avoid delay on the first llm call)
class MyAppConfig(AppConfig):
    name = 'cti_app'

    def ready(self):
        pass
"""