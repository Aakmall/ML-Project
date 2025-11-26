import os
from app import calculate_hpl, get_ai_response

# Mock API Key for testing if not set (though app.py has defaults)
# We rely on the defaults in app.py or system env vars

print("=== TEST 1: HPL Calculator ===")
# Test case 1: Valid date
test_date = "01-01-2024"
print(f"Input: !hpl {test_date}")
print(calculate_hpl(test_date))
print("-" * 30)

# Test case 2: Invalid date
invalid_date = "32-01-2024"
print(f"Input: !hpl {invalid_date}")
print(calculate_hpl(invalid_date))
print("-" * 30)

print("\n=== TEST 2: AI Response (PregnaBot Persona) ===")
# Test case 3: General pregnancy question
question = "Apa makanan yang bagus untuk trimester pertama?"
print(f"Question: {question}")
try:
    response = get_ai_response(question)
    print(f"Answer:\n{response}")
except Exception as e:
    print(f"Error testing AI: {e}")

print("\n=== TEST 3: Greeting ===")
greeting = "Halo PregnaBot!"
print(f"Greeting: {greeting}")
try:
    response = get_ai_response(greeting)
    print(f"Answer:\n{response}")
except Exception as e:
    print(f"Error testing AI: {e}")
