ZERO_SHOT_PROMPT = '''
CLASSIFY the ticket below into one of: billing, delivery, technical, fraud.
Return JSON only in the format:
{"category": "...", "reason": "..."}
Only use the ticket text provided. Do not include extra explanation.
'''

FEW_SHOT_PROMPT = '''
CLASSIFY the ticket below into one of: billing, delivery, technical, fraud.
Return JSON only in the format:
{"category": "...", "reason": "..."}
EXAMPLES:
1. Ticket: 'My account shows a duplicate charge on my card.' -> {"category": "billing", "reason": "Customer reports duplicate charge."}
2. Ticket: 'I was charged twice and the fraud team needs to look at my account.' -> {"category": "fraud", "reason": "Possible unauthorized charge."}
3. Ticket: 'The app keeps crashing when I open settings.' -> {"category": "technical", "reason": "App error or crash issue."}
'''
