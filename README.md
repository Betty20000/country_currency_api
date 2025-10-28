
build command: pip install -r requirements.txt && python manage.py collectstatic --noinput

start command:web: python manage.py migrate  && gunicorn country_currency.wsgi --bind 0.0.0.0:$PORT
# 🌍 Country Currency & Exchange API

A Django REST API that provides country data, currency exchange rates, and estimated GDPs.
Built for learning and practical backend experience.

---

## ⚙️ Features

✅ Fetches country data from [REST Countries API](https://restcountries.com/v2/all?fields=name,capital,region,population,flag,currencies)  
✅ Stores data locally in a MySQL or SQLite database  
✅ Allows filtering by: name, capital, region, population, currency_code, exchange_rate, estimated_gdp  
✅ Supports sorting by any field: `?sort=<field>_asc` or `?sort=<field>_desc`  
✅ Automatically orders by **highest GDP** when filtering by `region`  
✅ Dynamically reassigns IDs when results are sorted (IDs start from 1)  
✅ Clean error handling for invalid queries  
✅ Refreshes data from external APIs on demand  

---

## 🏗️ Tech Stack

- Python 3.11+
- Django 5+
- Django REST Framework
- Requests
- MySQL / SQLite

---

## 🚀 Setup Instructions

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/your-username/country-currency-api.git
cd country-currency-api
```

### 2️⃣ Create & Activate Virtual Environment
```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On Mac/Linux
source venv/bin/activate
```

### 3️⃣ Install Dependencies
```bash
pip install -r requirements.txt
```

### 4️⃣ Run Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 5️⃣ Run Server
```bash
python manage.py runserver
```

---

## 🧠 Example Endpoints

| Method | Endpoint | Description |
|--------|-----------|--------------|
| GET | `/countries` | List all countries |
| GET | `/countries?region=Africa` | Filter by region (auto-sorts by GDP) |
| GET | `/countries?sort=gdp_desc` | Sort by GDP descending |
| GET | `/countries?capital=Nairobi` | Filter by capital |
| POST | `/countries/refresh` | Refresh data from RESTCountries |

---

## 🧾 Sample JSON Response

```json
[
  {
    "id": 1,
    "name": "Nigeria",
    "capital": "Abuja",
    "region": "Africa",
    "population": 206139589,
    "currency_code": "NGN",
    "exchange_rate": 1600.23,
    "estimated_gdp": 25767448125.2,
    "flag_url": "https://flagcdn.com/ng.svg",
    "last_refreshed_at": "2025-10-22T18:00:00Z"
  },
  {
    "id": 2,
    "name": "Ghana",
    "capital": "Accra",
    "region": "Africa",
    "population": 31072940,
    "currency_code": "GHS",
    "exchange_rate": 15.34,
    "estimated_gdp": 3029834520.6,
    "flag_url": "https://flagcdn.com/gh.svg",
    "last_refreshed_at": "2025-10-22T18:00:00Z"
  }
]
```

---

## 🧩 Error Responses

| Status | Cause | Example |
|--------|--------|----------|
| 400 | Invalid filter or sort | `{ "error": "Validation failed", "details": {"sort": "invalid format"}}` |
| 404 | No matching countries | `{ "error": "Country not found"}` |
| 500 | Server error | `{ "error": "Internal server error"}` |

---

## 🧰 Environment Variables

Create a `.env` file in your project root:
```
SECRET_KEY=your_secret_key
DEBUG=True
DATABASE_URL=mysql://user:password@localhost/db_name
```

---

## 🧑‍💻 Development Commands

| Task | Command |
|------|----------|
| Start server | `python manage.py runserver` |
| Run migrations | `python manage.py migrate` |
| Create superuser | `python manage.py createsuperuser` |
| Collect static files | `python manage.py collectstatic` |

---

## 📜 License

MIT License © 2025 — You are free to use and modify this project.