import urllib.request
import sys
sys.path.append("e:\\VEDAGYA\\Thermal Trace\\Thermal-Trace\\backend")
from app.integrations.firms.normalizer import parse_firms_csv

url = "https://firms.modaps.eosdis.nasa.gov/api/area/csv/5466cd62ba42d916d50fcd014d873499/VIIRS_SNPP_NRT/68.0,6.0,98.0,38.0/5"

try:
    with urllib.request.urlopen(url) as response:
        csv_text = response.read().decode("utf-8")
        records = parse_firms_csv(csv_text, "VIIRS_SNPP_NRT")
        print("Total returned records after filtering:", len(records))
except Exception as e:
    print("Error:", e)
