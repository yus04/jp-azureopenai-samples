import os
import time
from azure.identity import DefaultAzureCredential
from azure.core.credentials import AccessToken
from openai import AzureOpenAI
from core.modelhelper import get_gpt_model, get_gpt_models

AZURE_OPENAI_SERVICE = os.environ.get("AZURE_OPENAI_SERVICE")
AZURE_OPENAI_API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION")
API_MANAGEMENT_ENDPOINT = os.environ.get("API_MANAGEMENT_ENDPOINT")
ENTRA_CLIENT_ID = os.environ.get("ENTRA_CLIENT_ID")
USE_API_MANAGEMENT = True if os.environ.get("USE_API_MANAGEMENT").lower() == "true" else False


class AzureOpenAiClientHelper():
    def __init__(self, azure_credential: DefaultAzureCredential):
        self.azure_credential = azure_credential
        self.aoai_token = self._new_aoai_token()
        self.aoai_clients = {}
        self.gpt_models = get_gpt_models()
        self.one_minute = 60

    def _init_clients(self) -> None:
        self.aoai_clients = {}

    def get_aoai_clients(self) -> dict:
        self._init_clients()
        for model_name in list(self.gpt_models.keys()):
            aoai_client = self._get_client(model_name)
            aoai_client = self._set_apim_token(aoai_client)
            self.aoai_clients[model_name] = aoai_client
        return self.aoai_clients

    def _get_client(self, model_name: str) -> AzureOpenAI:
        model_deployment = get_gpt_model(model_name).get("deployment")
        api_management_url = API_MANAGEMENT_ENDPOINT + f"/deployments/{model_deployment}/chat/completions?api-version={AZURE_OPENAI_API_VERSION}"
        azure_endpoint = f"https://{AZURE_OPENAI_SERVICE}.openai.azure.com" if not USE_API_MANAGEMENT else api_management_url
        aoai_client = AzureOpenAI(
            azure_endpoint = azure_endpoint,
            api_version=AZURE_OPENAI_API_VERSION,
            api_key = self.aoai_token.token
        )
        return aoai_client

    def update_aoai_token(self) -> dict:
        if self.aoai_token.expires_on - self.one_minute < int(time.time()):
            for model_name, aoai_client in self.aoai_clients.items():
                new_aoai_token = self._new_aoai_token()
                aoai_client.api_key = new_aoai_token.token
                aoai_client = self._set_apim_token(aoai_client)
                self.aoai_clients[model_name] = aoai_client
        return self.aoai_clients

    def _set_apim_token(self, aoai_client: AzureOpenAI) -> AzureOpenAI:
        return self.__set_apim_token(aoai_client) if USE_API_MANAGEMENT else aoai_client

    def __set_apim_token(self, aoai_client: AzureOpenAI) -> AzureOpenAI:
        apim_token = self._new_apim_token()
        aoai_client._azure_ad_token = apim_token.token
        return aoai_client
    
    def _new_apim_token(self) -> AccessToken:
        return self.azure_credential.get_token(f"{ENTRA_CLIENT_ID}/.default")
    
    def _new_aoai_token(self) -> AccessToken:
        return self.azure_credential.get_token("https://cognitiveservices.azure.com/.default")
