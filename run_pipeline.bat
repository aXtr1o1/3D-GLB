@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM ==== CONFIG ====
set "ROOT=C:\Users\tamil\Desktop\3D_Git\3D-GLB"
set "PY37=C:\Users\tamil\AppData\Local\Programs\Python\Python37\python.exe"
set "VCVARS=C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
set "CUDA_HOME=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.7"
REM ==============

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
REM (Optional) Clean torch extension cache again before JIT compile
rmdir /s /q "%LOCALAPPDATA%\Temp\torch_extensions" 2>nul
call "%PY37%" "demos\demo_reconstruct.py" -i "TestSamples\examples" --saveDepth True --saveObj True --useTex True
if errorlevel 1 goto :fail
popd

echo.
echo ✅ Pipeline completed successfully.
exit /b 0

:fail
echo.
echo ❌ Failed (errorlevel %errorlevel%). See the step above for details.
exit /b %errorlevel%
