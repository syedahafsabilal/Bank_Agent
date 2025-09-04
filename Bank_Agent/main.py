""" Bank Agent"""

from agents import (
    Agent,
    Runner,
    OpenAIChatCompletionsModel,
    AsyncOpenAI,
    RunConfig,
    Runner,
    RunContextWrapper,
    FunctionTool, 
    InputGuardrail,
    OutputGuardrail
    )
import os
import re
import asyncio

from dotenv import load_dotenv

load_dotenv()

gemini_api_key = os.getenv("GEMINI_API_KEY")

external_client = AsyncOpenAI(
    api_key= gemini_api_key,
    base_url ="https://generativelanguage.googleapis.com/v1beta/openai/"
)

model = OpenAIChatCompletionsModel(
    model ="gemini-2.0-flash",
    openai_client = external_client
)

config = RunConfig(
    model=model,
    model_provider = external_client,
    tracing_disabled = True

)


def check_balance_fn(account_number: str) -> str:
    return f"The balance of account {account_number} is $1000"

check_balance_tool = FunctionTool(
    name="check_balance",  # <--- REQUIRED
    description="Check the balance of a bank account",
    params_json_schema={
        "type": "object",
        "properties": {
            "account_number": {"type": "string"}
        },
        "required": ["account_number"]
    },
    on_invoke_tool=check_balance_fn
)




async def input_guard_fn(ctx, agent, user_input:str):
    valid = True
    reason = "Valid input"

    if not user_input.strip():
        valid = False
        reason = "Input cannot be empty"
    elif re.search(r'\b(pin|password|card|ssn)\b', user_input, re.I):
        valid = False
        reason = "Sensitive information is not allowed"

    return GuardrailFunctionOutput(
        output_info={"valid": valid, "reason": reason},
        guardrail_function=input_guard_fn
    )
## u copied this girl##
class GuardrailFunctionOutput:
    def __init__(self, output_info=None, guardrail_function=None, tripwire_triggered=False):
        self.output_info = output_info
        self.guardrail_function = guardrail_function
        self.tripwire_triggered = tripwire_triggered

class InputGuardrail:
    def __init__(self, name=None, guardrail_function=None):
        self.name = name
        self.guardrail_function = guardrail_function



input_guard_obj = InputGuardrail(
    name="UserInputGuard",
    guardrail_function=input_guard_fn
)


async def output_guard_fn(ctx, agent, response):
    if response is None:
        response = ""
    response = re.sub(r'\b(pin|password|card|ssn)\b', "[REDACTED]", response, flags=re.I)
    return GuardrailFunctionOutput(
        output_info={"response": response},
        tripwire_triggered=False
    )
   
output_guard_obj = InputGuardrail(
    name="OutputGuard",
    guardrail_function=output_guard_fn
)
class RefundTracker:
    def __init__(self):
        self.awaiting_details = False
        self.details = {"transaction_id": None, "date": None, "amount":None, "reason": None}
    def parse_input(self, query: str):
        tid = re.search(r"\b\d{2,}\b", query)
        date = re.search(r"\b\d{1,2}\s?[a-zA-Z]+\b", query)
        amount_match = re.findall(r"\$?(\d+)", query)
       
        if tid:
            self.details["transaction_id"] = tid.group()
        if date:
            self.details["date"] = date.group()
        if amount_match:
            self.details["amount"] = amount_match[-1]

        self.reasons_map = {
            "1": "Item not received",
            "2": "Duplicate charge",
            "3": "Wrong item delivered",
            "4": "Changed my mind",
            "5": "Other"
         }
        self.reason_map = {
            "item not received":"Item not received",
            "duplicate charge":  "Duplicate charge",
            "wrong item delivered":  "Wrong item delivered",
            "changed my mind":"Changed my mind",
            "other": "Other",
            "something else": "Other",
            "difficult reason": "Other"   
         }
       
        for key, val in self.reasons_map.items():
            if key in query.split():
               self.details["reason"] = val
               break

        if not self.details["reason"]:
            q_lower = query.lower()
            for phase, standard in self.reason_map.items():
                if phase in q_lower:
                   self.details["reason"] = standard
                   break
    def is_complete(self):
        return all(self.details.values())
