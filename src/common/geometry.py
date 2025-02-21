"""
This module provides various functions for manipulating objects and data frames with geometry.
Supported features include e.g. reprojection, finding nearest point on a line and transforming
geometries.

"""

from typing import List, Dict
from conf import gp_conf
import pyproj
from pyproj import CRS
from shapely.geometry import Point, LineString
from shapely.ops import split, snap, transform


def get_coords_from_lat_lon(latLon: Dict[str, float]) -> List[float]:
    return [latLon['lon'], latLon['lat']]


def get_point_from_lat_lon(latLon: Dict[str, float]) -> Point:
    return Point(get_coords_from_lat_lon(latLon))


def round_coordinates(coords_list: List[tuple], digits=6) -> List[tuple]:
    return [(round(coords[0], digits), round(coords[1], digits)) for coords in coords_list]


__projections = {
    (4326, gp_conf.proj_crs_epsg): pyproj.Transformer.from_crs(
        crs_from=CRS('epsg:4326'),
        crs_to=CRS(f'epsg:{gp_conf.proj_crs_epsg}'),
        always_xy=True),
    (gp_conf.proj_crs_epsg, 4326): pyproj.Transformer.from_crs(
        crs_from=CRS(f'epsg:{gp_conf.proj_crs_epsg}'),
        crs_to=CRS('epsg:4326'),
        always_xy=True)
}


def project_geom(geom, geom_epsg: int = 4326, to_epsg: int = gp_conf.proj_crs_epsg):
    """Projects Shapely geometry object (e.g. Point or LineString) to another CRS.
    The default conversion is from EPSG 4326 to 3879.
    """
    project = __projections[(geom_epsg, to_epsg)]
    return transform(project.transform, geom)


def split_line_at_point(
    line: LineString,
    split_point: Point,
    tolerance: float = 0.01
) -> List[LineString]:
    """Splits a line at nearest intersecting point.
    Returns:
        A list containing two LineString objects.
    """
    # try with many snapping distances as sometimes this fails to split line into two parts
    for snap_dist in (tolerance, 0.001, 0.0001, 0.00001, 0.000001, 0.0000001, 0.00000001):
        snap_line = snap(line, split_point, snap_dist)
        split_lines = split(snap_line, split_point)
        if len(split_lines) > 1:
            break
    if len(split_lines) == 1:
        raise ValueError(
            'Split lines to only one line instead of 2 - split point was probably not on the line'
        )

    return split_lines[0], split_lines[1]
