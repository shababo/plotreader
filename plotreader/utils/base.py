from typing import List, Dict
from requests import Response
from PIL.Image import Image

import anthropic
from anthropic.types.message import Message

from plotreader.utils.document import image_to_base64


class BasicAnthropicAgent:

    def __init__(
            self,
            model: str,
            max_tokens: int = 2048,
            temperature: float = 0.,
            system_prompt: str = None,
    ):
        
        self._model = model
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._system_prompt = system_prompt or ""

        self._api = anthropic.Anthropic()


    def message(self, prompt: str, images: List[Image]) -> Message:

        return self._api.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            temperature=self._temperature,
            system=self._system_prompt,
            messages=[self._format_message(prompt, images)]
        )

    def _format_message(self, text: str, images: List[Image]) -> Dict:
        
        content = [
                {
                    "type": "text",
                    "text": text
                },
                
            ]
        for image in images:
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": f"image/{image.format.lower()}",
                        "data": image_to_base64(image)
                    }
                }
            )
        return {
                    "role": "user",
                    "content": content
                }