refund_tracker = RefundTracker()

class BookingTracker:
    def __init__(self):
        self.awaiting_day = False
        self.day = None

    def parse_input(self, query:str):
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        for day in days:
            if day in query.lower():
                self.day = day
                self.awaiting_day = False
                return True
        return False

booking_tracker = BookingTracker()

booking_agent = Agent(
    name="Booking Agent",
    instructions="Handle booking queries safely",
    input_guardrails=[input_guard_obj],
    output_guardrails=[output_guard_obj]
)
refund_agent = Agent(
    name="Refund Agent",
    instructions="Handle refund requests safely",
    input_guardrails=[input_guard_obj],
    output_guardrails=[output_guard_obj]

)
banking_agent = Agent(
    name="Banking Agent",
    instructions="Handle balances, transfers, and general questions safely",
    input_guardrails=[input_guard_obj],
    output_guardrails=[output_guard_obj]
)
triage_agent = Agent(
    name="Triage Agent",
    instructions="Route user queries to the correct agent: banking, refund, booking",
    input_guardrails=[input_guard_obj],
    output_guardrails=[output_guard_obj],
    handoffs=[booking_agent, banking_agent, refund_agent]
)
if __name__ == "__main__":
    print("~~~~~~~~ Welcome to the Bank Assistant ~~~~~~")
    name = input("Enter your name:")
    account_id = input("Enter your account ID:")

    while True:
        query = input("Enter your query:").strip()
        guard_result = asyncio.run(input_guard_fn(None, None, query))
        if not guard_result.output_info["valid"]:
           print(f"Invalid input: {guard_result.output_info['reason']}")
           continue

        if query.lower() == "quit":
           print(f"Goodbye, {name}!")
           break

        if "refund" in query.lower() or refund_tracker.awaiting_details:
            refund_tracker.awaiting_details = True
            refund_tracker.parse_input(query)

            missing = [k for k, v in refund_tracker.details.items() if not v]
            if missing:
                print(f"Hello {name}, to process your refund, please provide:")
                if "transaction_id" in missing:
                    print("*transaction ID*")
                if "date" in missing:
                    print("*Date of purchase*")
                if "amount" in missing:
                    print("*Amount of the purchase*")
                if "reason" in missing:
                    print("*Reason for refund (choose one or type your reason):")
                    print(" 1. Items not received")
                    print(" 2. Duplicate charge")
                    print(" 3. Wrong item delivered")
                    print(" 4. Changed my mind")
                    print(" 5. Other")
            else:
                response = (f"Refund successful for Transaction ID {refund_tracker.details['transaction_id']},"
                            f"Date {refund_tracker.details['date']}, Amount ${refund_tracker.details['amount']},"
                            f"Reason: {refund_tracker.details['reason']}.")
                guarded_response = asyncio.run(output_guard_fn(None, None, response))
                refund_tracker.details = {"transaction_id": None, "date": None, "amount": None, "reason": None}
                print(guarded_response.output_info["response"])
                refund_tracker.awaiting_details = False
            continue
        if "book" in query.lower() or booking_tracker.awaiting_day:
            booking_tracker.awaiting_day = True
            if booking_tracker.parse_input(query):
                print(f" Appointment booked on {booking_tracker.day.capitalize()} for {name}!")
                booking_tracker.day = None
                booking_tracker.awaiting_day = False
            else:
                print(f"Hello {name}, which day would you like to book your appointment?(e.g, Monday, Tuesday..)")
            continue

        if "balance" in query.lower():
            print(f"Hello {name}, your balance is $1000 (simulated).")
        else:
            print(f"Hello {name}, I can help you with balance inquiries, refunds, or bookings."
                  f"Please mention what you would like to do?")