# 🚗🚘 Django Carpool-application API with JWT Authentication, Celery, and Redis

Welcome to the **Carpool Application**! This project is a comprehensive application built with **Python**, **Django**, **Django REST Framework (DRF)**, and **Celery**. It manages users, rides, ride requests, alerts and passenger within a carpool app context.


---

## 📌 **Project Overview**
This application allows users create rides, ride requests, alerts or reserve seats as passengers efficiently.

### **Tech Stack**
- **Python 3.11+** – Backend development.
- **Django 5.0+** – Web framework.
- **Django REST Framework** – API development.
- **Celery** – Task queue for async jobs.
- **Redis** – Message broker for Celery.
- **PostgreSQL** – Database.

---


## Features

This API provides a comprehensive set of functionalities for a carpool application, focusing on user management, security, performance, and asynchronous task handling.

* **User Registration, Login, and JWT Authentication:**
    * Users can securely register new accounts with the application.
    * A robust login system allows registered users to authenticate and access protected resources.
    * JSON Web Tokens (JWT) are employed for secure and stateless authentication, managed seamlessly through Djoser and `djangorestframework-simplejwt`. This ensures a scalable and secure way to handle user sessions.

* **Granular Permissions and Custom Access Control:**
    * The API implements a fine-grained permissions system to control access to specific API endpoints, ensuring that only authorized users can perform certain actions.
    * Custom permissions are defined and applied at the model and user levels, allowing for complex access control logic tailored to the specific needs of the carpool application (e.g., only the creator can edit a request, administrators have broader access).

* **Asynchronous Background Task Management with Celery and Redis:**
    * Long-running or resource-intensive tasks, such as sending email notifications, processing large datasets, or performing complex calculations related to carpool routes, are managed asynchronously using Celery.
    * Redis serves as the message broker for Celery, efficiently queuing and distributing tasks to worker processes. This ensures that the main API remains responsive and user experience is not hindered by background operations.

* **Efficient Cache Management with Redis:**
    * Redis is utilized as a caching backend to store frequently accessed data, such as rides and requests listings.
    * This caching strategy significantly reduces the load on the database, leading to faster response times and improved overall performance of the API, providing a smoother experience for users.

* **RESTful API Powered by Django REST Framework:**
    * The API adheres to RESTful architectural principles, leveraging the power and flexibility of Django REST Framework (DRF).
    * This ensures a well-structured, easy-to-understand, and developer-friendly API for accessing and manipulating carpool app functionalities. Standard HTTP methods (GET, POST, PUT, DELETE) are used to interact with resources, and data is exchanged in a standard format (typically JSON).

---

## Extensive desctiption of views


---

## Backend Configuration

This section highlights the advantages of the backend configurations implemented in this API, specifically concerning database management based on the environment, comprehensive logging, efficient caching strategies, and optimized database interactions.

### Dynamic Database Configuration Based on Environment

This API intelligently adapts its database connection based on whether it's running in a development or production environment.

**Benefits:**

* **Streamlined Development:** During the development phase, the API can utilize a simple and easy-to-configure database like SQLite. This allows developers to quickly set up their local environments without the overhead of managing a full-fledged database server.
* **Robust Production Setup:** For the live deployment, the API is configured to connect to a more powerful and scalable database system such as PostgreSQL or MySQL. This ensures the API can handle the demands of real-world traffic and maintain data integrity.
* **Environment Isolation and Safety:** By maintaining separate database configurations for development and production, we prevent accidental modifications or data corruption in the live environment during development activities. This separation ensures a more stable and reliable production API.

### Comprehensive Logging

The API is equipped with a robust logging system to record various events and activities.

**Benefits:**

* **Enhanced Debugging Capabilities:** Detailed logs provide invaluable information for diagnosing and resolving issues that may arise. By tracking the flow of requests and potential errors, developers can quickly pinpoint the root cause of problems.
* **Effective Monitoring and Auditing:** Logging allows for continuous monitoring of the API's health and performance. It also provides an audit trail of important actions, which can be crucial for security and compliance purposes.
* **Deeper Operational Insights:** Logs can offer valuable insights into how the API is being used, identify usage patterns, and highlight areas for potential optimization or improvement.

### Strategic Caching Implementation

To enhance performance and reduce server load, the API employs various caching mechanisms.

**Benefits:**

* **Improved API Responsiveness:** Caching stores frequently accessed data in faster memory layers, significantly reducing the time it takes to retrieve this information. This leads to quicker response times for users.
* **Reduced Database Strain:** By serving data from the cache instead of repeatedly querying the database, the API minimizes the load on the database server. This allows the database to handle more complex operations and improves overall scalability.
* **Enhanced Scalability:** With less reliance on the database for every request, the API can handle a larger volume of concurrent users and requests without performance degradation.

### Optimized Database Queries with Developer Tools

The integration of developer tools allows for in-depth analysis and optimization of the API's database interactions.

**Benefits:**

