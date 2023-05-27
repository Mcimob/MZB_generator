from functools import reduce
import os
import requests
from pykml import parser
from pykml.factory import nsmap, GX_ElementMaker as GX
import openpyxl
from lxml import etree
import lxml
from wgs84_ch1903 import GPSConverter
from db.db_utils import saveCoordinateData, getCoordinateData, deleteCoordinateData

KML_FILE_LOCATION = "./files/kml/"
XLSX_FILE_LOCATION = "./files/xlsx/"


def generate(filename):
    kml_fname = KML_FILE_LOCATION + filename + ".kml"
    root = getRoot(kml_fname)
    data = getCoordinateData(filename)
    data["poi"] = generatePOI(data["coords"], root)
    removeGenerated(root)
    coordinateDataToFile(root, data)
    saveKML(root, kml_fname, data)
    return data


def combineAndSave(file, filename):
    root = combine(file)
    data = createDataFromFile(root)
    addMarkers(root, data["poi"])
    saveKML(root, filename, data)


def combine(file):
    root = parser.parse(file).getroot()
    pms = root.xpath(
        ".//ns:Placemark[.//ns:LineString]", namespaces={"ns": nsmap[None]}
    )
    coords = connectLines(pms)
    for el in root.Document.getchildren():
        if not isinstance(el, lxml.objectify.StringElement):
            element_type = next(
                filter(lambda x: x.get("name") == "type", el.ExtendedData.getchildren())
            ).value.text
            if element_type in ["measure", "linepolygon"]:
                root.Document.remove(el)
    root.Document.append(createLine("measure_1", coords))

    return root


def createDataFromFile(root):
    coords = rootToDetailedCoords(root)
    poi = generatePOI(
        coords, root
    )  # POI Are named with available markers or relative position
    return {"coords": coords, "poi": poi}


def rootToDetailedCoords(root):
    pms = list(
        filter(
            lambda x: x.get("id") and "measure" in x.get("id"),
            root.Document.getchildren(),
        )
    )
    print(pms)

    converter = GPSConverter()
    data = {}
    for pm in pms:
        pm_id = pm.get("id")
        data[pm_id] = []
        coords = parseLineString(pm)
        for i, coord in enumerate(coords):
            data[pm_id].append(
                converter.WGS84toLV03(coord[0], coord[1], 0, clip=True)[0:2]
            )
        data[pm_id] = getDetailedCoords(data[pm_id])
        getRightAlts(data[pm_id])
    return data


def coordinateDataToFile(root, data):
    converter = GPSConverter()
    for key, l in data["coords"].items():
        line = [converter.LV03toWGS84(p["easting"], p["northing"], 0)[0:2] for p in l]
        root.Document.append(createLine(key, line))

    for key, l in data["poi"].items():
        poi = [converter.LV03toWGS84(p["easting"], p["northing"], 0)[0:2] for p in l]
        for i, p in enumerate(poi):
            root.Document.append(create_marker(i, data["poi"][i]["name"], p[1], p[0]))

    return root


def saveKML(root, filename, data):
    with open(filename, "wb") as f:
        f.write(etree.tostring(root, pretty_print=True))
    saveCoordinateData(filename.split("/")[-1].split(".")[0], data)
    # New Excel files should be generated


def getRoot(filename):
    with open(filename, "rb") as f:
        return parser.parse(f).getroot()


def removeGenerated(root):
    els = root.Document

    for el in els.getchildren():
        if el.get("id") and "generated" in el.get("id"):
            els.remove(el)
    return root


