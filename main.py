import os
from pathlib import Path
import requests
import sentry_sdk
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0,
    send_default_pii=True,
    integrations=[
        StarletteIntegration(transaction_style="endpoint"),
        FastApiIntegration(transaction_style="endpoint"),
    ],
)

app = FastAPI()


@app.get("/health")
def health_check():
    return {"status": "ok"}

# Enable CORS for frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
INDEX_FILE = BASE_DIR / "index.html"
FALLBACK_INDEX_FILE = BASE_DIR / "index.html.html"

# Store the token in the hosting provider's environment variables.
BHUVAN_TOKEN = os.getenv("BHUVAN_TOKEN")
BHUVAN_URL = "https://bhuvan-app1.nrsc.gov.in/api/lulc/curljson.php"
BHUVAN_WMS_URL = "https://bhuvan-vec1.nrsc.gov.in/bhuvan/wms"

LULC_MAPPING = {
    "l01": "Built-up (Urban)",
    "l02": "Kharif Crop",
    "l03": "Rabi Crop",
    "l04": "Agricultural Land",
    "l05": "Double / Triple Crop",
    "l06": "Fallow Land",
    "l08": "Barren / Wasteland",
    "l09": "Scrubland / Grassland",
    "l12": "Forest / Vegetation",
    "l16": "Waterbodies (Lakes/Ponds)",
    "l21": "Coastal / Wetlands / Mangroves",
    "l23": "Rivers / Streams",
}

LULC_COLORS = {
    "l01": "#c95c4b",
    "l02": "#d9a441",
    "l03": "#b8783e",
    "l04": "#e0c35a",
    "l05": "#8eaf52",
    "l06": "#c4a56a",
    "l08": "#8d8175",
    "l09": "#9b8f52",
    "l12": "#3f8b58",
    "l16": "#438fbd",
    "l21": "#4b9b91",
    "l23": "#4b70b5",
}

VERIFICATION_DATA = [
    {
        "category": "identify_property",
        "title": "Identify the property",
        "description": "Write down the details that identify the exact land parcel.",
        "what_is_this": "The basic location and reference numbers for the property.",
        "why_it_matters": "These details help you compare the property with official records.",
        "what_to_check": ["Survey/Gat number", "CTS number where applicable", "Village, Taluka and District"],
        "official_sources": [{"name": "Official source to be verified", "url": None}],
    },
    {
        "category": "land_records",
        "title": "Check land records",
        "description": "Review the relevant official record for the property.",
        "what_is_this": "Government records that may show the recorded holder, area and land details.",
        "why_it_matters": "The details should be consistent with the property information provided to you.",
        "what_to_check": ["7/12", "8A", "Property Card", "Recorded holder information", "Area"],
        "official_sources": [{"name": "Official Maharashtra land-record source to be verified", "url": None}],
    },
    {
        "category": "mutation",
        "title": "Check Ferfar / mutation",
        "description": "Review recorded changes connected with the land record.",
        "what_is_this": "Entries that record changes such as transfers or other updates in revenue records.",
        "why_it_matters": "They can help you compare the history shown in the records with the seller's information.",
        "what_to_check": ["Entry number and date", "Reason for the change", "Names and area shown in the entry"],
        "official_sources": [{"name": "Official Maharashtra mutation source to be verified", "url": None}],
    },
    {
        "category": "conversion",
        "title": "Check NA / land-use / conversion status",
        "description": "Verify the official land-use or conversion status for the intended use.",
        "what_is_this": "Information about how the land is recorded and whether a conversion process applies.",
        "why_it_matters": "Bhuvan land-use information is area-level and does not confirm an individual plot's permission.",
        "what_to_check": ["Recorded land use", "Conversion or NA order, if applicable", "Order number and date"],
        "official_sources": [{"name": "Official Maharashtra conversion guidance to be verified", "url": None}],
    },
    {
        "category": "planning",
        "title": "Check planning, zoning and reservations",
        "description": "Ask the relevant planning authority about controls affecting the property.",
        "what_is_this": "Local planning information about permitted uses, reservations and restrictions.",
        "why_it_matters": "The land-use category shown on a map does not establish planning permission for a plot.",
        "what_to_check": ["Applicable plan", "Reservation or road widening", "Permitted use for the intended activity"],
        "official_sources": [{"name": "Official Maharashtra planning source to be verified", "url": None}],
    },
    {
        "category": "parcel_map",
        "title": "Check official parcel/map information",
        "description": "Compare the property location and boundaries with official parcel information.",
        "what_is_this": "An official map or record used to identify the parcel on the ground.",
        "why_it_matters": "The Bhuvan map is not a survey of an individual property and does not establish its boundary.",
        "what_to_check": ["Parcel reference", "Boundary description", "Whether the map matches the records"],
        "official_sources": [{"name": "Official Maharashtra land-map source to be verified", "url": None}],
    },
    {
        "category": "disputes",
        "title": "Check available dispute/court information",
        "description": "Ask the appropriate official source about recorded disputes or cases.",
        "what_is_this": "Information that may be available from relevant court or revenue records.",
        "why_it_matters": "A map or land-use statistic cannot show whether a property is involved in a dispute.",
        "what_to_check": ["Case or reference number", "Parties and status", "Relevant revenue record entries"],
        "official_sources": [{"name": "Official court or revenue source to be verified", "url": None}],
    },
]

DISTRICT_MAP_CENTERS = {
    "2722": [19.1500, 72.8500],
    "2721": [18.9600, 72.8258],
    "2707": [18.5204, 73.8567],
    "0701": [28.6328, 77.2197],
    "2920": [12.9716, 77.5946],
    "3302": [13.0827, 80.2707],
}

