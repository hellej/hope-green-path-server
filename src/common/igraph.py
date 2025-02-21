"""igraph I/O utilities for green paths route planner.

This module provides functions for both loading and exporting street network graph
files for Green Paths route planner. External graph files use GraphML text format.

An important export of the module are Enum classes that include names of edge and node attributes.
The values of the enums are used as attribute names in the graph objects as well as in the exported
GraphML files. The attribute names in the exported files are compact to reduce file size.
On the other hand, the (descriptive) names of the enums are used as column names when edge or node
data is read to pandas DataFrame object.

"""

from typing import Any, List, Dict
from conf import gp_conf
import ast
from enum import Enum
import geopandas as gpd
import igraph as ig
from pyproj import CRS
from shapely import wkt
from shapely.geometry import LineString, Point
import logging


log = logging.getLogger('common.igraph')


# enum names are used as dataframe column names
# values are used as attribute names in igraph graph objects and exported GraphML files


class NoiseSource(Enum):
    road = 'road'
    train = 'train'
    metro = 'metro'
    tram = 'tram'


class Node(Enum):
    id_ig = 'ii'
    id_otp = 'io'
    name_otp = 'no'
    geometry = 'geom'
    geom_wgs = 'geom_wgs'
    traversable_walking = 'b_tw'
    traversable_biking = 'b_tb'
    traffic_light = 'tl'


class Edge(Enum):
    id_ig: int = 'ii'
    id_otp: str = 'io'
    id_way: int = 'iw'  # for similar geometries (e.g. two-way connections between node pairs)
    uv: tuple = 'uv'  # source & target node ids as a tuple
    name_otp: str = 'no'
    geometry: LineString = 'geom'
    geom_wgs: LineString = 'geom_wgs'
    length: float = 'l'
    bike_time_cost: float = 'c_bt'
    bike_safety_cost: float = 'c_bs'
    edge_class: str = 'ec'
    street_class: str = 'sc'
    is_stairs: bool = 'b_st'
    is_no_thru_traffic: bool = 'b_ntt'
    allows_walking: bool = 'b_aw'
    allows_biking: bool = 'b_ab'
    traversable_walking: bool = 'b_tw'
    traversable_biking: bool = 'b_tb'
    bike_safety_factor: float = 'bsf'
    noises: Dict[int, float] = 'n'  # nodata = None, no noises = {}
    noise_source: NoiseSource = 'ns'  # nodata = None, no noises = ''
    noise_sources: Dict[NoiseSource, int] = 'nss'  # nodata = None, no noises = {}
    aqi: float = 'aqi'  # air quality index
    gvi_gsv: float = 'g_gsv'  # mean green view index (GVI) from Google Street View (GSV) images
    gvi_low_veg_share: float = 'g_lv'  # share of low (<2m) vegetation in 30m buffer around edge
    gvi_high_veg_share: float = 'g_hv'  # share of high (>2m) vegetation in 30m buffer around edge
    gvi_comb_gsv_veg: float = 'g_gsv_v'  # combined GVI of GSV GVI and both vegetation shares
    gvi_comb_gsv_high_veg: float = 'g_gsv_hv'  # combined GVI of GSV GVI and high vegetation share
    gvi: float = 'g'  # combined GVI to use in routing (one of the above two)


def as_string(value: Any):
    if isinstance(value, bool):
        return '1' if value else '0'
    return str(value)

def to_str(value):
    return str(value) if value != 'None' else None

def to_int(value):
    return int(value) if value != 'None' else None

def to_float(value):
    return float(value) if value != 'None' else None

def to_geom(value):
    return wkt.loads(value)

def to_bool(value):
    if len(value) == 1: return value == '1'
    return ast.literal_eval(value)

def to_dict(value):
    return ast.literal_eval(value) if value != 'None' else None

def to_tuple(value):
    return ast.literal_eval(value) if value != 'None' else None


