# ai_analyzer.py
from openai import OpenAI
import os
from dotenv import load_dotenv
from typing import Tuple
import groq
import random
import string

load_dotenv(dotenv_path=".env.local")
os.environ['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY')
os.environ['GROQ_API_KEY'] = os.getenv('GROQ_API_KEY')


class ComplaintAnalyzer:
    def __init__(self):
        self.client = groq.Groq()
        self.model = "gemma2-9b-it"

    def analyze_complaint(self, complaint_text: str, past_complaints: int) -> Tuple[float, float, float, float]:
        sentiment = self._analyze_sentiment(complaint_text)
        urgency = self._evaluate_urgency(complaint_text)
        politeness = self._assess_politeness(complaint_text)
        priority = self._calculate_priority(sentiment, urgency, politeness, past_complaints)
        return sentiment, urgency, politeness, priority

    def _analyze_sentiment(self, text: str) -> float:
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert in analyzing customer complaints. "
                            "Your task is to assess the sentiment of the complaint and provide a score between 0 and 1.\n\n"
                            "Guidelines:\n"
                            "- 0 means 'extremely negative' (e.g., frustration, anger).\n"
                            "- 0.5 means 'neutral' or mixed sentiment.\n"
                            "- 1 means 'extremely positive' (e.g., gratitude, satisfaction).\n\n"
                            "Provide varied and realistic sentiment scores by analyzing:\n"
                            "1. Emotional intensity (e.g., anger vs. calm expression).\n"
                            "2. Phrases expressing dissatisfaction (e.g., 'worst experience').\n"
                            "3. Positive words (e.g., 'thank you').\n\n"
                            "Output only a float between 0 and 1 (e.g., 0.23). Avoid default values like 0.50."
                        )
                    },
                    {
                        "role": "user",
                        "content": f"Evaluate the sentiment of this complaint:\n\n{text}"
                    }
                ]
            )
            return float(completion.choices[0].message.content.strip())
        except:
            return 0.5

    def _evaluate_urgency(self, text: str) -> float:
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert in evaluating the urgency of customer complaints. "
                            "Your task is to provide a score between 0 and 1 for urgency.\n\n"
                            "Guidelines:\n"
                            "- 0 means 'not urgent' (e.g., minor issues or low impact).\n"
                            "- 0.5 means 'moderately urgent' (e.g., general complaints or minor delays).\n"
                            "- 1 means 'extremely urgent' (e.g., critical problems impacting the user immediately).\n\n"
                            "Consider the following:\n"
                            "1. Time-critical phrases (e.g., 'immediately,' 'urgent').\n"
                            "2. Complaints about waiting or delays (e.g., 'no response for days').\n"
                            "3. Impact on user operations (e.g., 'unable to work').\n\n"
                            "Output only a float between 0 and 1 (e.g., 0.67). Avoid default values like 0.50."
                        )
                    },
                    {
                        "role": "user",
                        "content": f"Evaluate the urgency of this complaint:\n\n{text}"
                    }
                ]
            )
            return float(completion.choices[0].message.content.strip())
        except:
            return 0.5

    def _assess_politeness(self, text: str) -> float:
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert in assessing politeness in customer complaints. Provide a score between 0 and 1.\n\n"
                            "Guidelines:\n"
                            "- 0 means 'extremely rude' (e.g., insults or hostile tone).\n"
                            "- 0.5 means 'neutral' (e.g., polite phrasing but frustration evident).\n"
                            "- 1 means 'extremely polite' (e.g., use of 'please,' 'thank you').\n\n"
                            "Consider the following:\n"
                            "1. Use of polite words and phrases (e.g., 'kindly,' 'please').\n"
                            "2. Avoiding harsh words (e.g., 'useless,' 'terrible').\n"
                            "3. Overall tone—distinguish politeness from frustration or dissatisfaction.\n\n"
                            "Output only a float between 0 and 1 (e.g., 0.68). Avoid default values like 0.50."
                        )
                    },
                    {
                        "role": "user",
                        "content": f"Evaluate the politeness of this complaint:\n\n{text}"
                    }
                ]
            )
            return float(completion.choices[0].message.content.strip())
        except:
            return 0.5

    def get_complaint_category(self, complaint: str):
        response = self.client.chat.completions.create(
            model=self.model,  # Ensure the model name is correct
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are given a task to categorize the complaints of a Broadband company Customer Care into: \n"
                        "1. Technical Support: return 0\n"
                        "2. Billing: return 1\n"
                        "3. New Connection: return 2\n"
                        "4. Added Service and Bundle offers: return 3\n"
                        "Return only the number corresponding to the category. "
                        "If I get anything else, I will terminate you."
                    )
                },
                {
                    "role": "user",
                    "content": complaint  # Use complaint as a string, not inside {}
                }
            ],
            temperature=0.7,
            max_tokens=5  # Limit response length as we need only a number
        )

        result = response.choices[0].message.content.strip()
        if result == "0":
            result = "Technical Support"
        elif result == "1":
            result = "Billing"
        elif result == "2":
            result = "New Connection"
        elif result == "3":
            result = "Added Service and Bundle offers"
        return result

    def _calculate_priority(self, sentiment: float, urgency: float, politeness: float, past_complaints: int) -> float:
        # Adjust weights for better differentiation
        urgency_weight = 0.35
        politeness_weight = 0.25
        sentiment_weight = 0.25
        past_complaints_weight = 0.15

        # Non-linear penalty for extreme values
        adjusted_urgency = urgency ** 0.8  # Slightly reduce the impact of very high urgency
        adjusted_past_complaints = min(1.0, past_complaints * 0.1)  # Cap the impact of past complaints

        # Calculate priority using the refined weights
        priority = (
            (adjusted_urgency * urgency_weight) +
            ((1 - politeness) * politeness_weight) +
            ((1 - sentiment) * sentiment_weight) +
            adjusted_past_complaints
        )

        return min(1.0, max(0.0, priority))  # Ensure the result is between 0 and 1

    def count_similar_complaints_with_ticket(self, complaint_data, ticket_id, ticket_id_generated, current_complain) -> list:
        try:
            # Extract the complaint descriptions and ticket IDs from past complaints
            descriptions = complaint_data['complaint_descriptions']
            past_ticket_ids = ticket_id['ticket_id']  # List of previous ticket IDs

            # Prepare the prompt for LLM
            system_prompt = f"""
You are given a list of customer complaint descriptions and their corresponding Ticket IDs. 
Your task is to determine how many complaints are similar to the reference one in the list and identify the Ticket ID of the first similar complaint.

Instructions:
1. This complaint description: {current_complain} will be the reference complaint.
2. Compare each of the previous complaints to the reference and assess their similarity.
3. A complaint is considered similar if it describes the same issue (e.g., slow network, poor service, etc.), uses a similar problem-solving approach, or faces similar challenges.
4. Focus on the general meaning and nature of the problem, not the exact wording or phrasing.
5. Identify the Ticket ID of the *first complaint* that is similar to the reference complaint.
6. If no complaints are similar to this complaint: {current_complain}:
   - Return a count of 0.
   - Return the Ticket ID as {ticket_id_generated}.

Output format: 
<Count of similar complaints>,<Ticket ID>
(e.g., "3,TICKET1234" or "0,LASTTICKET1234")
"""
            # Call the LLM with the generated prompt
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": system_prompt
                    },
                    {
                        "role": "user", 
                        "content": f"Count how many complaints are similar to the reference complaint. Complaint Descriptions: \n\n{descriptions}\n\nTicket IDs: {past_ticket_ids}"
                    }
                ]
            )

            # Extract and parse the LLM response
            response = completion.choices[0].message.content.strip()
            count, first_ticket_id = response.split(',')

            # Return the count and first ticket ID as a list
            return [int(count), str(first_ticket_id)]

        except Exception as e:
            characters = string.ascii_letters + string.digits
            random_string = ''.join(random.choice(characters) for _ in range(72))
            # Handle any errors or failures
            print(f"Error: {e}")
            return [0, "jT4^1b6s7FwMZ8#9lhRVpKtYz)w0uOeXL3qS"]
