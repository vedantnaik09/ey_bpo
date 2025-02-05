# ai_analyzer.py
from openai import OpenAI
import os
from typing import Tuple
from dotenv import load_dotenv
load_dotenv('.env.local')
os.environ['OPENAI_API_KEY']=os.getenv('OPENAI_API_KEY')


class ComplaintAnalyzer:
    def __init__(self):
        self.client = OpenAI()
        self.model = "gpt-4o-mini"

    def analyze_complaint(self, complaint_text: str) -> Tuple[float, float, float, float]:
        sentiment = self._analyze_sentiment(complaint_text)
        urgency = self._evaluate_urgency(complaint_text)
        politeness = self._assess_politeness(complaint_text)
        priority = self._calculate_priority(sentiment, urgency, politeness)
        return sentiment, urgency, politeness, priority

    def _analyze_sentiment(self, text: str) -> float:
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a sentiment analyzer."},
                    {"role": "user", "content": f"Rate the sentiment (0 to 1):\n\n{text}"}
                ]
            )
            return float(completion.choices[0].message.content)
        except:
            return 0.5

    def _evaluate_urgency(self, text: str) -> float:
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an urgency evaluator."},
                    {"role": "user", "content": f"Rate the urgency (0 to 1):\n\n{text}"}
                ]
            )
            return float(completion.choices[0].message.content)
        except:
            return 0.5

    def _assess_politeness(self, text: str) -> float:
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a politeness assessor."},
                    {"role": "user", "content": f"Rate the politeness (0 to 1):\n\n{text}"}
                ]
            )
            return float(completion.choices[0].message.content)
        except:
            return 0.5

    def _calculate_priority(self, sentiment: float, urgency: float, politeness: float) -> float:
        return (sentiment * 0.5) + (urgency * 0.3) + ((1 - politeness) * 0.2)
