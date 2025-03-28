# Arx - Django Forum For School System

A robust Django-based user authentication system using JWT (JSON Web Tokens) for secure, stateless authentication.

## Project Structure

### Root Directory

- `Arx/` - Main Django project configuration directory
  - Contains settings, main URL routing, and WSGI/ASGI configuration
  - `settings.py` - Project settings including JWT configuration
  - `urls.py` - Main URL routing configuration

### Applications

- `accounts/` - Django application for user authentication and management
  - `models.py` - User model with JWT token generation/validation methods
  - `views.py` - Authentication views for login, registration, and profile management
  - `middleware.py` - JWT authentication middleware
  - `decorators.py` - Custom decorators like `login_required`
  - `urls.py` - URL routing for the accounts application

### Templates and Static Files

- `htmls/` - Django template directory
  - `accounts/` - Templates related to the accounts application
    - `auth.html` - Authentication page (login/register)
    - `home.html` - Home page with user profile display

- `static/` - Static files directory
  - `accounts/` - Static files related to the accounts application
    - `css/` - CSS stylesheets
      - `styles.css` - Main stylesheet for all account-related pages
    - `js/` - JavaScript files
      - `auth.js` - Authentication logic for login/register
      - `home.js` - Home page functionality and user profile display

### Migrations

- `accounts/migrations/` - Database migration files for the accounts application

## Features

- User registration and login
- JWT token authentication
- Protected API routes requiring authentication
- User profile management
- Session-less authentication for better scalability
- Frontend integration with Vue.js and Element UI

## Authentication Flow

1. User registers or logs in through the authentication interface
2. Server validates credentials and generates a JWT token
3. Token is stored in localStorage on the client
4. Token is sent with each subsequent request in the Authorization header
5. Server middleware validates the token and identifies the user
6. Protected routes are accessible only to authenticated users

## Development

The project separates concerns with:
- Backend: Django for API endpoints and business logic
- Frontend: Vue.js for UI components and interactivity
- Authentication: JWT for secure, stateless authentication

This structure allows for clean separation between frontend and backend, making the application more maintainable and scalable. 