# Initial migration
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="Category",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=80)),
                ("slug", models.SlugField(blank=True, unique=True)),
                ("category_type", models.CharField(choices=[("pesticides","Pesticides"),("fertilizers","Fertilizers"),("seeds","Seeds")], max_length=20, unique=True)),
                ("description", models.CharField(blank=True, max_length=250)),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
            ],
            options={"ordering":["sort_order","name"],"verbose_name_plural":"Categories"},
        ),
        migrations.CreateModel(
            name="Product",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=180)),
                ("brand", models.CharField(blank=True, max_length=120)),
                ("slug", models.SlugField(blank=True, unique=True)),
                ("description", models.TextField()),
                ("price", models.DecimalField(decimal_places=2, max_digits=10)),
                ("unit", models.CharField(default="pack", max_length=50)),
                ("stock_quantity", models.PositiveIntegerField(default=0)),
                ("image", models.ImageField(blank=True, null=True, upload_to="products/")),
                ("is_active", models.BooleanField(default=True)),
                ("featured", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("category", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="products", to="store.category")),
            ],
            options={"ordering":["-featured","name"]},
        ),
    ]