__value_converter_by_edge_attribute = {
    Edge.id_ig: to_int,
    Edge.id_otp: to_str,
    Edge.id_way: to_int,
    Edge.uv: to_tuple,
    Edge.name_otp: to_str,
    Edge.geometry: to_geom,
    Edge.geom_wgs: to_geom,
    Edge.length: to_float,
    Edge.bike_time_cost: to_float,
    Edge.bike_safety_cost: to_float,
    Edge.edge_class: to_str,
    Edge.street_class: to_str,
    Edge.is_stairs: to_bool,
    Edge.is_no_thru_traffic: to_bool,
    Edge.allows_walking: to_bool,
    Edge.allows_biking: to_bool,
    Edge.traversable_walking: to_bool,
    Edge.traversable_biking: to_bool,
    Edge.bike_safety_factor: to_float,
    Edge.noises: to_dict,
    Edge.noise_source: to_str,
    Edge.noise_sources: to_dict,
    Edge.aqi: to_float,
    Edge.gvi_gsv: to_float,
    Edge.gvi_low_veg_share: to_float,
    Edge.gvi_high_veg_share: to_float,
    Edge.gvi_comb_gsv_veg: to_float,
    Edge.gvi_comb_gsv_high_veg: to_float,
    Edge.gvi: to_float
}

__value_converter_by_node_attribute = {
    Node.id_ig: to_int,
    Node.id_otp: to_str,
    Node.name_otp: to_str,
    Node.geometry: to_geom,
    Node.geom_wgs: to_geom,
    Node.traversable_walking: to_bool,
    Node.traversable_biking: to_bool,
    Node.traffic_light: to_bool,
}


def get_edge_dicts(G: ig.Graph, attrs: List[Enum] = [Edge.geometry]) -> list:
    """Returns all edges of a graph as a list of dictionaries. Only the selected attributes (attrs)
    are included in the dictionaries.
    """
    edge_dicts = []
    for edge in G.es:
        edge_attrs = edge.attributes()
        edge_dict = {}
        for attr in attrs:
            if attr.value in edge_attrs:
                edge_dict[attr.name] = edge_attrs[attr.value]
        edge_dicts.append(edge_dict)

    return edge_dicts


def get_edge_gdf(
    G: ig.Graph,
    id_attr: Enum = None,
    attrs: List[Enum] = [],
    ig_attrs: List[str] = [],
    geom_attr: Enum = Edge.geometry,
    epsg: int = gp_conf.proj_crs_epsg,
    drop_na_geoms: bool = False
) -> gpd.GeoDataFrame:
    """Returns all edges of a graph as GeoPandas GeoDataFrame. The default is to load the projected
    geometry, but it can be overridden by defining another geom_attr and the corresponding epsg.
    Edges without geometry can be omitted.
    """

    edge_dicts = []
    ids = []
    for edge in G.es:
        edge_dict = {}
        edge_attrs = edge.attributes()
        ids.append(edge_attrs[id_attr.value] if id_attr else edge.index)
        if isinstance(edge_attrs[geom_attr.value], LineString):
            edge_dict[geom_attr.name] = edge_attrs[geom_attr.value]
        else:
            edge_dict[geom_attr.name] = None

        for attr in attrs:
            if attr.value in edge_attrs:
                edge_dict[attr.name] = edge_attrs[attr.value]

        for attr in ig_attrs:
            if hasattr(edge, attr):
                edge_dict[attr] = getattr(edge, attr)

        edge_dicts.append(edge_dict)

    gdf = gpd.GeoDataFrame(edge_dicts, geometry=geom_attr.name, index=ids, crs=CRS.from_epsg(epsg))
    if drop_na_geoms:
        return gdf[gdf[geom_attr.name].apply(lambda geom: isinstance(geom, LineString))]
    else:
        return gdf


