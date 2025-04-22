# FTTBOX

A brief description of the Flask application, e.g., "A web application for managing and storing documents and folders, similar to Google Drive."

## Prerequisites

Before you begin, ensure you have the following installed on your system:

* **Python:** Version 3.10 or higher is recommended.
* **pip:** Python package installer (usually comes with Python).
* **Git:** For cloning the repository.
* **PostgreSQL:** A running PostgreSQL server instance (version 12+ recommended). You will need database connection details (host, port, username, password, database name).
* **AWS Account & IAM Credentials:**
    * An AWS account is required for S3 storage.
    * Each developer needs an IAM User with programmatic access (Access Key ID and Secret Access Key).
    * This IAM User needs permissions to perform actions (like `s3:PutObject`, `s3:GetObject`, `s3:DeleteObject`) on the designated S3 bucket. (**Note:** Provide specific instructions or policies given to teammates here).

## Setup Instructions

Follow these steps to set up your local development environment:

1.  **Clone the Repository:**
    ```bash
    git clone <your-repository-url>
    cd <your-project-directory>
    ```

2.  **Create and Activate Virtual Environment:**
    * **macOS/Linux:**
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```
    * **Windows (Git Bash/WSL):**
        ```bash
        python -m venv venv
        source venv/Scripts/activate 
        ```
    * **Windows (Command Prompt):**
        ```bash
        python -m venv venv
        .\venv\Scripts\activate.bat
        ```
    * **Windows (PowerShell):**
        ```bash
        python -m venv venv
        .\venv\Scripts\Activate.ps1 
        # If you get an error, you might need to run: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process 
        ```
    *(Your terminal prompt should now show `(venv)`)*

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Database Setup:**
    * Ensure your PostgreSQL server is running.
    * Create a new database and a user for this project if you haven't already. Note down the database name, username, password, host (usually `localhost`), and port (usually `5432`).
    * **(Crucial Step)** Set up the database schema using Flask-Migrate. Run the following command in your activated virtual environment from the project root:
        ```bash
        flask db upgrade
        ```
        This will create all the necessary tables based on the project's models and migration history.

5.  **Environment Variables:**
    * This project uses a `.env` file to manage configuration and sensitive credentials. This file is **not** committed to Git (it's listed in `.gitignore`).
    * Copy the example file:
        ```bash
        # macOS/Linux
        cp .env.example .env 

        # Windows
        copy .env.example .env 
        ```
    * **Edit the `.env` file** with your specific details:
        * `SECRET_KEY`: Generate a secure random key. You can use Python:
            ```bash
            # Run this in your terminal (doesn't need venv active)
            python -c 'import os; print(os.urandom(24).hex())' 
            ```
            Copy the generated hex string into the `.env` file.
        * `DATABASE_URL`: Update with your PostgreSQL connection details in the format: `postgresql://YOUR_DB_USER:YOUR_DB_PASSWORD@YOUR_DB_HOST:YOUR_DB_PORT/YOUR_DB_NAME` (e.g., `postgresql://devuser:devpass@localhost:5432/mydriveapp_db`)
        * `S3_BUCKET`: The exact name of the S3 bucket being used for storage.
        * `S3_KEY`: Your personal AWS IAM Access Key ID.
        * `S3_SECRET`: Your personal AWS IAM Secret Access Key.
        * `S3_REGION`: The AWS region where your S3 bucket is located (`us-east-2`).
        * `MAX_CONTENT_LENGTH_MB`: 50.
        * `FLASK_DEBUG`: Set to `True` for development (enables debug mode and auto-reloading), `False` for production.
    * **Save the `.env` file.**

## Running the Application

1.  Ensure your virtual environment is activated (`source venv/bin/activate` or Windows equivalent).
2.  Run the Flask development server:
    ```bash
    python app.py
    ```
3.  Open your web browser and navigate to: `http://127.0.0.1:5000` (or the URL provided in the terminal output).

## Database Migrations (For Developers)

This project uses Flask-Migrate to manage database schema changes.

* If you pull changes that include modifications to the SQLAlchemy models (`models.py`), you may need to apply new migrations by running:
    ```bash
    flask db upgrade
    ```
* If you make changes to the models yourself, you need to generate a new migration script:
    ```bash
    # Make sure the database is up-to-date first: flask db upgrade
    flask db migrate -m "Brief description of model changes" 
    # Review the generated script in migrations/versions/
    flask db upgrade 
    # Commit the new migration script along with your model changes
    ```

## Troubleshooting / Contact

* If you encounter setup issues, double-check your `.env` file values (database URL, AWS keys, region, bucket name) and ensure all prerequisites are installed.
* Contact for further assistance.