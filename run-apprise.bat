@echo off
REM Apprise Docker Run Script for Windows

setlocal enabledelayedexpansion

echo === Apprise Docker Runner ===

if "%1"=="" goto usage
set COMMAND=%1
shift

if "%COMMAND%"=="server" goto server
if "%COMMAND%"=="test" goto test
if "%COMMAND%"=="shell" goto shell
if "%COMMAND%"=="logs" goto logs
if "%COMMAND%"=="stop" goto stop
if "%COMMAND%"=="clean" goto clean
goto usage

:server
echo Starting Apprise API server...
echo URL will be: http://localhost:8000
docker run -d ^
    --name apprise-server ^
    --restart unless-stopped ^
    -p 8000:8000 ^
    -v "%CD%\config:/config" ^
    -e APPRISE_LOG_LEVEL=info ^
    apprise:latest ^
    --verbose --config="/config/apprise.conf" --server="0.0.0.0:8000"
echo Server started!
echo Check logs with: %0 logs
echo Stop with: %0 stop
goto end

:test
echo Running Apprise CLI in test mode...
docker run -it --rm ^
    -v "%CD%\config:/config" ^
    apprise:latest ^
    %*
goto end

:shell
echo Opening shell in container...
docker run -it --rm ^
    -v "%CD%\config:/config" ^
    --entrypoint /bin/bash ^
    apprise:latest
goto end

:logs
docker ps | findstr apprise-server >nul
if errorlevel 1 (
    echo No running apprise-server container found
    exit /b 1
)
echo Showing logs from apprise-server:
docker logs -f apprise-server
goto end

:stop
echo Stopping apprise-server...
docker stop apprise-server 2>nul
docker rm apprise-server 2>nul
echo Server stopped
goto end

:clean
echo Cleaning up...
docker stop apprise-server 2>nul
docker rm apprise-server 2>nul
docker rmi apprise:latest 2>nul
echo Cleanup complete
goto end

:usage
echo Usage: %0 [command] [options]
echo.
echo Commands:
echo   server      Run Apprise API server on port 8000
echo   test        Test Apprise CLI
echo   shell       Open shell in container
echo   logs        Show container logs
echo   stop        Stop running containers
echo   clean       Remove containers and images
echo.
echo Examples:
echo   %0 server
echo   %0 test --help
echo   %0 shell

:end
endlocal
