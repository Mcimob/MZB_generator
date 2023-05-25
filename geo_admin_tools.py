from pykml import parser
from pykml.factory import nsmap
import requests
import json
import openpyxl
import matplotlib.pyplot as plt
from wgs84_ch1903 import GPSConverter
from lxml import etree
from pykml.factory import GX_ElementMaker as GX
import pickle
from functools import reduce
import lxml
from utils import md5
from db.db_utils import saveFileHashData, getFileHashData

KML_FILE_LOCATION = "./files/kml/"
XLSX_FILE_LOCATION = "./files/xlsx/"


def generate(filename):
    root = getRoot(KML_FILE_LOCATION + filename + ".kml")
    removeGeneratedMarkers(root)
    coords = nameToDetailedCoords(filename)["measure_1"]
    poi = getPOI(coords)
    addMarkersToKML(root, poi)
    writeToExcel(poi, XLSX_FILE_LOCATION + filename + ".xlsx")
    saveKML(root, KML_FILE_LOCATION + filename + ".kml")
    return poi, coords


def generatePoiAndCoords(filename):
    coords = nameToDetailedCoords(filename)["measure_1"]
    poi = getPOI(coords)
    return poi, coords


def combineAndSave(file, filename):
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
    coordinate_string = ""
    for c in coords:
        coordinate_string += f"{str(c[1])},{str(c[0])} "
    placemark_string = f"""
    <Placemark id="measure_1">
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
        <coordinates>{coordinate_string}7.1680216340814,47.102926258242924 7.167786661098496,47.10250293939208 7.165687924078411,47.10074393542702 7.165373206045452,47.100464340476734 7.165401025566969,47.100176568170085 7.164431151975736,47.09922078200292 7.164432400144303,47.098977920979074 7.162526695550739,47.09814580133815 7.161856877194022,47.09776639441814 7.1617534614320935,47.09738835557112 7.161676110672602,47.0970643495039 7.161506464999982,47.09675810978932 7.161942066567804,47.0965792646386 7.162075369061782,47.096273757954485 7.161115943240974,47.095866661184 7.1602339651173095,47.0957655738494 7.159944708172968,47.09566592497002 7.159723190379697,47.09520664159254 7.158656449023806,47.095177051337195 7.158036731657829,47.09530146286251 7.157155290581988,47.09510140842784 7.156589967724828,47.09490212686431 7.1562487986447,47.09465842104405 7.156341996707803,47.09446975652559 7.156265539639473,47.09398383913911 7.156827810830437,47.09351186469473 7.154896274708025,47.0926424487225 7.1526019303392365,47.09189914766122 7.152444606954168,47.09176382952453 7.152305881914986,47.09184443730105 7.149656762374237,47.0909607664324 7.14828440065041,47.09023319578998 7.147195034435021,47.08954230965154 7.147169775082866,47.08934435553915 7.14595695612145,47.08835630815762 7.145721012143388,47.0881533170558 7.1452144750447175,47.08806206927871 7.142533409732301,47.087056718153015 7.140470489901509,47.08621482635779 7.137679394435722,47.08490324413348 7.137049119153366,47.08457776453673 7.136832037913378,47.08454121215376 7.135118910405805,47.08358770775514 7.134100735898773,47.08316673462293 7.133581380054738,47.08302592857693 7.133378041577947,47.08289046117273 7.132050052861231,47.082536105348176 7.131123659203353,47.08219180906678 7.130847205292848,47.0821775732604 7.129448076675758,47.081607115506806 7.129284310150601,47.08146275267384 7.129034561583679,47.08138561959087 7.126354449933016,47.08032591991853 7.123510673997332,47.07912628372059 7.1185390204398225,47.077075111368465 7.116509887579913,47.07621488952678 7.116207705248077,47.07610609810702 7.115243522793442,47.07551420276129 7.114529468233478,47.07493200295221 7.114222189243201,47.074580325917125 7.113666507786463,47.073940101732944 7.112432069315174,47.07126056554705 7.106831949855348,47.066717705969616 7.1071237985923945,47.066358749866225 7.105837735215482,47.065707372549895 7.104521099614223,47.065739515571295 7.104237719262708,47.06579490680571 7.101557941762892,47.06488304038287 7.095340153616223,47.062480862559404</coordinates>
      </LineString>
    </Placemark>"""
    root.Document.append(parser.fromstring(placemark_string))
    saveKML(root, filename)


def nameToDetailedCoords(name):
    item = getFileHashData(name)
    if item is None:
        raise Exception(f"No such line {name}")
    generatedFH = md5(KML_FILE_LOCATION + name + ".kml")
    print(item)
    if generatedFH == getattr(item, "filehash"):
        return json.loads(item.coordinate_data)
    return fileToDetailedCoords(KML_FILE_LOCATION + name + ".kml")


def fileToDetailedCoords(fname):
    with open(fname, "rb") as f:
        root = parser.parse(f).getroot()
    pms = root.xpath(
        "//ns:Placemark[starts-with(@id, 'measure_')]", namespaces={"ns": nsmap[None]}
    )
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


def saveKML(root, filename):
    with open(filename, "wb") as f:
        f.write(etree.tostring(root, pretty_print=True))
    fh = md5(filename)
    data = fileToDetailedCoords(filename)
    saveFileHashData(filename.split("/")[-1].split(".")[0], fh, data)
    # New Excel files should be generated


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
    marker = parser.fromstring(
        f"""<Placemark id="marker_{index + 1}_generated">
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


def addMarkersToKML(root, poi):
    converter = GPSConverter()
    for index, p in enumerate(poi):
        north, east, alt = converter.LV03toWGS84(p["easting"], p["northing"], 0)
        marker = create_marker(index, index, east, north)
        root.Document.append(marker)

    return root


def connectLines(lineStrings):
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
    # return pickle.load(open("./api_data.pkl", "rb"))
    arg = {"type": "LineString", "coordinates": coords}
    print("Making an API request")
    return requests.post(
        "https://api3.geo.admin.ch/rest/services/profile.json?sr=21781&distinct_points=True&nb_points=2000",
        json=arg,
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