def create_marker(index, title, east, north):
    marker = parser.fromstring(
        f"""<Placemark id="marker_{title}_{index}_generated">
  <ExtendedData>
    <Data name="type">
      <value>marker</value>
    </Data>
  </ExtendedData>
  <name>{title}</name>
  <description></description>
  <Style>
    <IconStyle>
      <Icon>
        <href>https://api3.geo.admin.ch/color/255,0,0/marker-24@2x.png</href>
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
    )
    icon = marker.Style.IconStyle.Icon
    icon.append(GX.w(48))
    icon.append(GX.h(48))

    return marker


def createLine(id: str, coordinates: list[list[float]]):
    coordinate_string = ""

    for i, c in enumerate(coordinates):
        coordinate_string += f"{str(c[1])},{str(c[0])}"
        if i != len(coordinates) - 1:
            coordinate_string += " "

    placemark_string = f"""
    <Placemark id="{id}_generated">
      <ExtendedData>
        <Data name="overlays"/>
        <Data name="type">
          <value>measure</value>
        </Data>
      </ExtendedData>
      <Style>
        <LineStyle>
          <color>ff0000ff</color>
          <width>3</width>
        </LineStyle>
        <PolyStyle>
          <color>660000ff</color>
        </PolyStyle>
      </Style>
      <LineString>
        <tessellate>1</tessellate>
        <altitudeMode>clampToGround</altitudeMode>
        <coordinates>{coordinate_string}</coordinates>
      </LineString>
    </Placemark>"""

    return parser.fromstring(placemark_string)


def addMarkers(root, poi):
    converter = GPSConverter()
    for key, item in poi.items():
        for index, p in enumerate(item):
            north, east, alt = converter.LV03toWGS84(p["easting"], p["northing"], 0)
            marker = create_marker(index, p["name"], east, north)
            root.Document.append(marker)
    return root


def connectLines(lineStrings):
    # TODO: Fix Doubling of edge vertices
    lines = []
    for line in lineStrings:
        coords = parseLineString(line)
        lines.append(coords)
    return reduce(lambda a, b: a + b, lines)


def parseLineString(placemark):
    return [
        (float(xy.split(",")[1]), float(xy.split(",")[0]))
        for xy in placemark.LineString.coordinates.text.split(" ")
    ]


def getDetailedCoords(coords):
    arg = {"type": "LineString", "coordinates": coords}
    print("Making an API request")
    return requests.post(
        "https://api3.geo.admin.ch/rest/services/profile.json?sr=21781&distinct_points=True",
        json=arg,
        timeout=3,
    ).json()


def getRightAlts(coords):
    for p in coords:
        p["alt"] = p["alts"]["DTM2"]
        del p["alts"]


def generatePOI(coords, root):
    out = {}
    for key, item in coords.items():
        for i, c in enumerate(item):
            c["relative"] = (
                "Start"
                if i == 0
                else "End"
                if i == len(item) - 1
                else "High"
                if (item[i - 1]["alt"] < c["alt"] and c["alt"] > item[i + 1]["alt"])
                else "Low"
                if (item[i - 1]["alt"] > c["alt"] and c["alt"] < item[i + 1]["alt"])
                else None
            )

        poi_tmp = [c for c in item if c["relative"]]
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
        for i, p in enumerate(poi):
            p["id"] = f"marker_{i}"
            p["name"] = p["relative"]
        getPointNames(poi, root)
        out[key] = poi
    return out


def getPointNames(coords, root):
    converter = GPSConverter()
    suppliedMarkers = list(
        filter(
            lambda x: x.get("id")
            and "marker" in x.get("id")
            and "generated" not in x.get("id"),
            root.Document.getchildren(),
        )
    )
    suppliedPoints = [p.Point.coordinates.text.split(",") for p in suppliedMarkers]
    suppliedPoints = [
        converter.WGS84toLV03(float(p[1]), float(p[0]), 0)[0:2] for p in suppliedPoints
    ]
    for c in coords:
        for i, p in enumerate(suppliedPoints):
            if pointsClose([c["easting"], c["northing"]], p):
                c["name"] = suppliedMarkers[i].name.text


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


def pointsClose(p1, p2):
    MARGIN = 50
    dist = (p1[0] - p2[0]) * (p1[0] - p2[0]) + (p1[1] - p2[1]) * (p1[1] - p2[1])
    return dist <= MARGIN


def removeRecord(name):
    deleteCoordinateData(name)
    os.remove(KML_FILE_LOCATION + name + ".kml")
    if (XLSX_FILE_LOCATION + name + ".xlsx") in os.listdir("./files/xlsx/"):
        os.remove(XLSX_FILE_LOCATION + name + ".xlsx")
