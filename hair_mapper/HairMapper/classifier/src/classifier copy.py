from classifier import Classifier  # assuming your main file defines this
from config import Config
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Load configuration
config = Config('C:\\Users\\sanje\\OneDrive\\Desktop\\hair_mapper\\HairMapper\\classifier\\config.yml')  # or pass config object directly
classifier = Classifier(config, name='gender_classification')
classifier.load()

# Predict
output = classifier.process('C:\\Users\\sanje\\OneDrive\\Desktop\\hair_mapper\\HairMapper\\test_data\\origin\\vineesh_01.png')  # path to your test image
gender = 'Female' if output[0][1] > output[0][0] else 'Male'
print('Predicted Gender:', gender)
