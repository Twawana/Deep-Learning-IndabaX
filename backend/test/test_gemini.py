service = GeminiService()

recommendation = service.generate_recommendation(
    farmer_question="Should I move my cattle this week?",
    pasture_data=pasture_data,
    weather_data=weather_data,
)

print(recommendation)