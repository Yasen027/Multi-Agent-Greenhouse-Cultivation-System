Return JSON only: {"crop":"tomato|lettuce|strawberry|cucumber|pepper|unknown","confidence":0.0,"evidence":[],"method":"deepseek_vision|metadata|fallback","human_intervention":{"required":false,"urgency":"none","reason":"","question_to_human":""}}.
Use the image when available, then user input and metadata. Confidence below 0.7 or an unknown crop requires human confirmation.
image={{image_data}} user={{user_input}} metadata={{context}} sensors={{sensor_data_json}} history={{history_json}}.
