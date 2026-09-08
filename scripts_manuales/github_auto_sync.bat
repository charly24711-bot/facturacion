@echo off
echo ==============================================
echo Iniciando Sincronizacion Automatica con GitHub
echo ==============================================

:: Cambiar al directorio del proyecto
cd /d "c:\ENTORNO LOCAL\Control"

:: Agregar todos los cambios
git add .

:: Crear un commit con la fecha y hora actual
set datetime=%date% %time:~0,8%
git commit -m "Backup Automatico - %datetime%"

:: Subir a GitHub
git push origin main

echo ==============================================
echo Sincronizacion Completada.
echo ==============================================
exit
