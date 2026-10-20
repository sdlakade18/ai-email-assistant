from abc import ABC, abstractmethod
from schemas import EmailClassification

class LLMProvider(ABC):
    
    @abstractmethod
    def classify_email(self, subject: str, body: str) -> EmailClassification:
        raise  NotImplementedError
        
