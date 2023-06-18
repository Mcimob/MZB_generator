from functools import reduce
import os
import math
import time
import requests
from pykml import parser
from pykml.factory import GX_ElementMaker as GX
import openpyxl
from lxml import etree
from wgs84_ch1903 import GPSConverter
from db.db_utils import (
    saveCoordinateData,
    getCoordinateData,
    deleteCoordinateData,
)
from db.database import db
from db.models import File

KML_FILE_LOCATION = "./files/kml/"
XLSX_FILE_LOCATION = "./files/xlsx/"

POINT_CLOSE_MARGIN = 50

converter = GPSConverter()


def generate_kml(fname, line_name):
    data = getCoordinateData(fname)
    coords = data["coords"][line_name]
    poi = data["poi"][line_name]

    root = getBaseKML()

    appendLineToRoot(root, coords, line_name)
    appendPOIMarkers(root, poi)
    return etree.tostring(root)


def generate_xlsx(fname, line_name):
    poi = getCoordinateData(fname)["poi"][line_name]
    book = openpyxl.load_workbook("files/xlsx/base.xlsx")
    sheet = book["leer"]

    for i, p in enumerate(poi):
        sheet[f"A{i+8}"] = p["name"]
        sheet[f"C{i+8}"] = p["alt"]

        if i != 0:
            sheet[f"E{i+8}"] = (p["dist"] - poi[i - 1]["dist"]) / 1000

    return book


def combineAndSave(file, filename):
    data = createDataFromFile(file)
    saveCoordinateData(filename, data)


def createDataFromFile(file):
    root = parser.parse(file).getroot()
    coords = rootToDetailedCoords(root)

    changed = True
    while changed:
        changed = combineLines(coords)

    markers = getSuppliedMarkers(root, coords)
    poi = generatePOI(
        coords, markers
    )  # POI Are named with available markers or relative position
    return {"coords": coords, "poi": poi, "markers": markers}


def combineLines(coords):
    for key, value in coords.items():
        for k, v in coords.items():
            if key == k:
                continue
            if pointEquals(value[0], v[-1]):
                for c in value:
                    c["dist"] += v[-1]["dist"]
                combinedLine = v[:] + value[1:]
                del coords[key]
                del coords[k]
                coords[f"measure_generated_{getCurrentTimeString()}"] = combinedLine

                return True

            if pointEquals(value[-1], v[0]):
                for c in v:
                    c["dist"] += value[-1]["dist"]
                combinedLine = value[:] + v[1:]
                del coords[key]
                del coords[k]
                coords[f"measure_generated_{getCurrentTimeString()}"] = combinedLine

                return True
    return False


def pointEquals(p1, p2):
    return p1["easting"] == p2["easting"] and p1["northing"] == p2["northing"]


def rootToDetailedCoords(root):
    pms = list(
        filter(
            lambda x: x.get("id")
            and ("measure" in x.get("id") or "linepolygon" in x.get("id")),
            root.Document.getchildren(),
        )
    )

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


def appendLineToRoot(root, coords, name):
    line = [converter.LV03toWGS84(p["easting"], p["northing"], 0)[0:2] for p in coords]
    root.Document.append(createLine(name, line))


def appendPOIMarkers(root, poi):
    poi_conv = [
        converter.LV03toWGS84(p["easting"], p["northing"], 0)[0:2] + (p["name"],)
        for p in poi
        if p["display"]
    ]
    for i, p in enumerate(poi_conv):
        root.Document.append(create_marker(i, p[2], p[1], p[0]))


def saveKML(root, filename, data):
    with open(filename, "wb") as f:
        f.write(etree.tostring(root, pretty_print=True))
    saveCoordinateData(filename.split("/")[-1].split(".")[0], data)
    # New Excel files should be generated


def getBaseKML():
    with open("files/kml/base.kml", "rb") as f:
        return parser.parse(f).getroot()


def removeGenerated(root):
    els = root.Document

    for el in els.getchildren():
        if el.get("id") and "generated" in el.get("id"):
            els.remove(el)
    return root


