# How to Migrate Django Models to SQlite3 DB using Django's ORM

1. **Set up your models**  
   In `src/models.py`, create or update your model classes.

2. **Generate migration files for src app**  
   Open your terminal and run:
   ```bash
   python manage.py makemigrations src
   ```
   This command scans your models and creates new migration files in the `migrations` directory.

3. **Apply the migrations**  
   Run:
   ```bash
   python manage.py migrate
   ```
   This commits the changes to the database (`db.sqlite3`).

> **TL;DR**: Whenever you change or create models, run `python manage.py makemigrations` and then `python manage.py migrate`.
