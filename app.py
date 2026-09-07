import os
import time
import requests
import gradio as gr
from google import genai


# =========================
# 1. Gemini API 연결
# =========================

api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)


# =========================
# 2. 날씨 Tool
# =========================

def get_weather(city: str) -> str:
    """도시 이름을 받아 현재 기온을 알려주는 함수입니다."""

    try:
        # 도시 이름 → 위도/경도
        geo_url = "https://nominatim.openstreetmap.org/search"

        geo_params = {
            "q": city,
            "format": "jsonv2",
            "limit": 1
        }

        headers = {
            "User-Agent": "travel-ai-agent/1.0 (https://travel-ai-agent-8bq7.onrender.com)"
        }

        geo_response = requests.get(
            geo_url,
            params=geo_params,
            headers=headers,
            timeout=10
        )

        geo_response.raise_for_status()
        geo_data = geo_response.json()

        if not geo_data:
            return f"{city}의 위치를 찾지 못했습니다."

        latitude = geo_data[0]["lat"]
        longitude = geo_data[0]["lon"]

        # 위도/경도 → 현재 날씨
        weather_url = "https://api.open-meteo.com/v1/forecast"

        weather_params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m"
        }

        weather_response = requests.get(
            weather_url,
            params=weather_params,
            timeout=10
        )

        weather_response.raise_for_status()
        weather_data = weather_response.json()

        temperature = weather_data["current"]["temperature_2m"]

        return f"{city}의 현재 기온은 {temperature}°C입니다."

    except Exception as e:
        return f"{city}의 날씨를 확인하지 못했습니다: {e}"


# =========================
# 3. 여행 일정 AI Agent
# =========================

def make_travel_plan_with_weather(destination, days, style):

    prompt = f"""
너는 친절한 여행 일정 AI 비서야.

여행지: {destination}
여행 기간: {days}일
여행 스타일: {style}

여행지의 현재 날씨를 확인하고,
그 날씨를 참고해서 여행 일정을 만들어줘.

날짜별로 오전, 점심, 오후, 저녁 순서로 작성하고,
각 장소의 추천 이유도 간단히 알려줘.
"""

    # Gemini 서버가 혼잡하면 한 번 재시도
    for attempt in range(2):

        try:
            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt,
                config={
                    "tools": [get_weather]
                }
            )

            return response.text

        except Exception as e:

            if "503" in str(e) and attempt == 0:
                time.sleep(5)

            else:
                return f"AI 요청 중 오류가 발생했습니다.\n\n{e}"

    return "AI가 응답하지 않았습니다. 잠시 후 다시 시도해주세요."


# =========================
# 4. Gradio 화면
# =========================

app = gr.Interface(
    fn=make_travel_plan_with_weather,

    inputs=[
        gr.Textbox(
            label="여행지",
            placeholder="예: 부산, 오사카, Paris"
        ),

        gr.Number(
            label="여행 기간(일)",
            value=2
        ),

        gr.Textbox(
            label="여행 스타일",
            placeholder="예: 맛집과 카페"
        )
    ],

    outputs=gr.Markdown(
        label="날씨를 반영한 여행 일정"
    ),

    title="날씨를 확인하는 여행 AI 비서",

    description=(
        "여행지, 기간, 스타일을 입력하면 "
        "현재 날씨를 확인한 뒤 여행 일정을 만들어드립니다. "
        "위치 데이터: © OpenStreetMap contributors"
    )
)


# =========================
# 5. Render에서 실행
# =========================

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 7860))

    app.launch(
        server_name="0.0.0.0",
        server_port=port
    )