def create_marker(index, title, east, north):
    marker = parser.fromstring(
        f"""<Placemark id="marker_{index}_generated">
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
    <Placemark id="{id}">
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


def generatePOI(coords, markers):
    out = {}
    for key, item_ in coords.items():
        item = item_.copy()
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
        MAX_ITEMS = 19 - len(markers[key])
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

            if len(poi) > MAX_ITEMS:
                over = True
                margin += 5
                poi = []

        insertMarkersToPOI(poi, poi_tmp[0], poi_tmp[-1], markers[key])

        for i, p in enumerate(poi):
            p["id"] = f"marker_{getCurrentTimeString()}"
            if "name" not in p.keys():
                p["name"] = p["relative"]
            if p["relative"] == "Marker" or i == 0 or i == len(poi) - 1:
                p["display"] = True
            else:
                p["display"] = False
        out[key] = poi
    return out


def insertMarkersToPOI(poi, start, end, markers):
    poi.insert(0, start)
    poi.append(end)
    for m in markers:
        for i, p in enumerate(poi):
            if pointEquals(p, m):
                poi[i] = m
                if i == 0 and pointEquals(p, poi[-1]):
                    poi[-1]["name"] = m["name"]
                break
            if p["dist"] > m["dist"]:
                poi.insert(i, m)
                break


def getSuppliedMarkers(root, coords):
    markersRaw = list(
        filter(
            lambda x: x.get("id") and "marker" in x.get("id"),
            root.Document.getchildren(),
        )
    )
    markersTexts = [p.Point.coordinates.text.split(",") for p in markersRaw]
    markersCoords = [
        converter.WGS84toLV03(float(p[1]), float(p[0]), 0)[0:2] for p in markersTexts
    ]
    markersTitles = [p.name.text for p in markersRaw]

    return sortMarkersByLine(coords, markersCoords, markersTitles)


def resortMarkersByLine(
    breakIndex: int, markers: list[dict]
) -> tuple[list[dict], list[dict]]:
    breakDistance = list(filter(lambda x: x["index"] == breakIndex, markers))[0]["dist"]
    markers_1 = []
    markers_2 = []
    for m in markers:
        if m["index"] >= breakIndex:
            markers_2.append(m.copy())
            markers_2[-1]["index"] -= breakIndex
            markers_2[-1]["dist"] -= breakDistance
            if m["index"] == breakIndex:
                markers_1.append(m.copy())
        else:
            markers_1.append(m.copy())

    return markers_1, markers_2


def sortMarkersByLine(coords, markersCoords, markersTitles=None):
    out = {}

    for key, value in coords.items():
        out[key] = []
        for i, p in enumerate(markersCoords):
            point, dist, index = closestPointOnCoords(
                value,
                {"easting": p[0], "northing": p[1]} if isinstance(p, tuple) else p,
            )
            if markersTitles:
                point["name"] = markersTitles[i]
            else:
                point["name"] = p["name"]

            if dist > POINT_CLOSE_MARGIN:
                continue

            if pointEquals(point, value[index - 1]):
                point["index"] = index - 1
                value[index - 1] = point
            else:
                point["index"] = index
                if pointEquals(point, value[index]):
                    value[index] = point
                else:
                    value.insert(index, point)

            out[key].append(point.copy())

    for key, value in out.items():
        value.sort(key=lambda x: x["dist"])

    return out


def pointsClose(p1, p2):
    dist = (p1["easting"] - p2["easting"]) ** 2 + (p1["northing"] - p2["northing"]) ** 2
    return dist <= POINT_CLOSE_MARGIN


def breakLineAtPoint(fname, line_name, point):
    data = getCoordinateData(fname)
    markers = data["markers"][line_name]
    if point not in [x["id"] for x in markers]:
        return False
    marker = list(filter(lambda x: x["id"] == point, markers))[0]
    index = marker["index"]
    line = data["coords"][line_name][:]

    del data["coords"][line_name]
    del data["poi"][line_name]
    del data["markers"][line_name]

    new_name_1 = f"measure_generated_{getCurrentTimeString()}"
    data["coords"][new_name_1] = line[: index + 1]

    new_name_2 = f"measure_generated_{getCurrentTimeString()}"
    data["coords"][new_name_2] = line[index + 1 :]
    data["coords"][new_name_2].insert(0, line[index].copy())

    firstDist = data["coords"][new_name_2][0]["dist"]
    for p in data["coords"][new_name_2]:
        p["dist"] -= firstDist

    data["markers"][new_name_1], data["markers"][new_name_2] = resortMarkersByLine(
        index, markers
    )
    data["poi"] = generatePOI(data["coords"], data["markers"])
    saveCoordinateData(fname, data)


def getPointDistance(px, py, qx, qy):
    return (px - qx) ** 2 + (py - qy) ** 2


def removeRecord(file_id):
    fname = File.query.get(file_id).fname
    deleteCoordinateData(fname)

    db.session.delete(File.query.get(file_id))
    db.session.commit()


def closestPointOnCoords(coords, point):
    """
    Returns a point dictionary,
    distance to closest point on the line,
    the index of the point which ends the line, the point is closest to (point is between index - 1 and index)
    """
    smallestDist = float("inf")
    linePoint = (0, 0)
    closestA = 0
    index = 0
    for i in range(1, len(coords)):
        newDist, newPoint, a = closestPointOnLine(coords[i - 1], coords[i], point)
        if newDist < smallestDist:
            smallestDist = newDist
            linePoint = newPoint
            closestA = a
            index = i

    dalt = coords[index]["alt"] - coords[index - 1]["alt"]
    ddist = coords[index]["dist"] - coords[index - 1]["dist"]

    return (
        {
            "easting": linePoint[0],
            "northing": linePoint[1],
            "dist": coords[index - 1]["dist"] + closestA * ddist,
            "alt": coords[index - 1]["alt"] + closestA * dalt,
            "relative": "Marker",
        },
        smallestDist,
        index,
    )


def closestPointOnLine(l_begin, l_end, point):
    x1, y1 = l_begin["easting"], l_begin["northing"]
    x2, y2 = l_end["easting"], l_end["northing"]
    x3, y3 = point["easting"], point["northing"]

    dx, dy = x2 - x1, y2 - y1
    det = dx * dx + dy * dy

    a = (dy * (y3 - y1) + dx * (x3 - x1)) / det
    b = (dy * (x3 - x1) + dx * (y1 - y3)) / det

    dist = abs(b) * math.sqrt(det)

    if a < 0:
        a = 0
        closestPoint = (x1, y1)
        dist = distBetweenPoints(l_begin, point)
    elif a > 0:
        a = 1
        closestPoint = (x2, y2)
        dist = distBetweenPoints(l_end, point)
    else:
        closestPoint = (x1 + a * dx, y1 + a * dy)

    return (dist, closestPoint, a)


def distBetweenPoints(p1, p2):
    return math.sqrt(
        (p1["easting"] - p2["easting"]) ** 2 + (p1["northing"] - p2["northing"]) ** 2
    )


def getCurrentTimeString():
    time.sleep(0.002)
    return str(round(time.time() * 1000))


def getCenterCoords(coords):
    out = {}
    for key, value in coords.items():
        top = 0
        bottom = float("inf")
        right = 0
        left = float("inf")

        for c in value:
            top = max(top, c["northing"])
            bottom = min(bottom, c["northing"])
            right = max(right, c["easting"])
            left = min(left, c["easting"])
        out[key] = ((top + bottom) / 2, (left + right) / 2)

    return out


def updatePoiNames(form):
    file_id = form["file_id"]
    fname = File.query.get(file_id).fname
    line_segment = form["linesegment"]

    data = getCoordinateData(fname)

    for key, name in form.items():
        if key.startswith("name"):
            index = int(key.split("_")[1]) - 1
            data["poi"][line_segment][index]["name"] = name
    saveCoordinateData(fname, data)


def updatePoiDisplay(form):
    file_id = form["file_id"]
    fname = File.query.get(file_id).fname
    line_segment = form["linesegment"]

    data = getCoordinateData(fname)

    for i, p in enumerate(data["poi"][line_segment]):
        if f"show_{i+1}" in form.keys():
            p["display"] = True
        else:
            p["display"] = False
    saveCoordinateData(fname, data)
