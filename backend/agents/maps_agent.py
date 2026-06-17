"""
JARVIS — Maps & Location Agent
Provides geocoding, reverse geocoding, route calculations, and interactive map rendering.
"""

import os
import requests
from typing import Literal

import folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

from langchain_core.tools import tool
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate

from backend.agents.base import BaseAgent
from backend.config import GENERATED_IMAGES_DIR, llm
from backend.logger import get_logger

logger = get_logger("agents.maps")

# Config Nominatim with a distinct User-Agent to comply with OSM usage guidelines
GEOLOCATOR = Nominatim(user_agent="JARVIS-MultiAgentSystem/1.0 (contact: support@jarvis-os.ai)")


@tool
def geocode_address(address: str) -> str:
    """
    Translates an address string into Latitude and Longitude coordinates.
    """
    logger.info(f"Geocoding address: '{address}'")
    try:
        location = GEOLOCATOR.geocode(address, timeout=10)
        if location:
            return f"Location: {location.address}\nLatitude: {location.latitude}\nLongitude: {location.longitude}"
        return f"Could not find coordinates for address: '{address}'"
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        logger.error(f"Geocoding service error: {e}")
        return f"Geocoding service error: {str(e)}"


@tool
def reverse_geocode(latitude: float, longitude: float) -> str:
    """
    Translates Latitude and Longitude coordinates into a human-readable address.
    """
    logger.info(f"Reverse geocoding coordinates: {latitude}, {longitude}")
    try:
        location = GEOLOCATOR.reverse((latitude, longitude), timeout=10)
        if location:
            return f"Resolved Address: {location.address}"
        return f"No address found for coordinates: {latitude}, {longitude}"
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        logger.error(f"Reverse geocoding service error: {e}")
        return f"Reverse geocoding service error: {str(e)}"


@tool
def calculate_route(start_address: str, end_address: str, profile: Literal["driving", "walking", "cycling"] = "driving") -> str:
    """
    Calculates driving, walking, or cycling route between two addresses.
    Returns distance, travel duration, and route geometry description.
    """
    logger.info(f"Calculating route from '{start_address}' to '{end_address}' using profile '{profile}'")
    try:
        start_loc = GEOLOCATOR.geocode(start_address, timeout=10)
        end_loc = GEOLOCATOR.geocode(end_address, timeout=10)

        if not start_loc or not end_loc:
            return f"Failed to geocode one or both addresses:\nStart: {start_loc}\nEnd: {end_loc}"

        # Query OSRM API (lon,lat format)
        url = f"http://router.project-osrm.org/route/v1/{profile}/{start_loc.longitude},{start_loc.latitude};{end_loc.longitude},{end_loc.latitude}?overview=full&geometries=geojson"
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        data = res.json()

        if data.get("code") != "Ok":
            return f"OSRM Route Calculation failed: {data.get('message', 'Unknown error')}"

        route = data["routes"][0]
        distance_km = route["distance"] / 1000.0
        duration_mins = route["duration"] / 60.0

        # Save route details to map template later if needed
        return (
            f"Route found ({profile}):\n"
            f"- Start Point: {start_loc.address} ({start_loc.latitude}, {start_loc.longitude})\n"
            f"- End Point: {end_loc.address} ({end_loc.latitude}, {end_loc.longitude})\n"
            f"- Distance: {distance_km:.2f} km\n"
            f"- Estimated Duration: {duration_mins:.1f} minutes"
        )
    except Exception as e:
        logger.error(f"Route calculation failed: {e}")
        return f"Error calculating route: {str(e)}"


@tool
def find_nearby_places(address: str, place_type: str, radius_meters: int = 1000) -> str:
    """
    Finds points of interest (e.g. cafe, restaurant, hospital, parking) near a given address.
    """
    logger.info(f"Finding {place_type} within {radius_meters}m of '{address}'")
    try:
        loc = GEOLOCATOR.geocode(address, timeout=10)
        if not loc:
            return f"Could not resolve address '{address}'"

        # Overpass QL Query
        # Search for node tags matching amenity=place_type or tourism=place_type etc.
        overpass_url = "https://overpass-api.de/api/interpreter"
        query = f"""
        [out:json];
        (
          node(around:{radius_meters},{loc.latitude},{loc.longitude})["amenity"="{place_type}"];
          node(around:{radius_meters},{loc.latitude},{loc.longitude})["tourism"="{place_type}"];
          node(around:{radius_meters},{loc.latitude},{loc.longitude})["shop"="{place_type}"];
        );
        out 15;
        """
        headers = {"User-Agent": "JARVIS-MultiAgentSystem/1.0 (contact: support@jarvis-os.ai)"}
        res = requests.post(overpass_url, data={"data": query}, headers=headers, timeout=15)
        res.raise_for_status()
        data = res.json()

        elements = data.get("elements", [])
        if not elements:
            return f"No places of type '{place_type}' found within {radius_meters} meters of '{address}'."

        places_info = []
        for i, el in enumerate(elements, 1):
            name = el.get("tags", {}).get("name", "Unnamed Place")
            lat = el.get("lat")
            lon = el.get("lon")
            places_info.append(f"{i}. {name} (Lat: {lat}, Lon: {lon})")

        return f"Found {len(places_info)} places of type '{place_type}' nearby:\n" + "\n".join(places_info)
    except Exception as e:
        logger.error(f"Failed to fetch nearby places: {e}")
        return f"Error searching nearby places: {str(e)}"


