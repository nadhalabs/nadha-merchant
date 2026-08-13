from typing import Protocol
class AIProvider(Protocol):
    def generate_business_answer(self,context:dict,question:str,language:str)->dict:...
class UnconfiguredProvider:
    name="unconfigured"
    def generate_business_answer(self,context:dict,question:str,language:str)->dict:return {"available":False,"message":"Nadha AI isn't configured yet."}
def provider()->AIProvider:return UnconfiguredProvider()
