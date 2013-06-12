#-*- coding: utf-8 -*-

###########################################################################
##                                                                       ##
## Copyrights Frederic Rodrigo 2013                                      ##
##                                                                       ##
## This program is free software: you can redistribute it and/or modify  ##
## it under the terms of the GNU General Public License as published by  ##
## the Free Software Foundation, either version 3 of the License, or     ##
## (at your option) any later version.                                   ##
##                                                                       ##
## This program is distributed in the hope that it will be useful,       ##
## but WITHOUT ANY WARRANTY; without even the implied warranty of        ##
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         ##
## GNU General Public License for more details.                          ##
##                                                                       ##
## You should have received a copy of the GNU General Public License     ##
## along with this program.  If not, see <http://www.gnu.org/licenses/>. ##
##                                                                       ##
###########################################################################

from shapely.wkt import loads
from shapely.geometry import Point
from modules import downloader
from interval_tree import IntervalTree


class ErrorFilter:
    def apply(self, classs, subclass, geom):
        return True


class PolygonErrorFilter(ErrorFilter):

    def __init__(self, polygon_id):
        polygon_url = "http://polygons.openstreetmap.fr/"
        url = polygon_url + "index.py?id="+str(polygon_id)
        s = downloader.urlread(url, 60)
        url = polygon_url + "get_wkt.py?params=0&id="+str(polygon_id)
        s = downloader.urlread(url, 60)
        if s.startswith("SRID="):
            s = s.split(";", 1)[1]
        self.polygon = loads(s)
        self.build()

    def sameVDir(self, x1, y1, x2, y2, x3, y3):
        # Check if next segment have same direction again vertical.
        if y1 < y2:
            return y2 < y3
        else:
            return y2 > y3

    class Interval:
        def __init__(self, x1, y1, x2, y2, sameDir):
            # Need for IntervalTree
            self.start = min(y1,y2)
            self.stop = max(y1,y2)
            # Segment
            self.x1 = x1
            self.x2 = x2
            self.y1 = y1
            self.y2 = y2
            self.sameDir = sameDir

    def build_polygon(self, coords):
        (x,y) = coords.xy
        n = len(x)
        ivals = []
        for i in range(n):
            ivals.append(self.Interval(x[i], y[i], x[(i+1)%n], y[(i+1)%n], self.sameVDir(x[i], y[i], x[(i+1)%n], y[(i+1)%n], x[(i+2)%n], y[(i+2)%n])))
        return ivals

    def build(self):
        ivals = []
        for p in self.polygon:
            ivals += self.build_polygon(p.exterior.coords)
            for i in p.interiors:
                ivals += self.build_polygon(i.coords)
        self.tree = IntervalTree(ivals)

    def point_inside_polygon(self, x, y):
        poly = self.tree.find(y, y)
        inside = False

        for p in poly:
            if p.y1 != p.y2:
                if p.y2 != y or p.sameDir: # This is a true cross and not a tangent
                    xinters = (y-p.y1)*(p.x2-p.x1)/(p.y2-p.y1)+p.x1
                    if x < xinters:
                        inside = not inside
            elif x <= max(p.x1, p.x2):
                inside = not inside

        return inside

    def apply(self, classs, subclass, geom):
        if "position" not in geom:
            return False
        else:
            inside = False
            for position in geom["position"]:
                lat = float(position["lat"])
                lon = float(position["lon"])
                inside |= self.point_inside_polygon(lon, lat)
            return inside
