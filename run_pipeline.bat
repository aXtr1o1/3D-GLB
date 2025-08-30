@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM ==== CONFIG (portable) ====
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
set "PY37=C:\Users\sanje_3wfdh8z\AppData\Local\Programs\Python\Python37\python.exe"
set "PY311=C:\Users\sanje_3wfdh8z\AppData\Local\Programs\Python\Python311\python.exe"
set "VCVARS=C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\VC\Auxiliary\Build\vcvars64.bat"
set "CUDA_HOME=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.7"
REM ===========================

REM ==== ARG PARSING (gender) ====
set "ARG=%~1"
if defined ARG ( if /i "%ARG:~0,1%"=="-" set "ARG=%ARG:~1%" )
if /i "%ARG%"=="male" (
  set "GENDER=male"
) else if /i "%ARG%"=="female" (
  set "GENDER=female"
) else (
  echo [error] Usage: %~nx0 ^<male^|female^>
  exit /b 2
)
echo [bootstrap] Gender: %GENDER%

echo.
echo [bootstrap] Loading MSVC build environment...
call "%VCVARS%" || (echo Failed to load vcvars64.bat & exit /b 1)

echo [bootstrap] Setting CUDA...
set "PATH=%CUDA_HOME%\bin;%PATH%"

echo [bootstrap] Root: %ROOT%
cd /d "%ROOT%" || (echo Could not cd to %ROOT% & exit /b 1)

REM Optional: clear failed torch extension builds
rmdir /s /q "%LOCALAPPDATA%\Temp\torch_extensions" 2>nul

where cl >nul 2>&1 || (echo [error] cl.exe not found even after vcvars. Aborting. & exit /b 1)
nvcc --version >nul 2>&1 || (echo [warn] nvcc not found on PATH; continuing...)

echo.
echo === Step 1: Moving Input Image (.) ===
if not exist "hair_mapper\stylegan-encoder\raw_images" mkdir "hair_mapper\stylegan-encoder\raw_images"
if not exist "input" mkdir "input"
if exist "input\*.*" move /Y "input\*.*" "hair_mapper\stylegan-encoder\raw_images" >nul

echo.
echo === Step 2: Analyzing Image (hair_mapper\stylegan-encoder) ===
if not exist "hair_mapper\stylegan-encoder\aligned_images" mkdir "hair_mapper\stylegan-encoder\aligned_images"
pushd "hair_mapper\stylegan-encoder"
call "%PY37%" "align_images.py" "raw_images" "aligned_images"
if errorlevel 1 goto :fail
popd

echo.
echo === Step 3: Cleaning image (raw_images) ===
del /q "hair_mapper\stylegan-encoder\raw_images\*.*" 2>nul

echo.
echo === Step 4: Moving aligned -> HairMapper\test_data\origin ===
if not exist "hair_mapper\HairMapper\test_data\origin" mkdir "hair_mapper\HairMapper\test_data\origin"
if exist "hair_mapper\stylegan-encoder\aligned_images\*.*" move /Y "hair_mapper\stylegan-encoder\aligned_images\*.*" "hair_mapper\HairMapper\test_data\origin" >nul

echo.
echo === Step 5: Encoding image (encoder4editing) ===
pushd "hair_mapper\HairMapper\encoder4editing"
call "%PY37%" "encode.py" --data_dir "..\test_data"
if errorlevel 1 goto :fail
popd

echo.
echo === Step 6: Hair removal (HairMapper) ===
pushd "hair_mapper\HairMapper"
call "%PY37%" "main_mapper.py" --data_dir "test_data"
if errorlevel 1 goto :fail
popd

echo.
echo === Step 7: Background Removal (.) ===
call "%PY37%" "background_remover.py"
if errorlevel 1 goto :fail

echo.
echo === Step 8: Cleaning mapper_res ===
rd /s /q "hair_mapper\HairMapper\test_data\mapper_res" 2>nul
mkdir "hair_mapper\HairMapper\test_data\mapper_res"

echo.
echo === Step 9: Reset test_data\code, mapper_res, origin ===
for %%F in (code mapper_res origin) do (
  if exist "hair_mapper\HairMapper\test_data\%%F" rd /s /q "hair_mapper\HairMapper\test_data\%%F"
  mkdir "hair_mapper\HairMapper\test_data\%%F"
)

echo.
echo === Step 10: Building 3D Mesh (DECA) ===
pushd "DECA"
rmdir /s /q "%LOCALAPPDATA%\Temp\torch_extensions" 2>nul
call "%PY37%" "demos\demo_reconstruct.py" -i "TestSamples\examples" --saveDepth True --saveObj True --useTex True
if errorlevel 1 goto :fail
popd

echo.
echo === Step 11: Moving (copy OBJ + texture; delete result folder) ===
REM Ensure destinations exist
if not exist "Blender\ready to use model\head" mkdir "Blender\ready to use model\head"
if not exist "Texture\input" mkdir "Texture\input"

REM Find newest result subfolder
set "RESULTS=DECA\TestSamples\examples\results"
set "NEWFOLDER="
for /f "delims=" %%D in ('dir /ad /b /o-d "%RESULTS%"') do set "NEWFOLDER=%%D" & goto :got_newest
:got_newest
if not defined NEWFOLDER (
  echo [error] No result folders found in "%RESULTS%".
  goto :fail
)
set "DYNFOLDER=%RESULTS%\%NEWFOLDER%"
set "BASENAME=%NEWFOLDER%"
echo Found newest result: "%DYNFOLDER%"