def get_node_gdf(
    G: ig.Graph,
    id_attr: Enum = None,
    attrs: List[Enum] = [],
    ig_attrs: List[str] = [],
    geom_attr: Enum = Node.geometry,
    epsg: int = gp_conf.proj_crs_epsg,
    drop_na_geoms: bool = False
) -> gpd.GeoDataFrame:
    """Returns all nodes of a graph as pandas GeoDataFrame. The default is to load the projected
    geometry, but it can be overridden by defining another geom_attr and a corresponding epsg.
    Nodes without geometry can be omitted.
    """

    node_dicts = []
    ids = []
    for node in G.vs:
        node_dict = {}
        node_attrs = node.attributes()
        ids.append(node_attrs[id_attr.value] if id_attr else node.index)

        if isinstance(node_attrs[geom_attr.value], Point):
            node_dict[geom_attr.name] = node_attrs[geom_attr.value]
        else:
            node_dict[geom_attr.name] = None

        for attr in attrs:
            if attr.value in node_attrs:
                node_dict[attr.name] = node_attrs[attr.value]

        for attr in ig_attrs:
            if hasattr(node, attr):
                node_dict[attr] = getattr(node, attr)

        node_dicts.append(node_dict)

    gdf = gpd.GeoDataFrame(node_dicts, geometry=geom_attr.name, index=ids, crs=CRS.from_epsg(epsg))
    if drop_na_geoms:
        return gdf[gdf[geom_attr.name].apply(lambda geom: isinstance(geom, Point))]
    else:
        return gdf


def read_graphml(graph_file: str, log=None) -> ig.Graph:
    """Loads an igraph graph object from GraphML file, including all edge and node
    attributes that are found in the data and recognized by this module.

    Since all attributes are saved in text format, an attribute specific converter must be found
    in the dictionary __value_converter_by_node_attribute for each attribute.
    Attributes for which a converter is not found are omitted.
    """

    G = ig.Graph()
    G = G.Read_GraphML(graph_file)
    del(G.vs['id'])

    for attr in G.vs[0].attributes():
        try:
            converter = __value_converter_by_node_attribute[Node(attr)]
            G.vs[attr] = [converter(value) for value in list(G.vs[attr])]
        except Exception:
            if log:
                log.warning(f'Failed to read node attribute {attr}')

    for attr in G.es[0].attributes():
        try:
            converter = __value_converter_by_edge_attribute[Edge(attr)]
            G.es[attr] = [converter(value) for value in list(G.es[attr])]
        except Exception:
            if log:
                log.warning(f'Failed to read edge attribute {attr}')

    return G


def export_to_graphml(
    G: ig.Graph,
    graph_file: str,
    n_attrs: List[Node] = [],
    e_attrs: List[Edge] = []
) -> None:
    """Writes the given graph object to a text file in GraphML format. Only the
    selected edge and node attributes are included in the export if some are specified.
    If no edge or node attributes are specified, all found attributes are exported.
    Attribute values are written as text, converted by str(value).
    """

    Gc = G.copy()  # avoid mutating the original graph

    if not n_attrs:
        for attr in Node:
            if attr.value in Gc.vs[0].attributes():
                Gc.vs[attr.value] = [as_string(value) for value in list(Gc.vs[attr.value])]
    else:
        for attr in n_attrs:
            Gc.vs[attr.value] = [as_string(value) for value in list(Gc.vs[attr.value])]
        # delete unspecified attributes
        for node_attr in G.vs.attribute_names():
            if node_attr not in [attr.value for attr in n_attrs]:
                del(Gc.vs[node_attr])

    if not e_attrs:
        for attr in Edge:
            if attr.value in Gc.es[0].attributes():
                Gc.es[attr.value] = [as_string(value) for value in list(Gc.es[attr.value])]
    else:
        for attr in e_attrs:
            Gc.es[attr.value] = [as_string(value) for value in list(Gc.es[attr.value])]
        # delete unspecified attributes
        for edge_attr in G.es.attribute_names():
            if edge_attr not in [attr.value for attr in e_attrs]:
                del(Gc.es[edge_attr])

    Gc.save(graph_file, format='graphml')
    log.info(f'Exported graph to file: {graph_file}')
