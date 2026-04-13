"""
City database used for nuclear targeting and blast-radius collateral checks.
Each entry: {"name": str, "lat": float, "lon": float, "pop": float (millions)}
Cities are weighted by population when selecting a nuclear target.
"""
import math
import random

# ── Utility functions ──────────────────────────────────────────────────────────

def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance in km between two lat/lon points."""
    R = 6371.0
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    dφ = math.radians(lat2 - lat1)
    dλ = math.radians(lon2 - lon1)
    a = math.sin(dφ / 2) ** 2 + math.cos(φ1) * math.cos(φ2) * math.sin(dλ / 2) ** 2
    return 2 * R * math.asin(math.sqrt(max(0.0, min(1.0, a))))


def blast_radius_km(warheads):
    """Return (lethal_km, damage_km) for a strike with the given warhead count.

    Model: each warhead ≈ 300 kt yield.  Radius scales as cube-root of effective
    warhead count (diminishing returns — saturates at 50 for geometric expansion).
    Single warhead:   lethal ≈ 15 km,  damage ≈ 80 km
    50  warheads:     lethal ≈ 55 km,  damage ≈ 292 km  (covers smaller countries)
    """
    eff = max(1, min(warheads, 50))
    lethal_km = 15.0 * (eff ** (1 / 3))
    damage_km = 80.0 * (eff ** (1 / 3))
    return lethal_km, damage_km


def pick_target_city(country):
    """Choose a city to target, weighted by city population.  Returns None if no
    city data is available for this country."""
    cities = getattr(country, 'cities', [])
    if not cities:
        return None
    total = sum(c['pop'] for c in cities)
    if total <= 0:
        return random.choice(cities)
    r = random.uniform(0, total)
    cumulative = 0.0
    for city in cities:
        cumulative += city['pop']
        if r <= cumulative:
            return city
    return cities[-1]


# Fraction of a city's population killed inside each zone
LETHAL_MORTALITY = 0.65
DAMAGE_MORTALITY = 0.18


def fallout_duration_months(warheads):
    """How many sim months the ☢ fallout badge persists after a strike.

    Scales sub-linearly with warhead count — doubling warheads doesn't
    double fallout duration because most of the extra yield just vaporises
    the same already-destroyed area.

    1  warhead  →  ~60 months  ( 5 years)
    10 warheads →  ~145 months (12 years)
    100 warheads → ~347 months (29 years)
    500 warheads → ~631 months (53 years)
    """
    return int(60 * max(warheads, 1) ** 0.42)


# ── City database ──────────────────────────────────────────────────────────────

CITIES = {
    "Afghanistan": [
        {"name": "Kabul",          "lat":  34.52, "lon":  69.18, "pop": 4.60},
        {"name": "Kandahar",       "lat":  31.61, "lon":  65.71, "pop": 0.61},
        {"name": "Herat",          "lat":  34.35, "lon":  62.20, "pop": 0.55},
        {"name": "Mazar-i-Sharif", "lat":  36.71, "lon":  67.11, "pop": 0.50},
    ],
    "Albania": [
        {"name": "Tirana",  "lat":  41.33, "lon":  19.82, "pop": 0.90},
        {"name": "Durrës",  "lat":  41.32, "lon":  19.46, "pop": 0.30},
    ],
    "Algeria": [
        {"name": "Algiers",    "lat":  36.74, "lon":   3.06, "pop": 3.80},
        {"name": "Oran",       "lat":  35.70, "lon":  -0.63, "pop": 0.90},
        {"name": "Constantine","lat":  36.37, "lon":   6.61, "pop": 0.45},
    ],
    "Angola": [
        {"name": "Luanda",  "lat":  -8.84, "lon":  13.23, "pop": 8.30},
        {"name": "Huambo",  "lat": -12.78, "lon":  15.74, "pop": 0.60},
        {"name": "Lobito",  "lat": -12.35, "lon":  13.55, "pop": 0.50},
    ],
    "Argentina": [
        {"name": "Buenos Aires", "lat": -34.60, "lon": -58.38, "pop": 15.0},
        {"name": "Córdoba",      "lat": -31.42, "lon": -64.18, "pop":  1.60},
        {"name": "Rosario",      "lat": -32.94, "lon": -60.66, "pop":  1.40},
        {"name": "Mendoza",      "lat": -32.89, "lon": -68.85, "pop":  1.10},
    ],
    "Armenia": [
        {"name": "Yerevan", "lat":  40.18, "lon":  44.51, "pop": 1.09},
        {"name": "Gyumri",  "lat":  40.79, "lon":  43.85, "pop": 0.12},
    ],
    "Australia": [
        {"name": "Sydney",    "lat": -33.87, "lon": 151.21, "pop": 5.30},
        {"name": "Melbourne", "lat": -37.81, "lon": 144.96, "pop": 5.10},
        {"name": "Brisbane",  "lat": -27.47, "lon": 153.03, "pop": 2.50},
        {"name": "Perth",     "lat": -31.95, "lon": 115.86, "pop": 2.10},
        {"name": "Canberra",  "lat": -35.28, "lon": 149.13, "pop": 0.45},
    ],
    "Austria": [
        {"name": "Vienna", "lat":  48.21, "lon":  16.37, "pop": 1.90},
        {"name": "Graz",   "lat":  47.07, "lon":  15.44, "pop": 0.29},
        {"name": "Linz",   "lat":  48.30, "lon":  14.29, "pop": 0.20},
    ],
    "Azerbaijan": [
        {"name": "Baku",  "lat":  40.41, "lon":  49.87, "pop": 2.30},
        {"name": "Ganja", "lat":  40.68, "lon":  46.36, "pop": 0.33},
    ],
    "Bahamas": [
        {"name": "Nassau", "lat":  25.05, "lon": -77.35, "pop": 0.27},
    ],
    "Bahrain": [
        {"name": "Manama", "lat":  26.23, "lon":  50.59, "pop": 0.60},
    ],
    "Bangladesh": [
        {"name": "Dhaka",     "lat":  23.81, "lon":  90.41, "pop": 21.0},
        {"name": "Chittagong","lat":  22.34, "lon":  91.83, "pop":  5.0},
        {"name": "Khulna",    "lat":  22.82, "lon":  89.55, "pop":  1.5},
        {"name": "Sylhet",    "lat":  24.90, "lon":  91.87, "pop":  0.5},
    ],
    "Barbados": [
        {"name": "Bridgetown", "lat":  13.10, "lon": -59.62, "pop": 0.11},
    ],
    "Belarus": [
        {"name": "Minsk",   "lat":  53.90, "lon":  27.57, "pop": 2.00},
        {"name": "Gomel",   "lat":  52.43, "lon":  30.98, "pop": 0.48},
        {"name": "Vitebsk", "lat":  55.20, "lon":  30.20, "pop": 0.36},
    ],
    "Belgium": [
        {"name": "Brussels", "lat":  50.85, "lon":   4.35, "pop": 1.20},
        {"name": "Antwerp",  "lat":  51.22, "lon":   4.40, "pop": 0.52},
        {"name": "Ghent",    "lat":  51.05, "lon":   3.72, "pop": 0.26},
        {"name": "Liège",    "lat":  50.63, "lon":   5.57, "pop": 0.19},
    ],
    "Belize": [
        {"name": "Belmopan", "lat":  17.25, "lon": -88.77, "pop": 0.02},
    ],
    "Benin": [
        {"name": "Cotonou",   "lat":   6.37, "lon":   2.42, "pop": 0.68},
        {"name": "Porto-Novo","lat":   6.49, "lon":   2.61, "pop": 0.27},
    ],
    "Bhutan": [
        {"name": "Thimphu", "lat":  27.47, "lon":  89.64, "pop": 0.12},
    ],
    "Bolivia": [
        {"name": "La Paz",       "lat": -16.50, "lon": -68.15, "pop": 1.83},
        {"name": "Santa Cruz",   "lat": -17.78, "lon": -63.18, "pop": 1.61},
        {"name": "Cochabamba",   "lat": -17.39, "lon": -66.16, "pop": 0.66},
    ],
    "Bosnia": [
        {"name": "Sarajevo",  "lat":  43.85, "lon":  18.40, "pop": 0.44},
        {"name": "Banja Luka","lat":  44.77, "lon":  17.18, "pop": 0.19},
    ],
    "Botswana": [
        {"name": "Gaborone", "lat": -24.65, "lon":  25.91, "pop": 0.27},
    ],
    "Brazil": [
        {"name": "São Paulo",    "lat": -23.55, "lon": -46.63, "pop": 22.0},
        {"name": "Rio de Janeiro","lat":-22.91, "lon": -43.17, "pop": 13.5},
        {"name": "Brasília",     "lat": -15.78, "lon": -47.93, "pop":  3.0},
        {"name": "Salvador",     "lat": -12.98, "lon": -38.52, "pop":  2.9},
        {"name": "Fortaleza",    "lat":  -3.72, "lon": -38.54, "pop":  2.7},
        {"name": "Manaus",       "lat":  -3.10, "lon": -60.02, "pop":  2.3},
        {"name": "Curitiba",     "lat": -25.43, "lon": -49.27, "pop":  1.9},
        {"name": "Belém",        "lat":  -1.46, "lon": -48.50, "pop":  1.5},
    ],
    "Brunei": [
        {"name": "Bandar Seri Begawan", "lat":   4.94, "lon": 114.95, "pop": 0.10},
    ],
    "Burkina Faso": [
        {"name": "Ouagadougou",   "lat":  12.37, "lon":  -1.53, "pop": 2.80},
        {"name": "Bobo-Dioulasso","lat":  11.18, "lon":  -4.30, "pop": 0.90},
    ],
    "Burundi": [
        {"name": "Bujumbura", "lat":  -3.38, "lon":  29.36, "pop": 1.00},
        {"name": "Gitega",    "lat":  -3.43, "lon":  29.92, "pop": 0.12},
    ],
    "Cambodia": [
        {"name": "Phnom Penh","lat":  11.57, "lon": 104.92, "pop": 2.10},
        {"name": "Siem Reap", "lat":  13.36, "lon": 103.86, "pop": 0.23},
    ],
    "Cameroon": [
        {"name": "Yaoundé", "lat":   3.87, "lon":  11.52, "pop": 3.70},
        {"name": "Douala",  "lat":   4.05, "lon":   9.70, "pop": 3.30},
    ],
    "Canada": [
        {"name": "Toronto",   "lat":  43.70, "lon":  -79.42, "pop": 6.20},
        {"name": "Montreal",  "lat":  45.51, "lon":  -73.55, "pop": 4.30},
        {"name": "Vancouver", "lat":  49.26, "lon": -123.12, "pop": 2.60},
        {"name": "Calgary",   "lat":  51.05, "lon": -114.07, "pop": 1.30},
        {"name": "Ottawa",    "lat":  45.42, "lon":  -75.70, "pop": 1.00},
        {"name": "Edmonton",  "lat":  53.55, "lon": -113.47, "pop": 0.98},
    ],
    "Cape Verde": [
        {"name": "Praia", "lat":  14.93, "lon": -23.51, "pop": 0.15},
    ],
    "Central African Republic": [
        {"name": "Bangui", "lat":   4.36, "lon":  18.56, "pop": 0.90},
    ],
    "Chad": [
        {"name": "N'Djamena", "lat":  12.11, "lon":  15.04, "pop": 1.40},
        {"name": "Moundou",   "lat":   8.57, "lon":  16.07, "pop": 0.16},
    ],
    "Chile": [
        {"name": "Santiago",    "lat": -33.46, "lon": -70.65, "pop": 6.90},
        {"name": "Valparaíso",  "lat": -33.05, "lon": -71.62, "pop": 0.30},
        {"name": "Concepción",  "lat": -36.82, "lon": -73.05, "pop": 0.23},
        {"name": "Antofagasta", "lat": -23.65, "lon": -70.40, "pop": 0.36},
    ],
    "China": [
        {"name": "Shanghai",   "lat":  31.23, "lon": 121.47, "pop": 27.0},
        {"name": "Beijing",    "lat":  39.91, "lon": 116.39, "pop": 21.5},
        {"name": "Guangzhou",  "lat":  23.13, "lon": 113.26, "pop": 16.0},
        {"name": "Chongqing",  "lat":  29.56, "lon": 106.55, "pop": 15.0},
        {"name": "Chengdu",    "lat":  30.66, "lon": 104.07, "pop": 14.0},
        {"name": "Tianjin",    "lat":  39.14, "lon": 117.18, "pop": 13.5},
        {"name": "Wuhan",      "lat":  30.59, "lon": 114.31, "pop": 12.0},
        {"name": "Shenzhen",   "lat":  22.54, "lon": 114.06, "pop": 12.5},
        {"name": "Xi'an",      "lat":  34.27, "lon": 108.95, "pop":  9.0},
        {"name": "Nanjing",    "lat":  32.06, "lon": 118.78, "pop":  8.5},
        {"name": "Harbin",     "lat":  45.75, "lon": 126.64, "pop":  5.3},
        {"name": "Ürümqi",     "lat":  43.80, "lon":  87.60, "pop":  3.5},
    ],
    "Colombia": [
        {"name": "Bogotá",      "lat":   4.71, "lon": -74.07, "pop": 8.00},
        {"name": "Medellín",    "lat":   6.25, "lon": -75.57, "pop": 2.70},
        {"name": "Cali",        "lat":   3.44, "lon": -76.52, "pop": 2.20},
        {"name": "Barranquilla","lat":  11.00, "lon": -74.82, "pop": 1.20},
    ],
    "Comoros": [
        {"name": "Moroni", "lat": -11.70, "lon":  43.26, "pop": 0.06},
    ],
    "Congo": [
        {"name": "Brazzaville",  "lat":  -4.27, "lon":  15.28, "pop": 2.30},
        {"name": "Pointe-Noire", "lat":  -4.77, "lon":  11.87, "pop": 1.20},
    ],
    "Costa Rica": [
        {"name": "San José", "lat":   9.93, "lon": -84.08, "pop": 1.40},
    ],
    "Croatia": [
        {"name": "Zagreb", "lat":  45.81, "lon":  15.98, "pop": 0.80},
        {"name": "Split",  "lat":  43.51, "lon":  16.44, "pop": 0.18},
    ],
    "Cuba": [
        {"name": "Havana",          "lat":  23.13, "lon": -82.38, "pop": 2.10},
        {"name": "Santiago de Cuba","lat":  20.02, "lon": -75.82, "pop": 0.43},
    ],
    "Cyprus": [
        {"name": "Nicosia", "lat":  35.17, "lon":  33.36, "pop": 0.25},
    ],
    "Czech Republic": [
        {"name": "Prague", "lat":  50.08, "lon":  14.44, "pop": 1.30},
        {"name": "Brno",   "lat":  49.20, "lon":  16.61, "pop": 0.38},
    ],
    "DR Congo": [
        {"name": "Kinshasa",  "lat":  -4.32, "lon":  15.32, "pop": 15.0},
        {"name": "Lubumbashi","lat": -11.66, "lon":  27.48, "pop":  2.3},
        {"name": "Goma",      "lat":  -1.68, "lon":  29.22, "pop":  1.1},
        {"name": "Kisangani", "lat":   0.52, "lon":  25.20, "pop":  1.0},
    ],
    "Denmark": [
        {"name": "Copenhagen","lat":  55.68, "lon":  12.57, "pop": 1.35},
        {"name": "Aarhus",    "lat":  56.15, "lon":  10.22, "pop": 0.28},
    ],
    "Djibouti": [
        {"name": "Djibouti City", "lat":  11.59, "lon":  43.15, "pop": 0.60},
    ],
    "Dominican Republic": [
        {"name": "Santo Domingo","lat":  18.47, "lon": -69.90, "pop": 3.30},
        {"name": "Santiago",     "lat":  19.45, "lon": -70.69, "pop": 0.75},
    ],
    "Ecuador": [
        {"name": "Quito",     "lat":  -0.23, "lon": -78.52, "pop": 2.00},
        {"name": "Guayaquil", "lat":  -2.16, "lon": -79.90, "pop": 2.70},
        {"name": "Cuenca",    "lat":  -2.90, "lon": -79.01, "pop": 0.33},
    ],
    "Egypt": [
        {"name": "Cairo",      "lat":  30.06, "lon":  31.25, "pop": 21.3},
        {"name": "Alexandria", "lat":  31.20, "lon":  29.92, "pop":  5.4},
        {"name": "Giza",       "lat":  30.01, "lon":  31.21, "pop":  9.0},
        {"name": "Port Said",  "lat":  31.25, "lon":  32.28, "pop":  0.7},
        {"name": "Suez",       "lat":  29.97, "lon":  32.55, "pop":  0.6},
    ],
    "El Salvador": [
        {"name": "San Salvador","lat":  13.69, "lon": -89.19, "pop": 1.10},
        {"name": "Santa Ana",   "lat":  13.99, "lon": -89.56, "pop": 0.27},
    ],
    "Equatorial Guinea": [
        {"name": "Malabo", "lat":   3.75, "lon":   8.78, "pop": 0.20},
    ],
    "Eritrea": [
        {"name": "Asmara", "lat":  15.34, "lon":  38.93, "pop": 0.96},
    ],
    "Estonia": [
        {"name": "Tallinn", "lat":  59.44, "lon":  24.75, "pop": 0.45},
        {"name": "Tartu",   "lat":  58.38, "lon":  26.73, "pop": 0.10},
    ],
    "Eswatini": [
        {"name": "Mbabane", "lat": -26.32, "lon":  31.14, "pop": 0.09},
    ],
    "Ethiopia": [
        {"name": "Addis Ababa","lat":   9.03, "lon":  38.74, "pop": 5.10},
        {"name": "Dire Dawa",  "lat":   9.60, "lon":  41.87, "pop": 0.49},
        {"name": "Mekele",     "lat":  13.50, "lon":  39.48, "pop": 0.32},
        {"name": "Adama",      "lat":   8.54, "lon":  39.27, "pop": 0.32},
    ],
    "Fiji": [
        {"name": "Suva", "lat": -18.14, "lon": 178.44, "pop": 0.18},
    ],
    "Finland": [
        {"name": "Helsinki", "lat":  60.17, "lon":  24.94, "pop": 0.65},
        {"name": "Tampere",  "lat":  61.50, "lon":  23.77, "pop": 0.24},
        {"name": "Turku",    "lat":  60.45, "lon":  22.27, "pop": 0.19},
    ],
    "France": [
        {"name": "Paris",      "lat":  48.86, "lon":   2.35, "pop": 11.0},
        {"name": "Marseille",  "lat":  43.30, "lon":   5.37, "pop":  1.6},
        {"name": "Lyon",       "lat":  45.75, "lon":   4.85, "pop":  1.7},
        {"name": "Toulouse",   "lat":  43.60, "lon":   1.44, "pop":  0.9},
        {"name": "Nice",       "lat":  43.71, "lon":   7.26, "pop":  0.6},
        {"name": "Strasbourg", "lat":  48.58, "lon":   7.75, "pop":  0.8},
        {"name": "Bordeaux",   "lat":  44.84, "lon":  -0.58, "pop":  0.8},
    ],
    "Gabon": [
        {"name": "Libreville", "lat":   0.39, "lon":   9.45, "pop": 0.80},
    ],
    "Gambia": [
        {"name": "Banjul", "lat":  13.45, "lon": -16.58, "pop": 0.46},
    ],
    "Georgia": [
        {"name": "Tbilisi", "lat":  41.69, "lon":  44.83, "pop": 1.17},
        {"name": "Batumi",  "lat":  41.64, "lon":  41.64, "pop": 0.17},
        {"name": "Kutaisi", "lat":  42.27, "lon":  42.69, "pop": 0.15},
    ],
    "Germany": [
        {"name": "Berlin",    "lat":  52.52, "lon":  13.40, "pop": 3.80},
        {"name": "Hamburg",   "lat":  53.57, "lon":  10.02, "pop": 1.90},
        {"name": "Munich",    "lat":  48.14, "lon":  11.58, "pop": 1.50},
        {"name": "Cologne",   "lat":  50.94, "lon":   6.96, "pop": 1.10},
        {"name": "Frankfurt", "lat":  50.11, "lon":   8.68, "pop": 0.77},
        {"name": "Stuttgart", "lat":  48.78, "lon":   9.18, "pop": 0.64},
        {"name": "Düsseldorf","lat":  51.23, "lon":   6.78, "pop": 0.64},
        {"name": "Leipzig",   "lat":  51.34, "lon":  12.38, "pop": 0.60},
        {"name": "Dresden",   "lat":  51.05, "lon":  13.74, "pop": 0.56},
    ],
    "Ghana": [
        {"name": "Accra",  "lat":   5.56, "lon":  -0.20, "pop": 2.50},
        {"name": "Kumasi", "lat":   6.69, "lon":  -1.62, "pop": 3.00},
    ],
    "Greece": [
        {"name": "Athens",       "lat":  37.98, "lon":  23.73, "pop": 3.75},
        {"name": "Thessaloniki", "lat":  40.64, "lon":  22.94, "pop": 1.11},
        {"name": "Patras",       "lat":  38.25, "lon":  21.73, "pop": 0.22},
    ],
    "Greenland": [
        {"name": "Nuuk",     "lat":  64.18, "lon": -51.74, "pop": 0.019},
        {"name": "Sisimiut", "lat":  66.93, "lon": -53.67, "pop": 0.006},
    ],
    "Guatemala": [
        {"name": "Guatemala City",  "lat":  14.64, "lon": -90.51, "pop": 3.00},
        {"name": "Quetzaltenango", "lat":  14.83, "lon": -91.52, "pop": 0.22},
    ],
    "Guinea": [
        {"name": "Conakry", "lat":   9.54, "lon": -13.68, "pop": 1.90},
    ],
    "Guinea-Bissau": [
        {"name": "Bissau", "lat":  11.86, "lon": -15.60, "pop": 0.49},
    ],
    "Guyana": [
        {"name": "Georgetown", "lat":   6.80, "lon": -58.16, "pop": 0.24},
    ],
    "Haiti": [
        {"name": "Port-au-Prince","lat":  18.54, "lon": -72.34, "pop": 2.80},
        {"name": "Cap-Haïtien",  "lat":  19.76, "lon": -72.20, "pop": 0.19},
    ],
    "Honduras": [
        {"name": "Tegucigalpa",  "lat":  14.10, "lon": -87.21, "pop": 1.40},
        {"name": "San Pedro Sula","lat": 15.50, "lon": -88.04, "pop": 0.90},
    ],
    "Hungary": [
        {"name": "Budapest", "lat":  47.50, "lon":  19.04, "pop": 1.75},
        {"name": "Debrecen", "lat":  47.53, "lon":  21.63, "pop": 0.20},
    ],
    "Iceland": [
        {"name": "Reykjavik", "lat":  64.14, "lon": -21.89, "pop": 0.23},
    ],
    "India": [
        {"name": "Mumbai",    "lat":  19.08, "lon":  72.88, "pop": 20.7},
        {"name": "Delhi",     "lat":  28.66, "lon":  77.22, "pop": 32.9},
        {"name": "Kolkata",   "lat":  22.57, "lon":  88.37, "pop": 14.8},
        {"name": "Chennai",   "lat":  13.08, "lon":  80.27, "pop":  7.1},
        {"name": "Bengaluru", "lat":  12.97, "lon":  77.59, "pop": 12.8},
        {"name": "Hyderabad", "lat":  17.38, "lon":  78.49, "pop":  9.7},
        {"name": "Ahmedabad", "lat":  23.03, "lon":  72.59, "pop":  8.6},
        {"name": "Pune",      "lat":  18.52, "lon":  73.85, "pop":  7.4},
        {"name": "Jaipur",    "lat":  26.92, "lon":  75.82, "pop":  4.0},
        {"name": "Lucknow",   "lat":  26.85, "lon":  80.95, "pop":  3.7},
        {"name": "Amritsar",  "lat":  31.63, "lon":  74.87, "pop":  1.3},
        {"name": "Chandigarh","lat":  30.73, "lon":  76.78, "pop":  0.9},
    ],
    "Indonesia": [
        {"name": "Jakarta",  "lat":  -6.21, "lon": 106.85, "pop": 10.5},
        {"name": "Surabaya", "lat":  -7.25, "lon": 112.75, "pop":  2.9},
        {"name": "Bandung",  "lat":  -6.92, "lon": 107.61, "pop":  2.5},
        {"name": "Medan",    "lat":   3.59, "lon":  98.67, "pop":  2.8},
        {"name": "Makassar", "lat":  -5.14, "lon": 119.43, "pop":  1.5},
    ],
    "Iran": [
        {"name": "Tehran",   "lat":  35.69, "lon":  51.39, "pop": 9.50},
        {"name": "Mashhad",  "lat":  36.28, "lon":  59.61, "pop": 3.40},
        {"name": "Isfahan",  "lat":  32.66, "lon":  51.68, "pop": 2.20},
        {"name": "Karaj",    "lat":  35.84, "lon":  50.94, "pop": 1.97},
        {"name": "Tabriz",   "lat":  38.08, "lon":  46.30, "pop": 1.73},
        {"name": "Shiraz",   "lat":  29.61, "lon":  52.54, "pop": 1.57},
    ],
    "Iraq": [
        {"name": "Baghdad", "lat":  33.34, "lon":  44.40, "pop": 7.60},
        {"name": "Mosul",   "lat":  36.34, "lon":  43.13, "pop": 1.70},
        {"name": "Basra",   "lat":  30.51, "lon":  47.82, "pop": 1.40},
        {"name": "Erbil",   "lat":  36.19, "lon":  44.01, "pop": 1.50},
    ],
    "Ireland": [
        {"name": "Dublin", "lat":  53.33, "lon":  -6.25, "pop": 1.17},
        {"name": "Cork",   "lat":  51.90, "lon":  -8.47, "pop": 0.22},
    ],
    "Israel": [
        {"name": "Jerusalem","lat":  31.78, "lon":  35.22, "pop": 0.92},
        {"name": "Tel Aviv", "lat":  32.09, "lon":  34.78, "pop": 0.46},
        {"name": "Haifa",    "lat":  32.82, "lon":  34.99, "pop": 0.29},
        {"name": "Beersheba","lat":  31.25, "lon":  34.79, "pop": 0.21},
    ],
    "Italy": [
        {"name": "Rome",    "lat":  41.89, "lon":  12.51, "pop": 2.87},
        {"name": "Milan",   "lat":  45.46, "lon":   9.19, "pop": 1.37},
        {"name": "Naples",  "lat":  40.85, "lon":  14.27, "pop": 0.96},
        {"name": "Turin",   "lat":  45.07, "lon":   7.69, "pop": 0.86},
        {"name": "Palermo", "lat":  38.12, "lon":  13.36, "pop": 0.67},
        {"name": "Genoa",   "lat":  44.41, "lon":   8.94, "pop": 0.58},
        {"name": "Bologna", "lat":  44.50, "lon":  11.34, "pop": 0.39},
    ],
    "Ivory Coast": [
        {"name": "Abidjan",      "lat":   5.35, "lon":  -4.00, "pop": 5.10},
        {"name": "Yamoussoukro","lat":   6.82, "lon":  -5.27, "pop": 0.28},
        {"name": "Bouaké",      "lat":   7.69, "lon":  -5.03, "pop": 0.60},
    ],
    "Jamaica": [
        {"name": "Kingston", "lat":  18.00, "lon": -76.80, "pop": 0.58},
    ],
    "Japan": [
        {"name": "Tokyo",     "lat":  35.69, "lon": 139.69, "pop": 13.9},
        {"name": "Yokohama",  "lat":  35.44, "lon": 139.64, "pop":  3.8},
        {"name": "Osaka",     "lat":  34.69, "lon": 135.50, "pop":  2.7},
        {"name": "Nagoya",    "lat":  35.18, "lon": 136.91, "pop":  2.3},
        {"name": "Sapporo",   "lat":  43.06, "lon": 141.35, "pop":  1.9},
        {"name": "Fukuoka",   "lat":  33.59, "lon": 130.40, "pop":  1.6},
        {"name": "Hiroshima", "lat":  34.39, "lon": 132.45, "pop":  1.2},
        {"name": "Sendai",    "lat":  38.27, "lon": 140.87, "pop":  1.1},
    ],
    "Jordan": [
        {"name": "Amman", "lat":  31.96, "lon":  35.95, "pop": 2.15},
        {"name": "Zarqa", "lat":  32.07, "lon":  36.08, "pop": 0.63},
        {"name": "Irbid", "lat":  32.56, "lon":  35.85, "pop": 0.31},
    ],
    "Kazakhstan": [
        {"name": "Nur-Sultan", "lat":  51.18, "lon":  71.45, "pop": 1.18},
        {"name": "Almaty",     "lat":  43.25, "lon":  76.95, "pop": 1.90},
        {"name": "Shymkent",   "lat":  42.32, "lon":  69.59, "pop": 1.00},
    ],
    "Kenya": [
        {"name": "Nairobi", "lat":  -1.29, "lon":  36.82, "pop": 4.40},
        {"name": "Mombasa", "lat":  -4.05, "lon":  39.67, "pop": 1.20},
        {"name": "Kisumu",  "lat":  -0.10, "lon":  34.75, "pop": 0.41},
    ],
    "Kuwait": [
        {"name": "Kuwait City", "lat":  29.37, "lon":  47.99, "pop": 2.40},
    ],
    "Kyrgyzstan": [
        {"name": "Bishkek", "lat":  42.87, "lon":  74.59, "pop": 1.05},
        {"name": "Osh",     "lat":  40.51, "lon":  72.80, "pop": 0.32},
    ],
    "Laos": [
        {"name": "Vientiane", "lat":  17.97, "lon": 102.62, "pop": 0.82},
    ],
    "Latvia": [
        {"name": "Riga", "lat":  56.95, "lon":  24.11, "pop": 0.63},
    ],
    "Lebanon": [
        {"name": "Beirut",  "lat":  33.89, "lon":  35.50, "pop": 2.40},
        {"name": "Tripoli", "lat":  34.44, "lon":  35.84, "pop": 0.23},
    ],
    "Lesotho": [
        {"name": "Maseru", "lat": -29.32, "lon":  27.48, "pop": 0.33},
    ],
    "Liberia": [
        {"name": "Monrovia", "lat":   6.31, "lon": -10.80, "pop": 1.40},
    ],
    "Libya": [
        {"name": "Tripoli", "lat":  32.90, "lon":  13.18, "pop": 1.17},
        {"name": "Benghazi","lat":  32.11, "lon":  20.07, "pop": 0.63},
        {"name": "Misrata", "lat":  32.38, "lon":  15.09, "pop": 0.38},
    ],
    "Lithuania": [
        {"name": "Vilnius", "lat":  54.69, "lon":  25.28, "pop": 0.54},
        {"name": "Kaunas",  "lat":  54.90, "lon":  23.92, "pop": 0.30},
    ],
    "Luxembourg": [
        {"name": "Luxembourg City", "lat":  49.61, "lon":   6.13, "pop": 0.12},
    ],
    "Madagascar": [
        {"name": "Antananarivo","lat": -18.91, "lon":  47.54, "pop": 3.40},
        {"name": "Toamasina",   "lat": -18.15, "lon":  49.40, "pop": 0.32},
    ],
    "Malawi": [
        {"name": "Lilongwe", "lat": -13.97, "lon":  33.79, "pop": 1.08},
        {"name": "Blantyre", "lat": -15.79, "lon":  35.01, "pop": 0.80},
    ],
    "Malaysia": [
        {"name": "Kuala Lumpur","lat":   3.15, "lon": 101.71, "pop": 1.80},
        {"name": "George Town", "lat":   5.41, "lon": 100.34, "pop": 0.71},
        {"name": "Johor Bahru", "lat":   1.49, "lon": 103.75, "pop": 0.50},
        {"name": "Ipoh",        "lat":   4.60, "lon": 101.08, "pop": 0.67},
    ],
    "Mali": [
        {"name": "Bamako",  "lat":  12.65, "lon":  -8.00, "pop": 2.70},
        {"name": "Sikasso", "lat":  11.32, "lon":  -5.67, "pop": 0.23},
        {"name": "Mopti",   "lat":  14.50, "lon":  -4.20, "pop": 0.11},
    ],
    "Mauritania": [
        {"name": "Nouakchott",  "lat":  18.08, "lon": -15.97, "pop": 1.20},
        {"name": "Nouadhibou",  "lat":  20.93, "lon": -17.04, "pop": 0.12},
    ],
    "Mexico": [
        {"name": "Mexico City", "lat":  19.43, "lon":  -99.14, "pop": 21.6},
        {"name": "Guadalajara", "lat":  20.68, "lon": -103.35, "pop":  5.3},
        {"name": "Monterrey",   "lat":  25.67, "lon": -100.31, "pop":  5.1},
        {"name": "Puebla",      "lat":  19.03, "lon":  -98.21, "pop":  3.2},
        {"name": "Tijuana",     "lat":  32.53, "lon": -117.04, "pop":  1.9},
        {"name": "León",        "lat":  21.13, "lon": -101.69, "pop":  1.7},
        {"name": "Ciudad Juárez","lat": 31.74, "lon": -106.49, "pop":  1.5},
    ],
    "Moldova": [
        {"name": "Chișinău", "lat":  47.01, "lon":  28.86, "pop": 0.49},
    ],
    "Mongolia": [
        {"name": "Ulaanbaatar", "lat":  47.91, "lon": 106.91, "pop": 1.63},
    ],
    "Montenegro": [
        {"name": "Podgorica", "lat":  42.44, "lon":  19.26, "pop": 0.18},
    ],
    "Morocco": [
        {"name": "Casablanca","lat":  33.59, "lon":  -7.62, "pop": 3.75},
        {"name": "Rabat",     "lat":  34.02, "lon":  -6.83, "pop": 0.58},
        {"name": "Fès",       "lat":  34.04, "lon":  -5.00, "pop": 1.15},
        {"name": "Marrakesh", "lat":  31.63, "lon":  -7.99, "pop": 0.93},
        {"name": "Tangier",   "lat":  35.78, "lon":  -5.80, "pop": 0.95},
    ],
    "Mozambique": [
        {"name": "Maputo",  "lat": -25.97, "lon":  32.58, "pop": 1.10},
        {"name": "Beira",   "lat": -19.84, "lon":  34.84, "pop": 0.53},
        {"name": "Nampula", "lat": -15.12, "lon":  39.27, "pop": 0.74},
    ],
    "Myanmar": [
        {"name": "Naypyidaw","lat":  19.75, "lon":  96.13, "pop": 1.16},
        {"name": "Yangon",   "lat":  16.87, "lon":  96.19, "pop": 5.30},
        {"name": "Mandalay", "lat":  22.00, "lon":  96.08, "pop": 1.22},
    ],
    "Namibia": [
        {"name": "Windhoek", "lat": -22.56, "lon":  17.08, "pop": 0.43},
    ],
    "Nepal": [
        {"name": "Kathmandu","lat":  27.71, "lon":  85.32, "pop": 1.74},
        {"name": "Pokhara",  "lat":  28.21, "lon":  83.99, "pop": 0.43},
    ],
    "Netherlands": [
        {"name": "Amsterdam","lat":  52.37, "lon":   4.89, "pop": 0.87},
        {"name": "Rotterdam","lat":  51.92, "lon":   4.48, "pop": 0.65},
        {"name": "The Hague","lat":  52.08, "lon":   4.32, "pop": 0.55},
        {"name": "Utrecht",  "lat":  52.09, "lon":   5.12, "pop": 0.36},
    ],
    "New Zealand": [
        {"name": "Auckland",     "lat": -36.86, "lon": 174.77, "pop": 1.60},
        {"name": "Wellington",   "lat": -41.29, "lon": 174.78, "pop": 0.44},
        {"name": "Christchurch", "lat": -43.53, "lon": 172.64, "pop": 0.38},
    ],
    "Nicaragua": [
        {"name": "Managua", "lat":  12.13, "lon": -86.28, "pop": 1.05},
    ],
    "Niger": [
        {"name": "Niamey", "lat":  13.51, "lon":   2.12, "pop": 1.30},
        {"name": "Zinder",  "lat":  13.81, "lon":   8.99, "pop": 0.32},
    ],
    "Nigeria": [
        {"name": "Lagos",       "lat":   6.46, "lon":   3.38, "pop": 14.8},
        {"name": "Kano",        "lat":  12.00, "lon":   8.52, "pop":  4.1},
        {"name": "Ibadan",      "lat":   7.39, "lon":   3.90, "pop":  3.6},
        {"name": "Abuja",       "lat":   9.07, "lon":   7.40, "pop":  3.6},
        {"name": "Port Harcourt","lat":  4.82, "lon":   7.01, "pop":  1.9},
        {"name": "Benin City",  "lat":   6.34, "lon":   5.62, "pop":  1.5},
    ],
    "North Korea": [
        {"name": "Pyongyang", "lat":  39.03, "lon": 125.75, "pop": 3.26},
        {"name": "Hamhung",   "lat":  39.92, "lon": 127.54, "pop": 0.77},
        {"name": "Chongjin",  "lat":  41.79, "lon": 129.78, "pop": 0.63},
    ],
    "North Macedonia": [
        {"name": "Skopje", "lat":  41.99, "lon":  21.43, "pop": 0.54},
    ],
    "Norway": [
        {"name": "Oslo",      "lat":  59.91, "lon":  10.75, "pop": 1.04},
        {"name": "Bergen",    "lat":  60.39, "lon":   5.33, "pop": 0.28},
        {"name": "Trondheim", "lat":  63.43, "lon":  10.39, "pop": 0.21},
    ],
    "Oman": [
        {"name": "Muscat",  "lat":  23.59, "lon":  58.59, "pop": 1.56},
        {"name": "Salalah", "lat":  17.02, "lon":  54.09, "pop": 0.19},
    ],
    "Pakistan": [
        {"name": "Karachi",    "lat":  24.86, "lon":  67.01, "pop": 16.0},
        {"name": "Lahore",     "lat":  31.55, "lon":  74.36, "pop": 13.0},
        {"name": "Faisalabad", "lat":  31.42, "lon":  73.09, "pop":  3.7},
        {"name": "Rawalpindi", "lat":  33.60, "lon":  73.05, "pop":  2.3},
        {"name": "Islamabad",  "lat":  33.72, "lon":  73.06, "pop":  1.1},
        {"name": "Peshawar",   "lat":  34.01, "lon":  71.58, "pop":  2.0},
        {"name": "Multan",     "lat":  30.20, "lon":  71.47, "pop":  1.9},
        {"name": "Quetta",     "lat":  30.19, "lon":  67.01, "pop":  1.0},
    ],
    "Panama": [
        {"name": "Panama City", "lat":   8.99, "lon": -79.52, "pop": 0.88},
    ],
    "Papua New Guinea": [
        {"name": "Port Moresby", "lat":  -9.44, "lon": 147.18, "pop": 0.36},
    ],
    "Paraguay": [
        {"name": "Asunción", "lat": -25.29, "lon": -57.65, "pop": 0.54},
    ],
    "Peru": [
        {"name": "Lima",      "lat": -12.05, "lon": -77.05, "pop": 10.9},
        {"name": "Arequipa",  "lat": -16.41, "lon": -71.54, "pop":  1.0},
        {"name": "Trujillo",  "lat":  -8.11, "lon": -79.03, "pop":  0.8},
        {"name": "Chiclayo",  "lat":  -6.77, "lon": -79.84, "pop":  0.6},
    ],
    "Philippines": [
        {"name": "Manila",      "lat":  14.60, "lon": 120.98, "pop": 1.85},
        {"name": "Quezon City", "lat":  14.68, "lon": 121.04, "pop": 2.96},
        {"name": "Davao",       "lat":   7.07, "lon": 125.61, "pop": 1.78},
        {"name": "Cebu",        "lat":  10.32, "lon": 123.90, "pop": 0.93},
    ],
    "Poland": [
        {"name": "Warsaw",  "lat":  52.23, "lon":  21.01, "pop": 1.86},
        {"name": "Łódź",    "lat":  51.75, "lon":  19.46, "pop": 0.68},
        {"name": "Kraków",  "lat":  50.06, "lon":  19.94, "pop": 0.78},
        {"name": "Wrocław", "lat":  51.11, "lon":  17.03, "pop": 0.64},
        {"name": "Poznań",  "lat":  52.41, "lon":  16.93, "pop": 0.55},
        {"name": "Gdańsk",  "lat":  54.35, "lon":  18.65, "pop": 0.47},
    ],
    "Portugal": [
        {"name": "Lisbon", "lat":  38.72, "lon":  -9.14, "pop": 0.55},
        {"name": "Porto",  "lat":  41.15, "lon":  -8.61, "pop": 0.24},
    ],
    "Qatar": [
        {"name": "Doha", "lat":  25.29, "lon":  51.53, "pop": 1.45},
    ],
    "Romania": [
        {"name": "Bucharest",  "lat":  44.43, "lon":  26.10, "pop": 1.80},
        {"name": "Cluj-Napoca","lat":  46.77, "lon":  23.59, "pop": 0.32},
        {"name": "Timișoara",  "lat":  45.75, "lon":  21.23, "pop": 0.25},
    ],
    "Russia": [
        {"name": "Moscow",          "lat":  55.75, "lon":  37.62, "pop": 12.5},
        {"name": "Saint Petersburg","lat":  59.93, "lon":  30.32, "pop":  5.4},
        {"name": "Novosibirsk",     "lat":  54.99, "lon":  82.90, "pop":  1.6},
        {"name": "Yekaterinburg",   "lat":  56.85, "lon":  60.60, "pop":  1.5},
        {"name": "Kazan",           "lat":  55.79, "lon":  49.11, "pop":  1.2},
        {"name": "Chelyabinsk",     "lat":  55.15, "lon":  61.43, "pop":  1.2},
        {"name": "Omsk",            "lat":  54.99, "lon":  73.37, "pop":  1.2},
        {"name": "Samara",          "lat":  53.20, "lon":  50.17, "pop":  1.2},
        {"name": "Vladivostok",     "lat":  43.12, "lon": 131.89, "pop":  0.6},
        {"name": "Krasnoyarsk",     "lat":  56.01, "lon":  92.87, "pop":  1.1},
    ],
    "Rwanda": [
        {"name": "Kigali", "lat":  -1.95, "lon":  30.06, "pop": 1.13},
    ],
    "Saudi Arabia": [
        {"name": "Riyadh", "lat":  24.69, "lon":  46.72, "pop": 7.70},
        {"name": "Jeddah", "lat":  21.54, "lon":  39.18, "pop": 4.70},
        {"name": "Mecca",  "lat":  21.39, "lon":  39.86, "pop": 1.70},
        {"name": "Medina", "lat":  24.47, "lon":  39.61, "pop": 1.20},
        {"name": "Dammam", "lat":  26.42, "lon":  50.09, "pop": 0.90},
    ],
    "Senegal": [
        {"name": "Dakar", "lat":  14.71, "lon": -17.47, "pop": 3.60},
        {"name": "Touba", "lat":  14.85, "lon": -15.88, "pop": 1.00},
    ],
    "Serbia": [
        {"name": "Belgrade", "lat":  44.80, "lon":  20.46, "pop": 1.69},
        {"name": "Novi Sad", "lat":  45.25, "lon":  19.84, "pop": 0.29},
    ],
    "Sierra Leone": [
        {"name": "Freetown", "lat":   8.49, "lon": -13.23, "pop": 1.10},
    ],
    "Singapore": [
        {"name": "Singapore", "lat":   1.35, "lon": 103.82, "pop": 5.64},
    ],
    "Slovakia": [
        {"name": "Bratislava","lat":  48.15, "lon":  17.11, "pop": 0.48},
        {"name": "Košice",    "lat":  48.72, "lon":  21.26, "pop": 0.24},
    ],
    "Slovenia": [
        {"name": "Ljubljana", "lat":  46.05, "lon":  14.51, "pop": 0.28},
    ],
    "Somalia": [
        {"name": "Mogadishu","lat":   2.05, "lon":  45.34, "pop": 2.00},
        {"name": "Hargeisa", "lat":   9.56, "lon":  44.06, "pop": 0.76},
    ],
    "South Africa": [
        {"name": "Johannesburg","lat": -26.20, "lon":  28.04, "pop": 5.60},
        {"name": "Cape Town",   "lat": -33.93, "lon":  18.42, "pop": 4.60},
        {"name": "Durban",      "lat": -29.86, "lon":  31.02, "pop": 3.90},
        {"name": "Pretoria",    "lat": -25.75, "lon":  28.19, "pop": 2.92},
        {"name": "Port Elizabeth","lat":-33.97,"lon":  25.57, "pop": 1.15},
    ],
    "South Korea": [
        {"name": "Seoul",   "lat":  37.57, "lon": 126.98, "pop":  9.77},
        {"name": "Busan",   "lat":  35.10, "lon": 129.04, "pop":  3.40},
        {"name": "Incheon", "lat":  37.48, "lon": 126.62, "pop":  2.96},
        {"name": "Daegu",   "lat":  35.88, "lon": 128.61, "pop":  2.43},
        {"name": "Daejeon", "lat":  36.36, "lon": 127.38, "pop":  1.54},
    ],
    "South Sudan": [
        {"name": "Juba", "lat":   4.86, "lon":  31.58, "pop": 0.37},
        {"name": "Wau",  "lat":   7.70, "lon":  28.00, "pop": 0.12},
    ],
    "Spain": [
        {"name": "Madrid",    "lat":  40.42, "lon":  -3.70, "pop": 3.30},
        {"name": "Barcelona", "lat":  41.39, "lon":   2.15, "pop": 1.64},
        {"name": "Valencia",  "lat":  39.47, "lon":  -0.38, "pop": 0.82},
        {"name": "Seville",   "lat":  37.39, "lon":  -5.99, "pop": 0.69},
        {"name": "Bilbao",    "lat":  43.26, "lon":  -2.93, "pop": 0.35},
        {"name": "Zaragoza",  "lat":  41.65, "lon":  -0.89, "pop": 0.67},
    ],
    "Sri Lanka": [
        {"name": "Colombo", "lat":   6.93, "lon":  79.85, "pop": 0.75},
        {"name": "Kandy",   "lat":   7.30, "lon":  80.64, "pop": 0.11},
    ],
    "Sudan": [
        {"name": "Khartoum", "lat":  15.55, "lon":  32.53, "pop": 6.16},
        {"name": "Omdurman", "lat":  15.65, "lon":  32.48, "pop": 2.81},
        {"name": "Port Sudan","lat":  19.62, "lon":  37.22, "pop": 0.49},
    ],
    "Suriname": [
        {"name": "Paramaribo", "lat":   5.85, "lon": -55.20, "pop": 0.24},
    ],
    "Sweden": [
        {"name": "Stockholm", "lat":  59.33, "lon":  18.07, "pop": 1.65},
        {"name": "Gothenburg","lat":  57.71, "lon":  11.97, "pop": 0.59},
        {"name": "Malmö",     "lat":  55.61, "lon":  13.00, "pop": 0.35},
    ],
    "Switzerland": [
        {"name": "Zurich", "lat":  47.38, "lon":   8.54, "pop": 0.43},
        {"name": "Geneva", "lat":  46.21, "lon":   6.15, "pop": 0.20},
        {"name": "Basel",  "lat":  47.56, "lon":   7.59, "pop": 0.18},
        {"name": "Bern",   "lat":  46.95, "lon":   7.45, "pop": 0.14},
    ],
    "Syria": [
        {"name": "Damascus", "lat":  33.51, "lon":  36.29, "pop": 2.50},
        {"name": "Aleppo",   "lat":  36.20, "lon":  37.16, "pop": 2.10},
        {"name": "Homs",     "lat":  34.73, "lon":  36.71, "pop": 0.65},
        {"name": "Latakia",  "lat":  35.52, "lon":  35.79, "pop": 0.38},
    ],
    "Taiwan": [
        {"name": "Taipei",    "lat":  25.05, "lon": 121.53, "pop": 2.65},
        {"name": "Kaohsiung", "lat":  22.62, "lon": 120.31, "pop": 2.77},
        {"name": "Taichung",  "lat":  24.15, "lon": 120.67, "pop": 2.81},
        {"name": "Tainan",    "lat":  23.00, "lon": 120.21, "pop": 1.88},
    ],
    "Tajikistan": [
        {"name": "Dushanbe", "lat":  38.56, "lon":  68.77, "pop": 0.87},
    ],
    "Tanzania": [
        {"name": "Dar es Salaam","lat":  -6.79, "lon":  39.21, "pop": 6.70},
        {"name": "Dodoma",       "lat":  -6.17, "lon":  35.74, "pop": 0.41},
        {"name": "Mwanza",       "lat":  -2.52, "lon":  32.90, "pop": 0.71},
        {"name": "Arusha",       "lat":  -3.37, "lon":  36.68, "pop": 0.42},
    ],
    "Thailand": [
        {"name": "Bangkok",     "lat":  13.75, "lon": 100.52, "pop": 10.5},
        {"name": "Chiang Mai",  "lat":  18.79, "lon":  98.98, "pop":  0.13},
        {"name": "Nonthaburi",  "lat":  13.86, "lon": 100.52, "pop":  0.26},
    ],
    "Timor-Leste": [
        {"name": "Dili", "lat":  -8.56, "lon": 125.58, "pop": 0.22},
    ],
    "Togo": [
        {"name": "Lomé",   "lat":   6.14, "lon":   1.21, "pop": 0.84},
        {"name": "Sokodé", "lat":   8.99, "lon":   1.14, "pop": 0.10},
    ],
    "Trinidad and Tobago": [
        {"name": "Port of Spain", "lat":  10.65, "lon": -61.52, "pop": 0.54},
    ],
    "Tunisia": [
        {"name": "Tunis", "lat":  36.82, "lon":  10.17, "pop": 2.29},
        {"name": "Sfax",  "lat":  34.74, "lon":  10.76, "pop": 0.33},
        {"name": "Sousse","lat":  35.83, "lon":  10.64, "pop": 0.27},
    ],
    "Turkey": [
        {"name": "Istanbul",   "lat":  41.01, "lon":  28.95, "pop": 15.5},
        {"name": "Ankara",     "lat":  39.93, "lon":  32.86, "pop":  5.6},
        {"name": "Izmir",      "lat":  38.42, "lon":  27.14, "pop":  4.4},
        {"name": "Bursa",      "lat":  40.20, "lon":  29.07, "pop":  3.1},
        {"name": "Adana",      "lat":  37.00, "lon":  35.32, "pop":  2.2},
        {"name": "Gaziantep",  "lat":  37.06, "lon":  37.38, "pop":  2.1},
    ],
    "Turkmenistan": [
        {"name": "Ashgabat",    "lat":  37.94, "lon":  58.38, "pop": 0.81},
        {"name": "Türkmenabat", "lat":  39.09, "lon":  63.57, "pop": 0.23},
    ],
    "UAE": [
        {"name": "Dubai",     "lat":  25.20, "lon":  55.27, "pop": 3.33},
        {"name": "Abu Dhabi", "lat":  24.45, "lon":  54.37, "pop": 1.48},
        {"name": "Sharjah",   "lat":  25.36, "lon":  55.40, "pop": 1.40},
    ],
    "Uganda": [
        {"name": "Kampala", "lat":   0.32, "lon":  32.58, "pop": 3.60},
        {"name": "Gulu",    "lat":   2.78, "lon":  32.30, "pop": 0.15},
    ],
    "Ukraine": [
        {"name": "Kyiv",          "lat":  50.45, "lon":  30.52, "pop": 2.96},
        {"name": "Kharkiv",       "lat":  49.99, "lon":  36.23, "pop": 1.43},
        {"name": "Odessa",        "lat":  46.48, "lon":  30.73, "pop": 1.01},
        {"name": "Dnipro",        "lat":  48.47, "lon":  35.05, "pop": 0.98},
        {"name": "Zaporizhzhia",  "lat":  47.84, "lon":  35.17, "pop": 0.72},
        {"name": "Lviv",          "lat":  49.84, "lon":  24.03, "pop": 0.72},
        {"name": "Donetsk",       "lat":  48.01, "lon":  37.80, "pop": 0.90},
    ],
    "United Kingdom": [
        {"name": "London",     "lat":  51.51, "lon":  -0.13, "pop": 9.54},
        {"name": "Birmingham", "lat":  52.48, "lon":  -1.90, "pop": 2.60},
        {"name": "Manchester", "lat":  53.48, "lon":  -2.24, "pop": 2.73},
        {"name": "Glasgow",    "lat":  55.86, "lon":  -4.25, "pop": 1.68},
        {"name": "Leeds",      "lat":  53.80, "lon":  -1.55, "pop": 0.79},
        {"name": "Liverpool",  "lat":  53.41, "lon":  -2.98, "pop": 0.86},
        {"name": "Edinburgh",  "lat":  55.95, "lon":  -3.19, "pop": 0.53},
    ],
    "United States": [
        {"name": "New York",     "lat":  40.71, "lon":  -74.01, "pop": 18.8},
        {"name": "Los Angeles",  "lat":  34.05, "lon": -118.24, "pop": 13.2},
        {"name": "Chicago",      "lat":  41.85, "lon":  -87.65, "pop":  9.5},
        {"name": "Houston",      "lat":  29.76, "lon":  -95.37, "pop":  7.3},
        {"name": "Phoenix",      "lat":  33.45, "lon": -112.07, "pop":  4.9},
        {"name": "Dallas",       "lat":  32.79, "lon":  -96.77, "pop":  7.6},
        {"name": "Washington DC","lat":  38.91, "lon":  -77.04, "pop":  6.4},
        {"name": "Philadelphia", "lat":  39.95, "lon":  -75.17, "pop":  6.2},
        {"name": "Atlanta",      "lat":  33.75, "lon":  -84.39, "pop":  6.2},
        {"name": "Seattle",      "lat":  47.61, "lon": -122.33, "pop":  4.0},
        {"name": "Boston",       "lat":  42.36, "lon":  -71.06, "pop":  4.9},
        {"name": "Denver",       "lat":  39.74, "lon": -104.98, "pop":  2.9},
        {"name": "San Antonio",  "lat":  29.43, "lon":  -98.49, "pop":  2.6},
        {"name": "Miami",        "lat":  25.77, "lon":  -80.19, "pop":  6.2},
        {"name": "Minneapolis",  "lat":  44.98, "lon":  -93.27, "pop":  3.7},
    ],
    "Uruguay": [
        {"name": "Montevideo", "lat": -34.86, "lon": -56.17, "pop": 1.40},
    ],
    "Uzbekistan": [
        {"name": "Tashkent",  "lat":  41.30, "lon":  69.27, "pop": 2.90},
        {"name": "Samarkand", "lat":  39.65, "lon":  66.96, "pop": 0.51},
        {"name": "Namangan",  "lat":  41.00, "lon":  71.67, "pop": 0.48},
    ],
    "Venezuela": [
        {"name": "Caracas",     "lat":  10.48, "lon": -66.88, "pop": 2.90},
        {"name": "Maracaibo",   "lat":  10.63, "lon": -71.65, "pop": 1.95},
        {"name": "Valencia",    "lat":  10.18, "lon": -68.00, "pop": 1.40},
        {"name": "Barquisimeto","lat":  10.07, "lon": -69.32, "pop": 1.05},
    ],
    "Vietnam": [
        {"name": "Ho Chi Minh City","lat":  10.82, "lon": 106.63, "pop": 9.00},
        {"name": "Hanoi",           "lat":  21.03, "lon": 105.85, "pop": 8.05},
        {"name": "Da Nang",         "lat":  16.07, "lon": 108.22, "pop": 1.22},
        {"name": "Haiphong",        "lat":  20.87, "lon": 106.69, "pop": 2.03},
    ],
    "Yemen": [
        {"name": "Sanaa",    "lat":  15.35, "lon":  44.21, "pop": 3.90},
        {"name": "Aden",     "lat":  12.78, "lon":  45.04, "pop": 0.86},
        {"name": "Taiz",     "lat":  13.58, "lon":  44.02, "pop": 0.61},
        {"name": "Hudaydah", "lat":  14.80, "lon":  42.95, "pop": 0.61},
    ],
    "Zambia": [
        {"name": "Lusaka", "lat": -15.42, "lon":  28.28, "pop": 2.00},
        {"name": "Ndola",  "lat": -12.96, "lon":  28.64, "pop": 0.50},
        {"name": "Kitwe",  "lat": -12.80, "lon":  28.21, "pop": 0.52},
    ],
    "Zimbabwe": [
        {"name": "Harare",   "lat": -17.83, "lon":  31.05, "pop": 1.54},
        {"name": "Bulawayo", "lat": -20.15, "lon":  28.59, "pop": 0.65},
    ],
}
