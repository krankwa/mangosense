from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from django.http import JsonResponse
from django.conf import settings
from django.utils import timezone
from PIL import Image
import numpy as np
import tensorflow as tf
import gc

# ML Configuration
IMG_SIZE = (224, 224)
class_names = [
    'Anthracnose', 'Bacterial Canker', 'Cutting Weevil', 'Die Back', 'Gall Midge',
    'Healthy', 'Powdery Mildew', 'Sooty Mold', 'Black Mold Rot', 'Stem End Rot'
]

# Treatment suggestions
treatment_suggestions = {
    'Anthracnose': 'The diseased twigs should be pruned and burnt along with fallen leaves. Spraying twice with Carbendazim (Bavistin 0.1%) at 15 days interval during flowering controls blossom infection.',
    'Bacterial Canker': 'Three sprays of Streptocycline (0.01%) or Agrimycin-100 (0.01%) after first visual symptom at 10 day intervals are effective in controlling the disease.',
    'Cutting Weevil': 'Use recommended insecticides and remove infested plant material.',
    'Die Back': 'Pruning of the diseased twigs 2-3 inches below the affected portion and spraying Copper Oxychloride (0.3%) on infected trees controls the disease.',
    'Gall Midge': 'Remove and destroy infested fruits; use appropriate insecticides.',
    'Healthy': 'No treatment needed. Maintain good agricultural practices.',
    'Powdery Mildew': 'Alternate spraying of Wettable sulphur 0.2 per cent at 15 days interval are recommended for effective control of the disease.',
    'Sooty Mold': 'Pruning of affected branches and their prompt destruction followed by spraying of Wettasulf (0.2%) helps to control the disease.'
}

# Load ML model
try:
    model_path = str(settings.MODEL_PATH)
    model = tf.keras.models.load_model(model_path)
except Exception as e:
    model = None
    print(f"Error loading model: {e}")

def validate_mobile_image(image_file):
    """Validate image uploaded from mobile app"""
    # Check file size (max 5MB for mobile)
    if image_file.size > 5 * 1024 * 1024:
        return False, "Image size must be less than 5MB"
    
    # Check file type - common mobile formats
    allowed_types = ['image/jpeg', 'image/jpg', 'image/png']
    if image_file.content_type not in allowed_types:
        return False, "Only JPEG and PNG images are allowed"
    
    try:
        # Verify it's a valid image
        img = Image.open(image_file)
        img.verify()
        return True, "Valid image"
    except Exception:
        return False, "Invalid image file"

def preprocess_image(image_file):
    """Preprocess image for ML model prediction"""
    img = Image.open(image_file).convert('RGB')
    img = img.resize(IMG_SIZE)
    img_array = np.array(img)
    img.close()
    img_array = tf.keras.applications.efficientnet.preprocess_input(img_array)
    img_array = np.expand_dims(img_array, axis=0)
    return img_array

@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def predict_image(request):
    """Handle image prediction from mobile Ionic app"""
    if 'image' not in request.FILES:
        return JsonResponse({
            'success': False,
            'error': 'No image uploaded'
        }, status=400)
    
    try:
        image_file = request.FILES['image']
        
        # Validate mobile image
        is_valid, validation_message = validate_mobile_image(image_file)
        if not is_valid:
            return JsonResponse({
                'success': False,
                'error': validation_message
            }, status=400)
        
        # Check if model is loaded
        if model is None:
            return JsonResponse({
                'success': False,
                'error': 'ML model not loaded properly'
            }, status=500)
        
        # Process image for prediction
        img_array = preprocess_image(image_file)
        prediction = model.predict(img_array)
        
        # Get top 3 predictions
        top_3_indices = np.argsort(prediction[0])[-3:][::-1]
        
        top_3_predictions = []
        for i, idx in enumerate(top_3_indices):
            confidence = float(prediction[0][idx]) * 100
            disease_name = class_names[idx] if idx < len(class_names) else f"Unknown_{idx}"
            
            top_3_predictions.append({
                'rank': i + 1,
                'disease': disease_name,
                'confidence': round(confidence, 2),
                'confidence_formatted': f"{confidence:.2f}%",
                'treatment': treatment_suggestions.get(disease_name, "No treatment information available.")
            })
        
        # Primary prediction (highest confidence)
        primary_prediction = top_3_predictions[0]
        
        # Clear memory
        gc.collect()
        
        # Return mobile-optimized response with top 3 predictions
        response_data = {
            'success': True,
            'primary_prediction': {
                'disease': primary_prediction['disease'],
                'confidence': primary_prediction['confidence_formatted'],
                'confidence_score': primary_prediction['confidence'],
                'treatment': primary_prediction['treatment']
            },
            'top_3_predictions': top_3_predictions,
            'prediction_summary': {
                'most_likely': primary_prediction['disease'],
                'confidence_level': 'High' if primary_prediction['confidence'] > 80 else 'Medium' if primary_prediction['confidence'] > 60 else 'Low',
                'total_diseases_checked': len(class_names)
            },
            'timestamp': timezone.now().isoformat(),
            'debug_info': {
                'model_loaded': model is not None,
                'class_names_count': len(class_names),
                'image_size': img_array.shape
            }
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Prediction failed: {str(e)}'
        }, status=500)

@api_view(['GET'])
def test_model_status(request):
    """Test endpoint to check if model and class names are loaded properly"""
    try:
        return JsonResponse({
            'success': True,
            'model_status': {
                'model_loaded': model is not None,
                'model_path': str(settings.MODEL_PATH) if hasattr(settings, 'MODEL_PATH') else 'Not set',
                'class_names': class_names,
                'class_names_count': len(class_names),
                'treatment_suggestions_count': len(treatment_suggestions)
            },
            'available_diseases': class_names,
            'img_size': IMG_SIZE
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)