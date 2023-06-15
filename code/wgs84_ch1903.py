#!/usr/bin/python3
#-*- coding: utf-8 -*-

# The MIT License (MIT)
#
# Copyright (c) 2014 Federal Office of Topography swisstopo, Wabern, CH and Aaron Schmocker
# Copyright (c) 2020 Marcel Waldvogel
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

# WGS84 <-> LV03 converter based on the scripts of swisstopo written for python2.7
# Aaron Schmocker [aaron@duckpond.ch]
# Marcel Waldvogel [marcel.waldvogel@trifence.ch]
# - Pythonized (simplified, Python3, PEP-8)
# vim: tabstop=4 shiftwidth=4 softtabstop=4 expandtab

# Source: https://www.swisstopo.admin.ch/en/knowledge-facts/surveying-geodesy/reference-systems/map-projections.html (see PDFs under "Documentation")
# Updated 9 dec 2014
# Please validate your results with NAVREF on-line service: https://www.swisstopo.admin.ch/en/maps-data-online/calculation-services/navref.html (difference ~ 1-2m)


class GPSConverter(object):
    '''
    GPS Converter class which is able to perform convertions between the
    CH1903 and WGS84 system.
    '''
    def clipDegree(self, d, clip):
        """
        Round Lat, Lon coordinates given in degrees (WGS84) to about
        a meter and avoid giving a false sense of precision
        """
        if clip:
            return round(d, 5)
        else:
            return d

    def clipMeter(self, m, clip):
        """
        Round E, N, H coordinates given in meters (LV95, LV03) to the next
        meter and avoid giving a false sense of precision
        """
        if clip:
            return round(m)
        else:
            return m

    def CHtoWGSheight(self, y, x, h, clip=False):
        """Convert CH y/x/h to WGS height"""
        # Auxiliary values (% Bern)
        y_aux = (y-600000) / 1000000
        x_aux = (x-200000) / 1000000
        h = h + 49.55 - 12.60*y_aux - 22.64*x_aux
        return self.clipMeter(h, clip)

    def CHtoWGSlat(self, y, x, clip=False):
        """Convert CH y/x to WGS lat"""
        # Auxiliary values (% Bern)
        y_aux = (y-600000) / 1000000
        x_aux = (x-200000) / 1000000
        lat = (16.9023892
               + 3.238272 * x_aux
               - 0.270978 * y_aux**2
               - 0.002528 * x_aux**2
               - 0.0447   * y_aux**2 * x_aux
               - 0.0140   * x_aux**3)
        # Unit 10000" to 1" and convert seconds to degrees (dec)
        lat = lat * 10000 / 3600
        return self.clipDegree(lat, clip)

    def CHtoWGSlng(self, y, x, clip=False):
        """Convert CH y/x to WGS long"""
        # Auxiliary values (% Bern)
        y_aux = (y-600000) / 1000000
        x_aux = (x-200000) / 1000000
        lng = (2.6779094
               + 4.728982 * y_aux
               + 0.791484 * y_aux * x_aux
               + 0.1306   * y_aux * x_aux**2
               - 0.0436   * y_aux**3)
        # Unit 10000" to 1" and convert seconds to degrees (dec)
        lng = lng * 10000 / 3600
        return self.clipDegree(lng, clip)

    def WGStoCHh(self, lat, lng, h, clip=False):
        """Convert WGS lat/long (° dec) and height to CH h"""
        # Decimal degrees to seconds
        lat = lat * 3600
        lng = lng * 3600
        # Auxiliary values (% Bern)
        lat_aux = (lat-169028.66) / 10000
        lng_aux = (lng-26782.5) / 10000
        h = h - 49.55 + 2.73*lng_aux + 6.94*lat_aux
        return self.clipMeter(h, clip)

    def WGStoCHx(self, lat, lng, clip=False):
        """Convert WGS lat/long (° dec) to CH x"""
        # Decimal degrees to seconds
        lat = lat * 3600
        lng = lng * 3600
        # Auxiliary values (% Bern)
        lat_aux = (lat-169028.66) / 10000
        lng_aux = (lng-26782.5) / 10000
        x = (200147.07
             + 308807.95 * lat_aux
             +   3745.25 * lng_aux**2
             +     76.63 * lat_aux**2
             -    194.56 * lng_aux**2 * lat_aux
             +    119.79 * lat_aux**3)
        return self.clipMeter(x, clip)

    def WGStoCHy(self, lat, lng, clip=False):
        """Convert WGS lat/long (° dec) to CH y"""
        # Decimal degrees to seconds
        lat = lat * 3600
        lng = lng * 3600
        # Auxiliary values (% Bern)
        lat_aux = (lat-169028.66) / 10000
        lng_aux = (lng-26782.5) / 10000
        y = (600072.37
             + 211455.93 * lng_aux
             -  10938.51 * lng_aux * lat_aux
             -      0.36 * lng_aux * lat_aux**2
             -     44.54 * lng_aux**3)
        return self.clipMeter(y, clip)

    def LV03toWGS84(self, east, north, height, clip=False):
        '''
        Convert LV03 to WGS84. Return a tuple of floating point numbers
        containing lat, long, and height
        '''
        return (self.CHtoWGSlat(east, north, clip),
                self.CHtoWGSlng(east, north, clip),
                self.CHtoWGSheight(east, north, height, clip))

    def WGS84toLV03(self, latitude, longitude, ellHeight, clip=False):
        '''
        Convert WGS84 to LV03. Return a tuple of floating point numbers
        containing east, north, and height
        '''
        return (self.WGStoCHy(latitude, longitude, clip),
                self.WGStoCHx(latitude, longitude, clip),
                self.WGStoCHh(latitude, longitude, ellHeight, clip))


if __name__ == "__main__":
    '''Example usage for the GPSConverter class.'''
    import sys

    converter = GPSConverter()

    if len(sys.argv) != 4:
        # Fixed coordinate example
        wgs84 = [46.95108, 7.438637, 0]

        # Convert WGS84 to LV03 coordinates
        lv03 = converter.WGS84toLV03(*wgs84, clip=True)

        print("WGS84: ")
        print(wgs84)
        print("LV03: ")
        print(lv03)
    else:
        # Convert a coordinate given on the command line
        # in one of the following formats to WGS84 or LV03:
        coords = tuple(map(float, sys.argv[1:]))
        if coords[0] < 90:
            # - WGS84: lat lon h
            print(converter.WGS84toLV03(*coords, clip=True))
        elif coords[0] < 1000000:
            # - LV03: e n h
            print(converter.LV03toWGS84(*coords, clip=True))
        else:
            # - LV95: e n h
            # LV95->LV03 conversion adds up to 1.6 m of additional error
            print(converter.LV03toWGS84(coords[0] - 2000000,
                                        coords[1] - 1000000,
                                        coords[2], clip=True))
