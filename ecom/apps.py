from django.apps import AppConfig


class EcomConfig(AppConfig):
    name = 'ecom'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        """
        Initialize the RAG pipeline when the Django app starts.
        This runs only once when the server starts, not on every request.
        """
        # Only initialize in the main process, not in reloader processes
        import os
        if os.environ.get('RUN_MAIN') != 'true':
            return

        try:
            print("🚀 Starting RAG pipeline initialization at app startup...")
            from .Chatbot.rag_pipeline import initialize_rag_pipeline
            initialize_rag_pipeline()
            print("✅ RAG pipeline initialized successfully at startup!")
        except Exception as e:
            print(f"❌ Failed to initialize RAG pipeline at startup: {e}")
            print("⚠️ Chatbot functionality may be limited.")
