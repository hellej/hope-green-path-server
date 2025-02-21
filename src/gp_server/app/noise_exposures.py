"""
This module provides various functions for assessing and calculating expsoures to traffic noise.
The functions are useful in calculating noise costs for quiet path route optimization and in
comparing exposures to noise between paths.

"""

from typing import List, Dict, Union
from collections import defaultdict


def calc_db_cost_v2(db) -> float:
    """Returns a noise cost for given dB based on a linear scale (dB >= 45 & dB <= 75).
    """
    if db <= 44:
        return 0.0
    db_cost = (db-40) / (75-40)
    return round(db_cost, 3)


def calc_db_cost_v3(db) -> float:
    """Returns a noise cost for given dB: every 10 dB increase doubles the cost (dB >= 45 & dB <= 75).
    """
    if db <= 44:
        return 0.0
    db_cost = pow(10, (0.3 * db)/10)
    return round(db_cost / 100, 3)


def get_db_costs(version: int = 3) -> Dict[int, float]:
    """Returns a set of dB-specific noise cost coefficients. They can be used in calculating the
    base (noise) cost for edges. Alternative noise costs can be calculated by multiplying the base
    noise cost with different noise sensitivities.

    Returns:
        A dictionary of noise cost coefficients where the keys refer to the lower boundaries of the
        5 dB ranges  (e.g. key 50 refers to 50-55 dB range) and the values are the dB-specific noise
        cost coefficients.
    """
    dbs = list(range(40, 80))
    if version == 2:
        return {db: calc_db_cost_v2(db) for db in dbs}
    elif version == 3:
        return {db: calc_db_cost_v3(db) for db in dbs}
    else:
        raise ValueError('Argument version must be either 2 or 3')


def get_noise_cost_coeff(noises: Dict[int, float], db_costs: Dict[int, float]) -> float:
    """Returns noise cost coefficient."""
    if not noises:
        return 0.0
    db_distance_cost = sum([db_costs[db] * length for db, length in noises.items()])
    total_length = sum(noises.values())
    return round(db_distance_cost / total_length, 3) if total_length else 0.0


def get_noise_range(db: float) -> int:
    """Returns the lower limit of one of the six pre-defined dB ranges based on dB.
    """
    if db >= 70.0:
        return 70
    elif db >= 65.0:
        return 65
    elif db >= 60.0:
        return 60
    elif db >= 55.0:
        return 55
    elif db >= 50.0:
        return 50
    else:
        return 40


def get_noise_range_exps(noises: dict, total_length: float) -> Dict[int, float]:
    """Calculates aggregated exposures to different noise level ranges.

    Note:
        Noise levels exceeding 70 dB and noise levels lower than 50 dB will be
        aggregated (separately).

    Returns:
        A dictionary containing exposures (m) to different noise level ranges.
        (e.g. { 40: 15.2, 50: 62.4, 55: 10.5 })
    """
    # aggregate noise exposures to pre-defined dB-ranges
    db_range_lens = defaultdict(float)
    for db, exp in noises.items():
        db_range_lens[get_noise_range(db)] += exp

    # round exposures
    return {
        k: round(v, 3)
        for k, v
        in db_range_lens.items()
    }


def get_noise_range_pcts(db_range_exps: dict, length: float) -> Dict[int, float]:
    """Calculates percentages of aggregated exposures to different noise levels of total length.

    Note:
        Noise levels exceeding 70 dB are aggregated and as well as noise levels lower than 50 dB.
    Returns:
        A dictionary containing noise level values with respective percentages.
        (e.g. { 50: 35.00, 60: 65.00 })
    """
    return {
        db_range: round(db_range_length * 100 / length, 3)
        for db_range, db_range_length
        in db_range_exps.items()
    }


def aggregate_exposures(exp_list: List[dict]) -> Dict[int, float]:
    """Aggregates noise exposures (contaminated distances) from a list of noise exposures.
    """
    exps = defaultdict(float)
    for db_exps in exp_list:
        for db, exp in db_exps.items():
            exps[db] += exp

    return {
        k: round(v, 3)
        for k, v
        in exps.items()
    }


def get_total_noises_len(noises: Dict[int, float]) -> float:
    """Returns the total length of exposures to any noise levels.
    """
    if not noises:
        return 0.0
    else:
        return round(sum(noises.values()), 3)


def get_mean_noise_level(noises: dict, length: float) -> float:
    """Returns the mean noise level based on noise exposures weighted by the contaminated distances
    to different noise levels.
    """
    # estimate mean dB of 5 dB range to be min dB + 2.5 dB
    sum_db = sum([(db + 2.5) * length for db, length in noises.items()])
    mean_db = sum_db/length
    return round(mean_db, 1)


def get_noise_exposure_index(
    noises: Dict[int, float],
    db_costs: Dict[int, float]
) -> float:
    """Returns the total noise cost (i.e. noise exposure index) based on exposures to different noise levels
    and db_costs.
    """
    if not noises:
        return 0.0
    else:
        return round(sum([db_costs[db] * length for db, length in noises.items()]), 2)


def get_noise_adjusted_edge_cost(
    sensitivity: float,
    db_costs: Dict[int, float],
    noises: Union[dict, None],
    length: float,
    bike_time_cost: Union[float, None] = None
):
    """Returns composite edge cost as 'base_cost' + 'noise_cost', i.e.
    length + noise exposure based cost.
    """
    if noises is not None and abs(length - sum(noises.values())) > 0.5:
        raise ValueError('Total length of noise exposures is not equal to length, cannot calculate noise cost')

    base_cost = bike_time_cost if bike_time_cost else length

    if noises is None:
        # set high noise costs for edges outside data coverage
        return round(base_cost + base_cost * 100 * sensitivity, 2)

    noise_cost_coeff = get_noise_cost_coeff(noises, db_costs)
   
    return round(base_cost + base_cost * noise_cost_coeff * sensitivity, 2)


def add_db_40_exp_to_noises(noises: Union[dict, None], length: float) -> Dict[int, float]:
    if noises is None or not length or 40 in noises:
        return noises

    total_db_length = get_total_noises_len(noises) if noises else 0.0
    db_40_len = round(length - total_db_length, 2)
    if db_40_len:
        return {40: db_40_len, **noises}

    return noises
