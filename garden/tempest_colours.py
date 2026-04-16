#!/usr/bin/env python3
"""
tempest_colours.py

A useless program that converts weather into color.
Temperature maps to hue. Humidity to saturation. Wind speed to brightness.
The result is a gradient that represents a place's weather as a mood.
"""

import requests
import json
from datetime import datetime


def temp_to_hue(celsius):
    """
    Map temperature to hue (0-360).
    Cold (0°C) = deep blue (240)
    Hot (35°C+) = warm orange-red (20)
    Comfort zone (20°C) = soft green (120)
    """
    # Normalize temperature to 0-1 range (clamped)
    # Assuming range of -10°C to 40°C
    normalized = max(0, min(1, (celsius + 10) / 50))
    
    # Map to hue: cold=blue (240), hot=red-orange (20)
    # Going through green (120) for moderate temps
    if normalized < 0.5:
        # Cold to moderate: blue (240) to green (120)
        return 240 - (normalized * 2 * 120)
    else:
        # Moderate to hot: green (120) to orange-red (20)
        return 120 - ((normalized - 0.5) * 2 * 100)


def humidity_to_saturation(humidity):
    """Higher humidity = more saturated colors."""
    return 30 + (humidity * 0.7)  # 30-100% saturation


def wind_to_brightness(wind_kph):
    """Higher wind = brighter, more energetic."""
    return min(95, 50 + (wind_kph * 1.5))  # 50-95% brightness


def hsb_to_rgb(h, s, b):
    """Convert HSB to RGB (all values 0-100)."""
    s = s / 100
    b = b / 100
    
    c = b * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = b - c
    
    if h < 60:
        r, g, bl = c, x, 0
    elif h < 120:
        r, g, bl = x, c, 0
    elif h < 180:
        r, g, bl = 0, c, x
    elif h < 240:
        r, g, bl = 0, x, c
    elif h < 300:
        r, g, bl = x, 0, c
    else:
        r, g, bl = c, 0, x
    
    return (int((r + m) * 255), int((g + m) * 255), int((bl + m) * 255))


def get_weather_data(lat=35.6895, lon=139.6917):
    """Fetch weather from Open-Meteo (free API, no key needed). Default: Tokyo."""
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        current = data['current']
        return {
            'temp': current['temperature_2m'],
            'humidity': current['relative_humidity_2m'],
            'wind': current['wind_speed_10m'],
            'location': f"{lat}, {lon}"
        }
    except Exception as e:
        # Fallback data if API fails
        return {
            'temp': 18.5,
            'humidity': 65,
            'wind': 12.3,
            'location': 'fallback (API error)',
            'error': str(e)
        }


def generate_gradient(weather):
    """Generate a gradient from the weather data."""
    hue = temp_to_hue(weather['temp'])
    saturation = humidity_to_saturation(weather['humidity'])
    brightness = wind_to_brightness(weather['wind'])
    
    # Create a gradient by varying hue slightly
    color1 = hsb_to_rgb(hue, saturation, brightness)
    color2 = hsb_to_rgb((hue + 20) % 360, saturation * 0.8, min(100, brightness + 10))
    
    return {
        'color1': f"rgb({color1[0]}, {color1[1]}, {color1[2]})",
        'color2': f"rgb({color2[0]}, {color2[1]}, {color2[2]})",
        'hue': hue,
        'saturation': saturation,
        'brightness': brightness
    }


def generate_html(weather, gradient):
    """Generate an HTML page showing the weather as color."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tempest Colours</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            min-height: 100vh;
            background: linear-gradient(135deg, {gradient['color1']}, {gradient['color2']});
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            font-family: 'Georgia', serif;
            color: rgba(255, 255, 255, 0.9);
            text-shadow: 0 2px 20px rgba(0, 0, 0, 0.3);
        }}
        
        .mood {{
            font-size: 3rem;
            font-weight: 300;
            letter-spacing: 0.1em;
            margin-bottom: 1rem;
        }}
        
        .data {{
            font-size: 1.1rem;
            opacity: 0.8;
            text-align: center;
            line-height: 1.8;
        }}
        
        .swatch {{
            margin-top: 2rem;
            padding: 1rem 2rem;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 4px;
            font-family: monospace;
            font-size: 0.9rem;
        }}
        
        .timestamp {{
            position: absolute;
            bottom: 2rem;
            font-size: 0.8rem;
            opacity: 0.6;
        }}
    </style>
</head>
<body>
    <div class="mood">{get_mood_text(weather)}</div>
    <div class="data">
        {weather['temp']:.1f}°C &nbsp;•&nbsp; {weather['humidity']:.0f}% humidity &nbsp;•&nbsp; {weather['wind']:.1f} km/h wind
    </div>
    <div class="swatch">
        hue: {gradient['hue']:.0f}° &nbsp;|&nbsp; sat: {gradient['saturation']:.0f}% &nbsp;|&nbsp; bri: {gradient['brightness']:.0f}%
    </div>
    <div class="timestamp">tempest_colours.py &nbsp;•&nbsp; {now}</div>
</body>
</html>"""
    
    return html


def get_mood_text(weather):
    """Generate a mood word based on weather conditions."""
    temp = weather['temp']
    humidity = weather['humidity']
    wind = weather['wind']
    
    # Simple mood mapping
    if temp < 5:
        return "frost"
    elif temp < 15:
        if humidity > 80:
            return "mist"
        return "crisp"
    elif temp < 25:
        if wind > 20:
            return "bloom"
        return "gentle"
    elif temp < 32:
        if humidity > 70:
            return "languid"
        return "warmth"
    else:
        return "ember"


def main():
    print("Fetching weather data...")
    weather = get_weather_data()
    
    print(f"Location: {weather['location']}")
    print(f"Temperature: {weather['temp']:.1f}°C")
    print(f"Humidity: {weather['humidity']:.0f}%")
    print(f"Wind: {weather['wind']:.1f} km/h")
    
    print("\nConverting to color...")
    gradient = generate_gradient(weather)
    
    print(f"Hue: {gradient['hue']:.0f}° (temperature)")
    print(f"Saturation: {gradient['saturation']:.0f}% (humidity)")
    print(f"Brightness: {gradient['brightness']:.0f}% (wind)")
    print(f"\nGradient: {gradient['color1']} → {gradient['color2']}")
    
    html = generate_html(weather, gradient)
    
    output_path = "/root/.openclaw/workspace/garden/tempest_colours.html"
    with open(output_path, 'w') as f:
        f.write(html)
    
    print(f"\n✓ Generated: {output_path}")
    print(f"✓ Mood: {get_mood_text(weather)}")
    print("\nOpen this file in a browser to see the weather as color.")


if __name__ == "__main__":
    main()