REM Resolve OBJ
set "OBJ_SRC=%DYNFOLDER%\%BASENAME%.obj"
if exist "%OBJ_SRC%" goto :obj_ok
set "OBJ_SRC="
for /f "delims=" %%F in ('dir /b /a:-d "%DYNFOLDER%\*.obj" 2^>nul') do set "OBJ_SRC=%DYNFOLDER%\%%F" & goto :obj_ok
echo [error] OBJ not found in "%DYNFOLDER%".
goto :fail
:obj_ok

REM Resolve texture (prefer png, then jpg, then jpeg; fallback newest)
set "TEX_SRC="
for %%E in (png jpg jpeg) do (
  if not defined TEX_SRC for /f "delims=" %%F in ('dir /b /a:-d "%DYNFOLDER%\*.%%E" 2^>nul') do set "TEX_SRC=%DYNFOLDER%\%%F" & goto :tex_ok
)
for /f "delims=" %%F in ('dir /b /a:-d /o-d "%DYNFOLDER%\*.png" "%DYNFOLDER%\*.jpg" "%DYNFOLDER%\*.jpeg" 2^>nul') do set "TEX_SRC=%DYNFOLDER%\%%F" & goto :tex_ok
echo [error] Texture image (.png/.jpg/.jpeg) not found in "%DYNFOLDER%".
goto :fail
:tex_ok

REM Copy files (and print friendly names)
for %%A in ("%OBJ_SRC%") do set "OBJ_NAME=%%~nxA"
for %%A in ("%TEX_SRC%") do set "TEX_NAME=%%~nxA"
copy /Y "%OBJ_SRC%" "Blender\ready to use model\head" >nul || goto :fail
echo Copied OBJ: %OBJ_NAME% -> Blender\ready to use model\head
copy /Y "%TEX_SRC%" "Texture\input" >nul || goto :fail
echo Copied TEX: %TEX_NAME% -> Texture\input

REM Optional: clean sample PNGs
del /q "DECA\TestSamples\examples\*.png" 2>nul

REM Delete the dynamic folder only after successful copies
rd /s /q "%DYNFOLDER%"
echo Deleted folder: "%DYNFOLDER%"


echo.
echo === Step 12: Applying Textures (Texture) ===
pushd "Texture"
call "%PY311%" "texture.py"
if errorlevel 1 goto :fail
popd

echo.
echo === Step 13: Cleaning (Texture\input) ===
del /q "Texture\input\*.png" 2>nul
del /q "Texture\input\*.jpg" 2>nul
del /q "Texture\input\*.jpeg" 2>nul

echo.
echo === Step 14: Move head final_texture ===
if exist "Blender\ready to use model\head\final_texture.jpeg" del /q "Blender\ready to use model\head\final_texture.jpeg"
move /Y "Texture\output\final_texture.jpeg" "Blender\ready to use model\head" >nul

echo.
echo === Step 15: Move body blend_image ===
if not exist "Blender\Texture_body\input" mkdir "Blender\Texture_body\input"
if exist "Blender\Texture_body\input\blend_image.jpg" del /q "Blender\Texture_body\input\blend_image.jpg"
move /Y "Texture\output\blend_image.jpg" "Blender\Texture_body\input" >nul

echo.
echo === Step 16: Body Importing (Texture_body) ===
pushd "Blender\Texture_body"
call "%PY311%" "texture_body.py"
if errorlevel 1 goto :fail
popd

echo.
echo === Step 17: Final Rendering (Blender) ===
pushd "Blender"
call "%PY311%" "blender_merging.py" --g "%GENDER%"
if errorlevel 1 goto :fail
popd

echo.
echo === Step 18: Output cleanup (head) ===
if exist "Blender\ready to use model\head\*.*" del /q "Blender\ready to use model\head\*.*" 2>nul



echo.
echo === Step 19: Uploading to S3 ===
echo { 
echo    "title": "Upload to S3", 
echo    "dir": ".", 
echo    "command": [
echo        "python_311", 
echo        "s3_push_objs.py", 
echo        "--dir", "Blender/output", 
echo        "--bucket", "3dglbops", 
echo        "--prefix", "blender/outputs", 
echo        "--region", "ap-south-1", 
echo        "--public"
echo    ] 
echo }
call "%PY311%" "s3_push_objs.py" --dir "Blender/output" --bucket "3dglbops" --prefix "blender/outputs" --region "ap-south-1" --public
if errorlevel 1 goto :fail

echo.
echo === Step 20: Cleaning Up ===
echo { 
echo    "title": "Cleaning Up", 
echo    "dir": ".", 
echo    "command": "lambda: ([os.remove(f) for f in glob.glob('Blender/output/*.glb')]) and None" 
echo }
call "%PY311%" -c "import os, glob; [os.remove(f) for f in glob.glob('Blender/output/*.glb')]"
if errorlevel 1 goto :fail

echo.
echo ✅ Pipeline completed successfully.
exit /b 0

