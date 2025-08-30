
# 3D GLB Generator Project

This project takes a face photo and generates a 3D `.glb` file using deep learning models integrated through an API.

---

## 🔧 System Requirements

Before starting, make sure your system has:

- **CUDA 11.7** installed and properly configured (for GPU acceleration)
- **Python 3.7.9** and **Python 3.11.0** both installed
- **Visual Studio Community 2019** installed with:
  - ✅ Desktop Development with C++ workload enabled
  - ✅ Windows 11 SDK selected during setup

---

## 📁 Project Setup

### 1. Clone This GitHub Repository

Open a terminal or command prompt and run:

```bash
git clone https://github.com/your-username/3d-glb-project.git
cd 3d-glb-project
````

---

### 2. Download Model Checkpoints (Required for Inference)

* 📥 Download the pretrained model files from this Google Drive link:

  👉 [Download Models](https://drive.google.com/file/d/1CAcvtqD8XTkjr9C-6G4L12dkQVDZxQkz/view?usp=sharing)

* Once downloaded:

  * Unzip the folder.
  * You will find two subfolders:

    * `DECA_data`
    * `hairmapper_ckpts`

---

### 3. Place the Model Files Correctly

After unzipping:

* 🗂️ Copy **everything inside `DECA_data`** and paste it into:

  ```
  DECA/data/
  ```

  > ℹ️ Tip: Make sure you're pasting the **contents**, not the folder itself.

* 🗂️ Copy **everything inside `hairmapper_ckpts`** and paste it into:

  ```
  hair_mapper/HairMapper/ckpts/
  ```

---

## 📦 Python Environment Setup

You will need both Python 3.7.9 and 3.11.0 for different parts of the project.

### A. Set up Python 3.7.9 Environment

Use this to install dependencies for older models:

```bash
pip install -r requirements37.txt
```

```
Use this if your facing a error on dlib 

set CMAKE_GENERATOR=Ninja
set CMAKE_ARGS=-DCMAKE_POLICY_VERSION_MINIMUM=3.5
pip install dlib==19.24.2 --no-build-isolation
```

### B. Set up Python 3.11.0 Environment


```bash
pip install -r requirements311.txt
```

> 💡 Tip: Consider using [virtualenv](https://virtualenv.pypa.io/en/latest/) or [pyenv](https://github.com/pyenv/pyenv) to manage multiple Python versions easily.

---

### c. install blender

```
install blender 2.79
```
### .env config

```
fill out the .env file 
```

### check this folder 
```
texture/ input
Blender/ready to use model/head
hair_mapper/stylegan-encoder/aligned_images
hair_mapper/stylegan-encoder/raw_images

```

```
check for this folder sometimes git doesnt add empty folder soo it might will be removed if soo add these
```
### If you're using the .bat file make sure you change this in run_pipeline.bat to your system config

* REM ==== CONFIG (portable) ====
* set "ROOT=%~dp0"
* if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
* set "PY37=C:\Users\sanje_3wfdh8z\AppData\Local\Programs\Python\Python37\python.exe"
* set "PY311=C:\Users\sanje_3wfdh8z\AppData\Local\Programs\Python\Python311\python.exe"
* set "VCVARS=C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\VC\Auxiliary\Build\vcvars64.bat"
* set "CUDA_HOME=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.7"
* REM ===========================


## ▶️ Running the Project

### 1. Prepare Input Image

* Supported formats: `.jpg` or `.png`
* Recommended: Image should be well-lit and high resolution.

---

### 2. Start the API Server

From the project root directory, run:

```bash
uvicorn api_function:app --reload
```
* if you want to call the normal function 
or
```bash
uvicorn api_bat:app --reload
```
* if you want to call the .bat file 


* This will start a local server and print an endpoint URL in the terminal.
* The server listens for POST requests containing gender input.

---

## 📬 Testing the API

You can test it using **Postman** or any REST client.

### A. Sample Request

* **Method:** `POST`

* **URL:** `http://localhost:<your-port>/upload`


### B. Add Form Data

1. Go to the **Body** tab in Postman.
2. Select **form-data**.
3. Add the following form fields:

| Key    | Value               |
|--------|---------------------|
| gender | male (or female)     |
| file   | (Select an image file) |

- **gender**: Specify `male` or `female` (case-sensitive, lowercase).
- **file**: Select an image file from your local machine that you want to upload.

## ✅ Final Checklist

Before running, confirm that:

* [ ] CUDA 11.7 is installed and working
* [ ] Python 3.7.9 and 3.11.0 are both installed
* [ ] Visual Studio 2019 is set up with required components
* [ ] You cloned the GitHub repository
* [ ] You downloaded and placed the model files in the correct folders
* [ ] Dependencies are installed using the correct `requirements*.txt` files
* [ ] Input image is placed in `input/` folder
* [ ] API server is running (`docker_api.py`)
* [ ] You tested the endpoint with a valid JSON using Postman

---

## 🙋 Need Help?

If you face issues:

* Check for folder structure errors (e.g., content not placed properly)
* Confirm you're using the right Python version
* Check terminal output for clear errors
* Raise an issue in the GitHub repo

