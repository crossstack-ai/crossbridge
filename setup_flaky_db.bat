@echo off
REM Setup and populate flaky test database with sample data

echo ================================================================================
echo CROSSBRIDGE FLAKY TEST DATABASE SETUP
echo ================================================================================
echo.

REM Check if PostgreSQL is running
echo Checking PostgreSQL connection...
docker ps | findstr crossbridge-db >nul 2>&1
if errorlevel 1 (
    echo PostgreSQL container not found. Starting it now...
    docker run -d --name crossbridge-db -e POSTGRES_DB=crossbridge -e POSTGRES_USER=crossbridge -e POSTGRES_PASSWORD=crossbridge -p 5432:5432 postgres:15
    echo Waiting for PostgreSQL to be ready...
    timeout /t 10 /nobreak >nul
) else (
    echo PostgreSQL container is already running
)

echo.
echo Setting environment variable...
set CROSSBRIDGE_DB_URL=postgresql://crossbridge:crossbridge@localhost:5432/crossbridge

echo.
echo Running database population script...
python tests\populate_flaky_test_db.py

echo.
echo ================================================================================
echo SETUP COMPLETE!
echo ================================================================================
echo.
echo Grafana Dashboard: grafana/flaky_test_dashboard.json
echo Database URL: postgresql://crossbridge:crossbridge@localhost:5432/crossbridge
echo.
pause
