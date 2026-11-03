"""Genera los datos de Radar Nexenia a partir del extracto de OpenStreetMap de España.
Lee GeoJSONSeq (osmium export) y escribe teselas de 0,25° en radar/data/."""
import json, sys, os, math, re, datetime
SECT = {"hosteleria": [["amenity", "restaurant|cafe|bar|fast_food|pub|ice_cream|biergarten"]], "belleza": [["shop", "hairdresser|beauty|cosmetics|massage|tattoo|nails"], ["leisure", "fitness_centre"]], "salud": [["amenity", "dentist|clinic|doctors|veterinary"], ["healthcare", "physiotherapist|psychotherapist|podiatrist|optometrist|alternative|dentist|clinic"]], "motor": [["shop", "car|car_repair|tyres|car_parts|motorcycle"], ["amenity", "car_wash|driving_school|car_rental"]], "alojamiento": [["tourism", "hotel|guest_house|hostel|apartment|motel|camp_site"]], "profesional": [["office", "lawyer|accountant|estate_agent|insurance|architect|tax_advisor|notary|financial|travel_agent|employment_agency"], ["shop", "travel_agency"]], "comercio": [["shop", "clothes|shoes|furniture|electronics|bakery|butcher|florist|optician|jewelry|bicycle|hardware|pet|sports|toys|gift|mobile_phone|books|kitchen|interior_decoration|bed|garden_centre|wine|deli|confectionery|pastry"]], "oficios": [["craft", "electrician|plumber|carpenter|painter|builder|hvac|roofer|glaziery|locksmith|metal_construction|gardener|tiler"], ["shop", "doityourself|trade"]], "formacion": [["amenity", "kindergarten|language_school|music_school|dancing_school|prep_school|driving_school"], ["leisure", "sports_centre|dance"]]}
TILE = 0.25
rules = [(s, k, re.compile("^(" + v + ")$")) for s, qs in SECT.items() for k, v in qs]
def classify(t):
    for s, k, rx in rules:
        val = t.get(k)
        if val and rx.match(val):
            return s, val
    return None
def centroid(g):
    tp, c = g["type"], g["coordinates"]
    if tp == "Point": return c[1], c[0]
    pts = []
    def walk(x):
        if isinstance(x[0], (int, float)): pts.append(x)
        else:
            for y in x: walk(y)
    walk(c)
    if not pts: return None
    return sum(p[1] for p in pts)/len(pts), sum(p[0] for p in pts)/len(pts)
def phone(p):
    p = (p or "").split(";")[0].strip()
    return re.sub(r"^\+34\s?", "", p)
tiles, n = {}, 0
for line in open(sys.argv[1], encoding="utf-8"):
    line = line.strip().lstrip("\x1e")
    if not line: continue
    f = json.loads(line)
    t = f.get("properties") or {}
    name = t.get("name")
    if not name: continue
    cl = classify(t)
    if not cl: continue
    c = centroid(f["geometry"])
    if not c: continue
    lat, lon = round(c[0], 5), round(c[1], 5)
    addr = " ".join(x for x in [t.get("addr:street"), t.get("addr:housenumber")] if x)
    if t.get("addr:city"): addr += (", " if addr else "") + t["addr:city"]
    fid = str(f.get("id", "")).replace("/", "")
    row = [fid, name, cl[0], cl[1], lat, lon,
           t.get("website") or t.get("contact:website") or t.get("url") or "",
           phone(t.get("phone") or t.get("contact:phone") or t.get("mobile") or t.get("contact:mobile")),
           t.get("email") or t.get("contact:email") or "",
           t.get("opening_hours") or "",
           t.get("contact:instagram") or "", t.get("contact:facebook") or "",
           addr, t.get("brand") or ""]
    key = f"{math.floor(lat/TILE)}_{math.floor(lon/TILE)}"
    tiles.setdefault(key, []).append(row); n += 1
out = sys.argv[2]; os.makedirs(out, exist_ok=True)
for fn in os.listdir(out):
    if fn.startswith("t_"): os.remove(os.path.join(out, fn))
for k, rows in tiles.items():
    with open(os.path.join(out, f"t_{k}.json"), "w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, separators=(",", ":"))
with open(os.path.join(out, "index.json"), "w") as fh:
    json.dump({"updated": datetime.date.today().isoformat(), "count": n, "tile": TILE,
               "fields": ["id","n","s","k","lat","lon","w","p","e","h","ig","fb","a","br"],
               "tiles": sorted(tiles)}, fh)
print(n, "negocios en", len(tiles), "teselas")
