from pykml import parser
from pykml.factory import nsmap
import requests
import json
import openpyxl
import matplotlib.pyplot as plt
from wgs84_ch1903 import GPSConverter
from lxml import etree

KML_FILE_LOCATION = "./files/kml/"
XLSX_FILE_LOCATION = "./files/xlsx/"


def generate(filename):
    root = getRoot(KML_FILE_LOCATION + filename + ".kml")
    removeGeneratedMarkers(root)
    coords = kmlToLV03Coords(root)
    coords = getDetailedCoords(coords)
    getRightAlts(coords)
    poi = getPOI(coords)
    text = etree.tostring(root)
    with open(KML_FILE_LOCATION + filename + ".kml", "w") as f:
        addMarkersToKML(
            f,
            poi,
            text,
        )
    writeToExcel(poi, XLSX_FILE_LOCATION + filename + ".xlsx")


def getRoot(filename):
    with open(filename, "rb") as f:
        return parser.parse(f).getroot()


def removeGeneratedMarkers(root):
    els = root.Document

    for el in els.getchildren():
        if el.get("id") and "generated" in el.get("id"):
            els.remove(el)
    return root


def create_marker(index, title, east, north):
    return f"""<Placemark id="marker_{index + 1}_generated">
  <ExtendedData>
    <Data name="type">
      <value>marker</value>
    </Data>
  </ExtendedData>
  <name>Marker {title}</name>
  <description></description>
  <Style>
    <IconStyle>
      <Icon>
        <href>https://api3.geo.admin.ch/color/255,0,0/marker-24@2x.png</href>
        <gx:w>48</gx:w>
        <gx:h>48</gx:h>
      </Icon>
      <hotSpot x="24" y="4.799999999999997" xunits="pixels" yunits="pixels"/>
    </IconStyle>
    <LabelStyle>
      <color>ff0000ff</color>
    </LabelStyle>
  </Style>
  <Point>
    <tessellate>1</tessellate>
    <altitudeMode>clampToGround</altitudeMode>
    <coordinates>{east},{north}</coordinates>
  </Point>
</Placemark>"""


def addMarkersToKML(outFile, poi, template):
    converter = GPSConverter()
    markers = []
    for index, p in enumerate(poi):
        north, east, alt = converter.LV03toWGS84(p["easting"], p["northing"], 0)
        marker = create_marker(index, index, east, north)
        markers.append(marker)

    index = template.find("</Document>")
    outFile.write(template[0:index])
    for m in markers:
        outFile.write(m)
    outFile.write(template[index:-1])
    return


def kmlToLV03Coords(root):
    pms = root.xpath(
        ".//ns:Placemark[.//ns:LineString]", namespaces={"ns": nsmap[None]}
    )
    coords = []
    converter = GPSConverter()
    print(pms)
    for coord in pms[0].LineString.coordinates.text.split(" "):
        xy = coord.split(",")
        print(float(xy[0]), float(xy[1]))
        coords.append(
            converter.WGS84toLV03(float(xy[1]), float(xy[0]), 0, clip=True)[0:2]
        )

    return coords


def getDetailedCoords(coords):
    arg = json.dumps({"type": "LineString", "coordinates": coords})
    return requests.get(
        f"https://api3.geo.admin.ch/rest/services/profile.json?geom={arg}&sr=21781&distinct_points=True",
        timeout=3,
    ).json()


def getRightAlts(coords):
    for p in coords:
        p["alt"] = p["alts"]["DTM2"]
        del p["alts"]


def getPOI(coords):
    for i, c in enumerate(coords):
        c["relative"] = (
            "Start"
            if i == 0
            else "End"
            if i == len(coords) - 1
            else "High"
            if (coords[i - 1]["alt"] < c["alt"] and c["alt"] > coords[i + 1]["alt"])
            else "Low"
            if (coords[i - 1]["alt"] > c["alt"] and c["alt"] < coords[i + 1]["alt"])
            else None
        )

    poi_tmp = [c for c in coords if c["relative"]]
    poi = []
    over = True
    margin = 0
    while over:
        over = False

        for i in range(1, len(poi_tmp) - 1):
            if (
                max(
                    abs(poi_tmp[i]["alt"] - poi_tmp[i - 1]["alt"]),
                    abs(poi_tmp[i]["alt"] - poi_tmp[i + 1]["alt"]),
                )
                >= margin
            ):
                poi.append(poi_tmp[i])

        poi.append(poi_tmp[-1])
        poi.insert(0, poi_tmp[0])

        if len(poi) > 21:
            over = True
            margin += 5
            poi = []
    return poi


def writeToExcel(poi, filename):
    book = openpyxl.load_workbook("MZB_template.xlsx")
    sheet = book["leer"]

    for i, p in enumerate(poi):
        sheet[f"A{i+8}"] = f"Point {i+1}"
        sheet[f"C{i+8}"] = p["alt"]

        if i != 0:
            sheet[f"E{i+8}"] = (p["dist"] - poi[i - 1]["dist"]) / 1000
            print(sheet[f"E{i+8}"])

    book.save(filename)


""" x = [p['dist'] for p in coords]
y = [p['alt'] for p in coords]
fig, ax = plt.subplots()

ax.plot(x, y)

plt.show() """
