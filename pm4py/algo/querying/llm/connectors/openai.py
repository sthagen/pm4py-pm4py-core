from enum import Enum
from pm4py.util import exec_utils
from typing import Optional, Dict, Any
import base64
from pm4py.util import constants


class Parameters(Enum):
    API_URL = "api_url"
    API_KEY = "api_key"
    OPENAI_MODEL = "openai_model"
    IMAGE_PATH = "image_path"


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def apply(prompt: str, parameters: Optional[Dict[Any, Any]] = None) -> str:
    import requests

    if parameters is None:
        parameters = {}

    image_path = exec_utils.get_param_value(Parameters.IMAGE_PATH, parameters, None)
    api_key = exec_utils.get_param_value(Parameters.API_KEY, parameters, constants.OPENAI_API_KEY)
    api_url = exec_utils.get_param_value(Parameters.API_URL, parameters, None)
    simple_content_specification = image_path is None

    if api_url is None:
        api_url = constants.OPENAI_API_URL
    else:
        if not api_url.endswith("/"):
            api_url += "/"

    model = exec_utils.get_param_value(Parameters.OPENAI_MODEL, parameters,
                                       constants.OPENAI_DEFAULT_MODEL if image_path is None else constants.OPENAI_DEFAULT_VISION_MODEL)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    messages = []
    if simple_content_specification:
        messages.append({"role": "user", "content": prompt})
    else:
        messages.append({"role": "user", "content": [{"type": "text", "text": prompt}]})

    payload = {
        "model": model
    }

    if image_path is not None:
        base64_image = encode_image(image_path)
        messages[0]["content"].append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image} "}})
        payload["max_tokens"] = 4096

    payload["messages"] = messages

    response = requests.post(api_url+"chat/completions", headers=headers, json=payload).json()

    if "error" in response:
        # raise an exception when the request fails, with the provided message
        raise Exception(response["error"]["message"])

    return response["choices"][0]["message"]["content"]
