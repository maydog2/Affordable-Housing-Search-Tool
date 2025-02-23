import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import requests

# Geocode an address and get its latitude/longitude
def geocode_address(addr, expected_state="California"):
    print(f"\naddr: {addr}")

    formatted_addr = addr.replace(" ", "+")
    url = f"https://nominatim.openstreetmap.org/search?q={formatted_addr}&format=json"

    try:
        # Prevents API blocking
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)

        if response.status_code != 200 or not response.text.strip():
            print("Error: Empty response or bad status code")
            return None, None

        json_response = response.json()

        if not json_response:
            print("Error: No results found for the given address")
            return None, None

        # Filter results to match the expected state
        for result in json_response:
            if expected_state in result["display_name"] and result["class"] == "place":
                lat, lon = result["lat"], result["lon"]
                print(f"Selected Location: {result['display_name']}")
                print(f"Lat: {lat}, Lon: {lon}")
                return lat, lon

        print("Error: No matching result found in the expected state.")
        return None, None

    except requests.exceptions.RequestException as e:
        print(f"Network error: {e}")
        return None, None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None, None


# Get the Census Tract FIPS code using the FCC Census Block API.
def get_fips_code(lat, lon):
    url = f"https://geo.fcc.gov/api/census/area?lat={lat}&lon={lon}&format=json"

    try:
        response = requests.get(url)
        data = response.json()

        if "results" in data and len(data["results"]) > 0:
            county_fips = data["results"][0]["county_fips"]
            tract_code = data["results"][0]["block_fips"][5:11]
            full_fips = f"{county_fips}{tract_code}"
            return full_fips
        else:
            print("Error: No FIPS code found for this location.")
            return None

    except Exception as e:
        print(f"Exception occurred: {e}")
        return None

if __name__ == "__main__":
    try:
        qct_df = pd.read_csv("data/QCT2025.csv")
        fips_set = set(qct_df["fips"].astype(str).str.zfill(11))
        dda_zones = gpd.read_file("data/DDA/DDA2024.shp")

        # Ensure the shapefile is in WGS 84 (EPSG:4326)
        if dda_zones.crs != "EPSG:4326":
            dda_zones = dda_zones.to_crs("EPSG:4326")

    except FileNotFoundError as e:
        print(f"Error: Missing file - {e}")
        exit(1)  # Exit the script since files are essential

    except Exception as e:
        print(f"Unexpected error while loading files: {e}")
        exit(1)

    # addrs = ['5455 Wilshire Blvd', '5425 Wilshire Blvd', '1164 W Sunset Blvd', '1420 S Point View St', '1420 S Cochran Ave', '3205 Ocean Park Blvd']
    addrs = ['5455 Wilshire Blvd', '5425 Wilshire Blvd', '2331 Portland St']

    for addr in addrs:
        try:
            is_in_qct, is_in_dda = False, False
            lat, lon = geocode_address(addr)

            if lat is None or lon is None:
                print(f"Warning: Could not geocode address '{addr}'. Skipping.")
                continue  # Skip this address

            fips_code = get_fips_code(lat, lon)

            if fips_code is None:
                print(f"Warning: Could not retrieve FIPS code for '{addr}'. Skipping.")
                continue  # Skip this address

            point = Point(lon, lat)

            # Check if address is in QCT zone
            is_in_qct = fips_code in fips_set

            # Check if address is in DDA zone (ensure dda_zones is not empty)
            if not dda_zones.empty:
                is_in_dda = dda_zones.contains(point).any()

            print(f"{addr} is in a QCT zone: {is_in_qct}, in a DDA zone: {is_in_dda}")

        except Exception as e:
            print(f"Error processing '{addr}': {e}")