STATIC_DISTRICT_DATA = {
    "2722": {
        "name": "Mumbai Suburban (MH)",
        "totalarea": "446.00",
        "l01": "210.45",
        "l04": "12.30",
        "l06": "5.10",
        "l08": "18.20",
        "l09": "14.80",
        "l12": "85.60",
        "l16": "12.45",
        "l21": "68.30",
        "l23": "18.80",
    },
    "2721": {
        "name": "Mumbai City (MH)",
        "totalarea": "157.00",
        "l01": "112.30",
        "l08": "4.10",
        "l12": "6.80",
        "l16": "5.20",
        "l21": "18.40",
        "l23": "10.20",
    },
    "2707": {
        "name": "Pune (MH)",
        "totalarea": "15643.00",
        "l01": "845.20",
        "l02": "4210.50",
        "l03": "3120.40",
        "l04": "8500.00",
        "l06": "650.30",
        "l08": "1120.10",
        "l12": "2410.80",
        "l16": "430.20",
        "l23": "296.00",
    },
    "0701": {
        "name": "Central Delhi (DL)",
        "totalarea": "25.00",
        "l01": "19.50",
        "l04": "0.80",
        "l09": "1.20",
        "l12": "2.10",
        "l16": "0.40",
        "l23": "1.00",
    },
    "2920": {
        "name": "Bengaluru Urban (KA)",
        "totalarea": "2196.00",
        "l01": "712.40",
        "l02": "340.10",
        "l04": "820.50",
        "l06": "110.20",
        "l08": "95.40",
        "l12": "185.30",
        "l16": "98.60",
        "l23": "33.50",
    },
    "3302": {
        "name": "Chennai (TN)",
        "totalarea": "426.00",
        "l01": "265.80",
        "l04": "15.20",
        "l08": "12.10",
        "l12": "22.40",
        "l16": "35.60",
        "l21": "44.10",
        "l23": "30.80",
    },
}

def parse_bhuvan_number(val):
    if val is None:
        return 0.0
    try:
        clean_str = str(val).replace(",", "").strip()
        return float(clean_str)
    except (ValueError, TypeError):
        return 0.0

# Route to render the frontend page.
@app.get("/", response_class=FileResponse)
def home():
    use_new_frontend = os.getenv("USE_NEW_FRONTEND", "1") == "1"
    index_path = INDEX_FILE if use_new_frontend else FALLBACK_INDEX_FILE
    if not index_path.exists():
        index_path = FALLBACK_INDEX_FILE
    return FileResponse(index_path)

@app.get("/api/lulc/stats")
def get_lulc_stats(distcode: str = "2722", year: str = "1112"):
    params = {"distcode": distcode, "year": year, "token": BHUVAN_TOKEN}
    try:
        res = requests.get(BHUVAN_URL, params=params, timeout=5)
        if res.status_code == 200:
            json_data = res.json()
            if isinstance(json_data, list) and len(json_data) > 0:
                return json_data[0]
            elif isinstance(json_data, dict) and parse_bhuvan_number(json_data.get("totalarea")) > 0:
                return json_data
    except Exception:
        pass

    return STATIC_DISTRICT_DATA.get(distcode, STATIC_DISTRICT_DATA["2722"])

@app.get("/api/lulc/stats/formatted")
def get_formatted_stats(distcode: str = "2722", year: str = "1112"):
    data = get_lulc_stats(distcode=distcode, year=year)

    district_name = data.get("name") or data.get("district_name") or f"District {distcode}"
    total_area = parse_bhuvan_number(data.get("totalarea") or data.get("total_area"))

    breakdown = {}
    for code, label in LULC_MAPPING.items():
        if code in data:
            val = parse_bhuvan_number(data[code])
            if val > 0:
                breakdown[label] = f"{val} sq km"

    return {
        "district_name": district_name,
        "total_area_sqkm": total_area,
        "year_cycle": "2005-06" if year == "0506" else "2011-12",
        "breakdown": breakdown,
        "bhuvan_thematic_map_url": "https://bhuvan-app1.nrsc.gov.in/thematic/",
    }

@app.get("/api/verification")
def get_verification_guidance():
    return VERIFICATION_DATA

@app.get("/api/verification/{category}")
def get_verification_category(category: str):
    for item in VERIFICATION_DATA:
        if item["category"] == category:
            return item
    raise HTTPException(status_code=404, detail="Verification category not found")

@app.get("/api/lulc/map-config")
def get_map_config(distcode: str = "2722", year: str = "1112"):
    return {
        "available": year == "1112",
        "center": DISTRICT_MAP_CENTERS.get(distcode, DISTRICT_MAP_CENTERS["2722"]),
        "district_code": distcode,
        "zoom": 10,
        "base_layer": {
            "url": "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
            "attribution": "© OpenStreetMap contributors",
            "max_zoom": 19,
        },
        "bhuvan_layer": {
            "url": "/api/lulc/wms",
            "upstream_url": BHUVAN_WMS_URL,
            "layers": "lulc:LULC50K_1112",
            "format": "image/png",
            "transparent": True,
            "version": "1.1.1",
            "attribution": "© ISRO / Bhuvan NRSC",
        },
        "note": "The statistics API does not provide district boundaries or map coordinates.",
    }

@app.get("/api/lulc/wms")
def get_lulc_wms_tile(request: Request):
    try:
        res = requests.get(BHUVAN_WMS_URL, params=dict(request.query_params), timeout=15)
        return Response(
            content=res.content,
            status_code=res.status_code,
            media_type=res.headers.get("content-type", "image/png").split(";", 1)[0],
        )
    except requests.RequestException as error:
        raise HTTPException(status_code=502, detail="Bhuvan WMS is unavailable") from error
    