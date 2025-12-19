import anthropic
import yfinance as yf
import os
import finnhub
from dotenv import load_dotenv


#load env variables
load_dotenv()
ANTHROPIC_API_KEY= os.getenv("ANTHROPIC_API_KEY")
FINNHUB_API_KEY=os.getenv("FINNHUB_API_KEY")

client = anthropic.Anthropic()
finnhub_client = finnhub.Client(api_key=FINNHUB_API_KEY)

##### PROMPTS #########
system_prompt = """
You are a stock market analyst. Analyze the provided stock data and give 
a recommendation.

Respond in this format:

VOTE: [BUY, HOLD, or SELL]
CONFIDENCE: [0-100]%
REASONING: [2-3 sentences explaining why]
"""


def interact(question:str) -> str:
    message = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=500,
    messages=[
        {
            "role": "user",
            "content": question
        }
    ]
    )
    return message

def interact_agent(question:str) -> str:
    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=500,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": question
            }
        ]
    )
    return message

def fetch_price(symbol:str) -> str:
    quote = finnhub_client.quote(symbol)
    #current_price = quote["c"]
    return quote

def fetch_news(symbol:str) -> str:
    return finnhub_client.general_news("General", min_id=0)

def fetch_insider(symbol:str) -> str:
    return finnhub_client.stock_insider_transactions(symbol)

def analyse_symbol(symbol:str) -> str:
    quote = fetch_price(symbol)
    user_prompt = f"""
Analyze {symbol} stock:

Current Price: ${quote['c']:.2f}
Previous Close: ${quote['pc']:.2f}
Change: ${quote['d']:+.2f} ({quote['dp']:+.2f}%)

Today's Trading:
- Open: ${quote['o']:.2f}
- High: ${quote['h']:.2f}
- Low: ${quote['l']:.2f}

Should we buy, hold, or sell this stock? Explain your reasoning.
"""
    return interact_agent(user_prompt)

def test():
    question_counter = 0
    MAX_QUESTION = 5


    print(finnhub_client.quote("AAPL"))
    while question_counter < MAX_QUESTION:
        user_input = str(input("User: "))
        output = interact(user_input)
        print("Assistant: ", output)



def main():
    print("############ Ongoing process ##############")
    symbol = "AAPL"
    info = []
    info.append("Here is a list of information about AAPL without any format")
    
    info.append(fetch_price(symbol))
    info.append(fetch_news(symbol))
    info.append(fetch_insider(symbol))

    for item in info:
        print(item)
    



if __name__ == "__main__":
    main()