* **Identification of Performance Bottlenecks:** Tools can highlight slow or inefficient database queries, enabling developers to pinpoint areas in the code that are causing performance issues.
* **Efficient Data Retrieval:** By analyzing query patterns, developers can implement strategies such as eager loading of related data to minimize the number of database queries required, leading to faster data retrieval.
* **Better Resource Utilization:** Optimizing database queries reduces the overall resource consumption of the API, leading to more efficient use of server resources and potentially lower operating costs.


---

## Unit Testing for Robustness

This API incorporates comprehensive unit tests for its core components: views, serializers, and models. These tests reside in dedicated `tests` directories within each application.

**Why Unit Testing is Necessary:**

* **Ensuring Code Correctness:** Unit tests verify that individual units of code (functions, methods, classes) behave as expected under various conditions. This helps catch bugs early in the development cycle, preventing them from propagating into more complex parts of the application.
* **Facilitating Refactoring:** With a solid suite of unit tests, you can confidently refactor your code to improve its design or performance. The tests act as a safety net, ensuring that your changes haven't introduced any regressions or broken existing functionality.
* **Improving Code Quality:** Writing unit tests encourages developers to think about the design and behavior of their code more rigorously. This often leads to cleaner, more modular, and more maintainable code.
* **Providing Documentation:** Unit tests serve as a form of living documentation, illustrating how individual components of the API are intended to be used and what their expected behavior is.
* **Accelerating Development:** While it might seem counterintuitive, a well-maintained test suite can actually speed up development in the long run by reducing the time spent debugging and fixing errors in later stages.

**Running Unit Tests:**

To execute the unit tests for this API, navigate to the root directory of this project in your terminal and run the following Django management command:

```bash
python manage.py test
---



## 🛠 **Setup Instructions and configurations**

### 1️⃣ **Clone the Repository**
```sh
git clone https://github.com/SiandjaRemy/carpool-application-API
cd carpool-app-API
```

### 2️⃣ Create and activate a virtual environment:
   ```
   virtualenv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

### 3️⃣ **Install the dependencies:**
   ```
   pip install -r requirements.txt
   ```

### 4️⃣ **Create `.env` file for sensitive settings (such as secret keys, database credentials, etc.):**
   ```env
   SECRET_KEY="your-secret-key"
   DEBUG=True

   REDIS_INSTANCE_URL=redis://127.0.0.1:6379/0
   REDIS_INSTANCE_URL_2=redis://127.0.0.1:6379/1
   REDIS_INSTANCE_URL_3=redis://127.0.0.1:6379/2

   LOCAL_DB_NAME=
   LOCAL_DB_USER=
   LOCAL_DB_PASSWORD=
   LOCAL_DB_HOST=
   LOCAL_DB_PORT=

   FRONTEND_URL="Link to a frontend you link the API to"

   EMAIL_HOST_USER="Your email host user"
   EMAIL_HOST_PASSWORD="Your email host password"
   DEFAULT_FROM_EMAIL=Carpool <"Your email host user">

   MAIN_ADMIN_NAME="Admin name"
   MAIN_ADMIN_EMAIL="Your email host user"
   ```

### 5️⃣ Run the migrations:
   ```
   python manage.py makemigrations

   python manage.py migrate
   ```


---


## Running the Application

### Starting the Django Server
To run the Django development server:
```
python manage.py runserver
```
This will start the server at http://127.0.0.1:8000/

Go to http://127.0.0.1:8000/swagger for the swagger view


### Running Celery
To start the Celery worker:
```
celery -A Carpool_Sytem --loglevel=info
```

on Windows, use --pool=solo
```
celery -A Carpool_Sytem worker --pool=solo --loglevel=INFO 
```

To start Celery beat (for periodic tasks):
```
celery -A Carpool_Sytem beat --loglevel=info
```


---


## Possible Improvements
### Note:
This project is a demo ment to showcase my understanding of query optimization, background tasks and caching using Django and the DjangoRest Framework, as such, some functionalities required for this app to be used in production may be missing for they are out of the scope of this project. 
However, you can find many different repositories where functionalities missing here have been implemented

Below are some of the functionalities that i think are lacking. I will work on some in the near future but not all, so, feel free to add them on your side.

1. Email verification: When an account is created, the user creating the account must validate that he is the actual owner of that email.

2. The password reset functionality sends a link to the email that redirects to a frontend that i haven created. Feel free to modify the password reset flow.


3. If the current filters might be too basic and lacking in precision for certain cases. Feel free to add more of them.

4. A passenger should be able of reserving the whole car if he wants to.

5. The permisions are pretty basic. Play with them to suit your need.

6. Payment intergration.

7. Containerizing the app using docker will be great.


### Conclusion
This Django Carpool App API is optimized for high performance and scalability, with mechanisms in place to handle a large volume of requests. The inclusion caching, Celery, and Redis enhances overall performance. The application needs a minimal amount of modifications/updates to be ready to be deployed in production and can easily scale as needed.


---


## 🎯 **License**
This project is licensed under the **MIT License**.

---

🚀 **Happy coding!** 🎉



