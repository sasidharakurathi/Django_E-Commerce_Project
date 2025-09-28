# your_app/management/commands/export_data.py

import os
from django.core.management.base import BaseCommand
from ecom.models import Product

class Command(BaseCommand):
    help = 'Exports relevant e-commerce data to a text file for the RAG knowledge base.'

    def handle(self, *args, **kwargs):
        # Define the output file path. It will be created in the project's root directory.
        output_file_path = os.path.join(os.getcwd(), 'knowledge_base.txt')

        self.stdout.write(f"Starting data export to {output_file_path}...")

        with open(output_file_path, 'w', encoding='utf-8') as f:
            # --- Export Product Data ---
            f.write("--- Products ---\n\n")
            products = Product.objects.all()
            if not products.exists():
                f.write("No product information available.\n\n")
            else:
                for product in products:
                    f.write(f"Product Name: {product.name}\n")
                    f.write(f"Description: {product.description}\n")
                    f.write(f"Price: ${product.price:.2f}\n")
            
            self.stdout.write(f"Exported {products.count()} products.")

        self.stdout.write(self.style.SUCCESS(f"Successfully exported all data to {output_file_path}"))