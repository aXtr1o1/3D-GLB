import os
import sys
import torch
from torch import nn
import numpy as np

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try to load the necessary DECA components
try:
    from decalib.deca import DECA
    from decalib.utils.config import cfg as deca_cfg
    print("Successfully imported DECA modules")
except Exception as e:
    print(f"Error importing DECA modules: {e}")
    sys.exit(1)

# Configuration
device = 'cpu'

try:
    print("Setting up DECA configuration...")
    # Get the model path directly from the config
    model_path = os.path.join(deca_cfg.deca_dir, 'data', 'deca_model.tar')
    print(f"Model path from config: {model_path}")
    
    # Print some config values
    print(f"DECA directory: {deca_cfg.deca_dir}")
    print(f"Using device: {device}")
    
    # Initialize DECA step by step
    print("Creating FLAME decoder...")
    
    # Attempt to load the model directly first
    print(f"Testing direct model loading...")
    checkpoint = torch.load(model_path, map_location=device)
    print("Direct model loading successful!")
    print(f"Checkpoint keys: {list(checkpoint.keys())}")
    
    # Now try the full DECA initialization
    print("Initializing full DECA...")
    deca = DECA(config=deca_cfg, device=device)
    print("DECA initialization successful!")
    
    print("Test completed successfully!")
except Exception as e:
    print(f"Error during test: {e}")
    import traceback
    traceback.print_exc()