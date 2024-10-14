import configparser
import google.generativeai as genai

if __name__ == "__main__":
    # Get API Key
    cfg_file = configparser.ConfigParser()
    cfg_file.read("config\setup.ini")
    api_key = cfg_file["GOOGLE_AI"]["api_key"]

    # Configure API Key
    genai.configure(api_key=api_key)

    # Model configuration
    model_config = {
        "temperature": 1,
        "top_p": 0.99,
        "top_k": 0,
        "max_output_tokens": 4096,
    }

    model = genai.GenerativeModel(
        "gemini-1.5-flash-latest", generation_config=model_config
    )

    response = model.generate_content("President of USA is")
    print(response.text)
