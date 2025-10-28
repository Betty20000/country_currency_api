web: python manage.py migrate  && gunicorn country_currency.wsgi --bind 0.0.0.0:$PORT

pip install -r requirements.txt && python manage.py collectstatic --noinput

