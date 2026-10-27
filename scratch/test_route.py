import urllib.request
import json

wps = [
    {'city': 'Toshkent', 'lat': 41.2268, 'lng': 69.2198},
    {'city': 'Yangiyo\'l', 'lat': 41.1167, 'lng': 69.0500},
    {'city': 'Chinoz', 'lat': 40.9411, 'lng': 68.7594},
    {'city': 'Sirdaryo', 'lat': 40.8373, 'lng': 68.6618},
    {'city': 'Guliston', 'lat': 40.4897, 'lng': 68.7847},
    {'city': 'Yangiyer', 'lat': 40.2667, 'lng': 68.8167},
    {'city': 'Dashtobod', 'lat': 40.1000, 'lng': 68.4500},
    {'city': 'Zarbdor', 'lat': 40.0800, 'lng': 68.1700},
    {'city': 'Jizzax', 'lat': 40.1158, 'lng': 67.8422},
    {'city': 'G\'allaorol', 'lat': 40.0150, 'lng': 67.5850},
    {'city': 'Bulung\'ur', 'lat': 39.7611, 'lng': 67.2711},
    {'city': 'Samarqand', 'lat': 39.6542, 'lng': 66.9597}
]

q = ';'.join(str(w['lng']) + ',' + str(w['lat']) for w in wps)
url = 'https://router.project-osrm.org/route/v1/driving/' + q + '?overview=full&geometries=geojson'

req = urllib.request.urlopen(url)
data = json.loads(req.read().decode('utf-8'))
route = data['routes'][0]
coords = route['geometry']['coordinates']

print(f"Total points: {len(coords)}")
print(f"Total distance: {route['distance'] / 1000:.2f} km")
print(f"Total estimated driving time: {route['duration'] / 3600:.2f} hours")

# Check if any coordinate falls into Kazakhstan's Makhtaaral wedge:
# Kazakhstan Makhtaaral wedge is roughly: lat between 40.40 and 40.90, lng between 68.10 and 68.60.
kz_points = [pt for pt in coords if 40.40 <= pt[1] <= 40.85 and 68.15 <= pt[0] <= 68.58]
print(f"Points in Kazakhstan Makhtaaral wedge: {len(kz_points)}")

# Generate sampled fallback coordinates for offline / fallback
step = max(1, len(coords) // 30)
sampled = [coords[i] for i in range(0, len(coords), step)]
if sampled[-1] != coords[-1]:
    sampled.append(coords[-1])
print("Sampled count:", len(sampled))
with open("scratch/sample_coords.json", "w") as f:
    json.dump(sampled, f)
print("Saved sample coords successfully.")
