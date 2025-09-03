# ☕ Nam Cohhee - Coffee Shop Web Application

**Nam Cohhee** is a full-stack coffee shop management platform built with **Flask (Python)** and **PostgreSQL**, designed with dual user flows: **Admin** and **Customer**.  
It provides seamless e-commerce functionality, blog interaction, voucher management, employee scheduling, and interactive analytics dashboards.

---

## 🌟 Key Features

### 👤 Customer
- Register with **email verification** (via Gmail SMTP)  
- Login and manage personal profile  
- Browse menu by category  
- Place and track orders  
- Review purchased products  
- Add products to **favorites**  
- Read blogs, **like** or **comment**  
- Track personal spending analytics (charts)  
- View purchase history & order details  
- Access shop contact information  

### 🛠️ Admin
- Manage **employees**: add, edit, delete  
- Assign and monitor **shifts**  
- Manage **customers** and orders (status tracking)  
- Manage **products, categories, suppliers**  
- Create, edit, delete **blogs** and moderate comments  
- Create **vouchers** for one or multiple customers  
- Visualize shop performance: **revenue, top products, employee efficiency**  

---

## 🗺️ User Flow

### Customer Flow
```mermaid
flowchart TD
    A[Register / Login] --> B[Browse Menu / Products]
    B --> C[Add to Cart / Place Order]
    C --> D[Order Tracking]
    D --> E[Review Products]
    E --> F[Add to Favorites]
    F --> G[Read Blogs / Like / Comment]
    G --> H[View Personal Analytics & Profile]
flowchart TD
    A[Admin Login] --> B[Dashboard Overview]
    B --> C[Manage Employees / Shifts]
    B --> D[Manage Customers / Orders]
    B --> E[Manage Products / Categories]
    B --> F[Create / Edit / Delete Blogs]
    B --> G[Create Vouchers / Promotions]
    B --> H[View Revenue & Analytics Charts]
🏗️ Architecture & Tech Stack
```
### Frontend

HTML5, CSS3, JavaScript, Bootstrap 5
Responsive UI, dynamic dashboard, interactive charts

---


### Backend

Python (Flask)
RESTful API, authentication, email verification, business logic

---

### Database

PostgreSQL
Normalized relational schema: users, orders, products, blogs, vouchers, shifts

---

### Email

Gmail SMTP (for registration verification)
Analytics
Chart.js / JS libraries

---

Interactive charts for spending, revenue, and performance

💾 Data Management

Users: customer, employee, adminshop

Products & Inventory: product, category, supplier, importment

Orders: orders, orderdetail

Blog & Reviews: blog, blog_comments, blog_likes, review

Favorites & Vouchers: favorites, vouchers, voucher_customers

Shift Management: shift

---

⚙️ Installation & Setup

Clone the repository
```
git clone https://github.com/PhamNam342/coffee_shop_web.git
cd coffee_shop_web
```

---


Create a virtual environment & install dependencies
```
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows
pip install -r requirements.txt
```
---

## Configure the database

Create PostgreSQL database coffee_shop

Import schema (if provided)

Update config.py with your database credentials

Run the application
```
python app.py
```

---

## Access the app
👉 http://127.0.0.1:5000/

## 🔒 Security

Passwords hashed securely

Email verification for new registrations

Role-based access: Admin / Customer

Input validation on all forms

## 📊 Analytics & Visualization

Customer: spending insights, most purchased products

Admin: revenue overview, top-selling products, employee performance

Powered by Chart.js for interactive dashboards

## 📞 Contact

Author: Pham Nam

Repository: coffee_shop_web
