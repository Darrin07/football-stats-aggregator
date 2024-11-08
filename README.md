# football-stats-aggregator

# Football Stats Aggregator is a Python-based web application that aggregates 
# and displays real-time and historical football statistics. The platform 
# allows users to view and compare player and team performance, track game 
# results, and analyze key stats using an interactive dashboard. Built with 
# microservice architecture, the project integrates external sports data 
# APIs to provide up-to-date information, making it a useful tool for 
# football enthusiasts, analysts, and fantasy football players.




import requests

url = "http://recommendation-service.netflix.com/recommend"
payload = {"user_id": 1234, "preferences": ["comedy", "action"]}
response = requests.post(url, json=payload)

print(response.json())
