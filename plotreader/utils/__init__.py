from typing import Union, Any
import base64
import io


def image_to_base64(image: Union[str, Any]):

    if isinstance(image, str):
        with open(image, "rb") as image_file:
            binary_data = image_file.read()
        
    else:
        # image = image.convert('RGB')
        image_data = io.BytesIO()
        image.save(image_data, format=image.format.lower(), optimize=True, quality=100)
        image_data.seek(0)
        binary_data = image_data.getvalue()
    
    
    base_64_encoded_data = base64.b64encode(binary_data)
    return base_64_encoded_data.decode('utf-8')