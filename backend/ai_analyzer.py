# ai_analyzer.py
from openai import OpenAI
import os
from dotenv import load_dotenv
from typing import Tuple

load_dotenv(dotenv_path=".env.local")
os.environ['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY')


class ComplaintAnalyzer:
    def _init_(self):
        self.client = OpenAI()
        self.model = "gpt-4o-mini"

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
                    {"role": "system", "content": 
                        "You are an expert in analyzing customer complaints. Your task is to assess the sentiment of the complaint and provide a score between 0 and 1.\n\n"
                        "Guidelines:\n"
                        "- 0 means 'extremely negative' (e.g., frustration, anger).\n"
                        "- 0.5 means 'neutral' or mixed sentiment.\n"
                        "- 1 means 'extremely positive' (e.g., gratitude, satisfaction).\n\n"
                        "Provide varied and realistic sentiment scores by analyzing:\n"
                        "1. Emotional intensity (e.g., anger vs. calm expression).\n"
                        "2. Phrases expressing dissatisfaction (e.g., 'worst experience').\n"
                        "3. Positive words (e.g., 'thank you').\n\n"
                        "Output only a float between 0 and 1 (e.g., 0.23). Avoid default values like 0.50."},
                    {"role": "user", "content": f"Evaluate the sentiment of this complaint:\n\n{text}"}
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
                    {"role": "system", "content": 
                        "You are an expert in evaluating the urgency of customer complaints. Your task is to provide a score between 0 and 1 for urgency.\n\n"
                        "Guidelines:\n"
                        "- 0 means 'not urgent' (e.g., minor issues or low impact).\n"
                        "- 0.5 means 'moderately urgent' (e.g., general complaints or minor delays).\n"
                        "- 1 means 'extremely urgent' (e.g., critical problems impacting the user immediately).\n\n"
                        "Consider the following:\n"
                        "1. Time-critical phrases (e.g., 'immediately,' 'urgent').\n"
                        "2. Complaints about waiting or delays (e.g., 'no response for days').\n"
                        "3. Impact on user operations (e.g., 'unable to work').\n\n"
                        "Output only a float between 0 and 1 (e.g., 0.67). Avoid default values like 0.50."},
                    {"role": "user", "content": f"Evaluate the urgency of this complaint:\n\n{text}"}
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
                    {"role": "system", "content": 
                        "You are an expert in assessing politeness in customer complaints. Provide a score between 0 and 1.\n\n"
                        "Guidelines:\n"
                        "- 0 means 'extremely rude' (e.g., insults or hostile tone).\n"
                        "- 0.5 means 'neutral' (e.g., polite phrasing but frustration evident).\n"
                        "- 1 means 'extremely polite' (e.g., use of 'please,' 'thank you').\n\n"
                        "Consider the following:\n"
                        "1. Use of polite words and phrases (e.g., 'kindly,' 'please').\n"
                        "2. Avoiding harsh words (e.g., 'useless,' 'terrible').\n"
                        "3. Overall tone—distinguish politeness from frustration or dissatisfaction.\n\n"
                        "Output only a float between 0 and 1 (e.g., 0.68). Avoid default values like 0.50."},
                    {"role": "user", "content": f"Evaluate the politeness of this complaint:\n\n{text}"}
                ]
            )
            return float(completion.choices[0].message.content.strip())
        except:
            return 0.5

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
    def count_similar_complaints_with_ticket(self, complaint_data, ticket_id,ticket_id_generated,current_complain) -> list:
            try:
                # Extract the complaint descriptions and ticket IDs
                descriptions = complaint_data['complaint_descriptions']
                ticket = ticket_id['ticket_id']
                descriptions.append(current_complain)
                
                # Call the LLM with the generated prompt
                completion = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                    {
                        "role": "system", 
                        "content": f"""
                You are given a list of customer complaint descriptions and their corresponding Ticket IDs. 
                Your task is to determine how many complaints are similar to the last one in the list and identify the Ticket ID of the first similar complaint.

                Instructions:
                1. The last complaint description in the list will be the reference complaint.
                2. Compare each of the previous complaints to the reference and assess their similarity.
                3. A complaint is considered similar if it describes the same issue (e.g., slow network, poor service, etc.), uses a similar problem-solving approach, or faces similar challenges.
                4. Focus on the general meaning and nature of the problem, not the exact wording or phrasing.
                5. Identify the Ticket ID of the *first complaint* that is similar to the last complaint.
                6. If no complaints are similar to the last one:
                    - Return a count of 0.
                    - Return the Ticket ID as {ticket_id_generated}.

                Output format: 
                <Count of similar complaints>,<Ticket ID>
                (e.g., "3,TICKET1234" or "0,LASTTICKET1234")
                """
                    },
                    {
                        "role": "user", 
                        "content": f"Count how many complaints are similar to the last one. Complaint Descriptions: \n\n{descriptions}\n\nTicket IDs: {ticket}"
                    }
                ]
                )
                
                # Extract and parse the LLM response
                response = completion.choices[0].message.content.strip()
                count, first_ticket_id = response.split(',')

                # Return the count and first ticket ID as a dictionary
                return [int(count), str(first_ticket_id)]
            
            except Exception as e:
                # Handle any errors or failures
                print(f"Error: {e}")
                return [0,"jT4^1b6s7FwMZ8#9lhRVpKtYz)w0uOeXL3qS"]