@tool
def generate_map(start_address: str, end_address: str = "", map_name: str = "interactive_map") -> str:
    """
    Generates a beautiful interactive Leaflet HTML map centered on the start address (and showing the route to the end address if provided).
    Saves the file in the shared static folder.
    """
    logger.info(f"Generating map: {map_name}")
    try:
        start_loc = GEOLOCATOR.geocode(start_address, timeout=10)
        if not start_loc:
            return f"Could not resolve start address '{start_address}'"

        # Create basic map
        m = folium.Map(location=[start_loc.latitude, start_loc.longitude], zoom_start=14)
        folium.Marker(
            [start_loc.latitude, start_loc.longitude],
            popup=start_loc.address,
            tooltip="Start",
            icon=folium.Icon(color="green", icon="play")
        ).add_to(m)

        # Draw route if end_address is provided
        if end_address:
            end_loc = GEOLOCATOR.geocode(end_address, timeout=10)
            if end_loc:
                folium.Marker(
                    [end_loc.latitude, end_loc.longitude],
                    popup=end_loc.address,
                    tooltip="Destination",
                    icon=folium.Icon(color="red", icon="stop")
                ).add_to(m)

                # Fetch OSRM coordinate geometry
                url = f"http://router.project-osrm.org/route/v1/driving/{start_loc.longitude},{start_loc.latitude};{end_loc.longitude},{end_loc.latitude}?overview=full&geometries=geojson"
                res = requests.get(url, timeout=10)
                if res.status_code == 200:
                    route_data = res.json()
                    if route_data.get("code") == "Ok":
                        coords = route_data["routes"][0]["geometry"]["coordinates"]
                        # OSRM lon,lat needs to be converted to lat,lon for folium
                        points = [[c[1], c[0]] for c in coords]
                        folium.PolyLine(points, color="blue", weight=5, opacity=0.8).add_to(m)
                        m.fit_bounds([[start_loc.latitude, start_loc.longitude], [end_loc.latitude, end_loc.longitude]])

        # Ensure directory exists and save
        os.makedirs(GENERATED_IMAGES_DIR, exist_ok=True)
        file_path = os.path.join(GENERATED_IMAGES_DIR, f"{map_name}.html")
        m.save(file_path)

        web_url = f"http://localhost:8000/images/{map_name}.html"
        return f"Interactive map successfully created!\n- Local File Path: {file_path}\n- Browser View URL: {web_url}"
    except Exception as e:
        logger.error(f"Failed to generate map: {e}")
        return f"Error generating interactive map: {str(e)}"


class MapsAgent(BaseAgent):
    name = "maps"
    description = (
        "Enables address geocoding, coordinate reverse geocoding, route calculation "
        "(distance, duration, directions), point of interest search, and generating interactive HTML maps."
    )

    def __init__(self):
        self.tools = [
            geocode_address,
            reverse_geocode,
            calculate_route,
            find_nearby_places,
            generate_map
        ]

    def run(self, query: str) -> str:
        logger.info(f"Running maps task: '{query[:80]}...'")

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are the JARVIS Maps & Location Agent.\n"
                "Your job is to assist the user or system in geocoding addresses, finding directions, routing, "
                "locating places of interest nearby, or generating interactive HTML Leaflet maps.\n\n"
                "Guidelines:\n"
                "- If the user requests directions or a route, calculate the route first. "
                "If they want a map, use the generate_map tool as well.\n"
                "- Return clean markdown summaries of distances, durations, addresses, and map links."
            ),
            ("human", "{query}"),
            ("placeholder", "{agent_scratchpad}"),
        ])

        agent = create_tool_calling_agent(llm=llm, tools=self.tools, prompt=prompt)
        executor = AgentExecutor(agent=agent, tools=self.tools, verbose=False)

        try:
            response = executor.invoke({"query": query})
            result = response.get("output", str(response))
            logger.info("Maps task completed.")
            return result
        except Exception as e:
            logger.error(f"Maps execution error: {e}")
            return f"Error: {str(e)}"
