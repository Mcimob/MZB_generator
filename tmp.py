from geo_admin_tools import *
from pykml import parser
from pykml.factory import KML_ElementMaker as KML
from pykml.factory import GX_ElementMaker as GX
from lxml import etree

filename = "./files/kml/map2.kml"

with open(filename, "rb") as f:
    root = parser.parse(f).getroot()

els = root.Document
print(els.getchildren())

for el in els.getchildren():
    if el.get("id") and "generated" in el.get("id"):
        els.remove(el)

text = """<Placemark id="marker_21_generated">
  <ExtendedData>
    <Data name="type">
      <value>marker</value>
    </Data>
  </ExtendedData>
  <name>Marker 20</name>
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
    <coordinates>7.854566722316687,47.39759705076591</coordinates>
  </Point>
</Placemark>"""

newMarker = parser.fromstring(text)
icon = newMarker.Style.IconStyle.Icon

icon.append(GX.w(48))
icon.append(GX.h(48))

print(icon.getchildren())
print(etree.tostring(icon, pretty_print=True))

print(root)
