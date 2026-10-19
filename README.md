# Vijaya Lakshmi Agro Agencies — Django store

Starter e-commerce website for pesticides, fertilizers and seeds, with product management in Django Admin and WhatsApp checkout.

## Included
- Three product categories: Pesticides, Fertilizers, Seeds
- Product photos, descriptions, prices, stock and active/inactive status
- Search, category filter, product detail and cart
- Checkout form that prepares a WhatsApp order message for **+91 8297243999**
- English, Telugu and Hindi interface selector (interface labels are translated; product descriptions are entered by the shop owner)
- Django Admin at `/admin/`
- PostgreSQL support and Render deployment configuration
- Optional Cloudinary integration for persistent product images

## Run locally (Windows / VS Code)
1. Install Python 3.12 or newer supported Python.
2. Open this folder in VS Code.
3. In the VS Code terminal run:

   ```powershell
   py -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   copy .env.example .env
   py manage.py migrate
   py manage.py createsuperuser
   py manage.py runserver
   ```

4. Open `http://127.0.0.1:8000/`.
5. Open `http://127.0.0.1:8000/admin/` and sign in to add products.

If PowerShell blocks activation, use `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` for that terminal, then activate again.

## Add products
In Django Admin, open Products → Add product. Choose the category, enter the name, description, price, stock and upload a photo. Mark the product active to show it on the public website. Only add products that the business is legally authorised to sell.

## WhatsApp checkout
The checkout page estimates the subtotal from the server-side product prices, then opens WhatsApp with the product list, customer details and estimate. The customer must press **Send** in WhatsApp. The owner confirms availability, delivery fee, final total and payment. This project does not collect online payments or automatically create a confirmed paid order.

## Deployment on Render
1. Push this project to a GitHub repository.
2. In Render, create a Blueprint from the repository and review `render.yaml`.
3. Deploy the web service and PostgreSQL database.
4. Create a Django superuser from the Render Shell: `python manage.py createsuperuser`.
5. Configure a persistent image-storage provider before uploading real product images. For Cloudinary, set `CLOUDINARY_URL` in Render Environment. Without this, uploaded media on an ephemeral server filesystem may be lost on redeploy.
6. For a custom domain, add it in Render and copy the exact DNS records Render shows into your domain registrar. Set `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` to match your real domain.
7. Before launch, use a strong secret, verify HTTPS, test backups, check current Render plan costs, and test checkout on mobile.

## Important production notes
- The shop's owner WhatsApp number is configured in `store/views.py` as `918297243999`.
- `DEBUG` must be false in production.
- Product prices are estimates; shipping/delivery fees are not included until the owner confirms them.
- Pesticide/fertilizer products may be subject to local licensing, labelling and sale restrictions. Verify the business and product eligibility before listing them.
