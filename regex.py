import re
text = "Contact us at support@example.com or sales@company.org for help."
# Find all email addresses
emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
text)
print("Emails found:", emails)
# ['support@example.com', 'sales@company.org']
# Find all words starting with capital letter
capitals = re.findall(r'\b[A-Z][a-z]+', text)
print("Capitalized words:", capitals)
# Replace phone numbers with [PHONE]
text2 = "Call me at 9876543210 or 9123456789"
cleaned = re.sub(r'\b\d{10}\b', '[PHONE]', text2)
print(cleaned) # Call me at [PHONE] or [PHONE]
