import argparse
import os.path
import re

import pandas as pd
import geopandas as gpd

from devtools import debug

DESO_PATTERN = r'^[0-9]{4}[A-C][0-9]{4}$'


def main():
    pass


def make_geom(deso_path, deso_layer, deso_id, index_path):
    gdf = gpd.read_file(args.deso_file, layer=args.deso_layer).set_index('deso')

    print(gdf, gdf.dtypes)

    df = pd.read_excel(args.index_file).set_index('deso')

    print(df, df.dtypes)

    res = gdf.join(df, how='inner')

    print(res)

    res.to_file('sormland_deso_index.fgb', driver='FlatGeobuf')


def points(foo):
    """
    Calculate points for a series
    """
    low = foo.quantile(0.2)
    high = foo.quantile(0.8)

    print(low, high)

    p = pd.Series(2, index=foo.index, dtype=int)

    p[foo <= low] = 3
    p[foo >= high] = 1
    print(p, p.dtypes)

    return p


if __name__ == '__main__':
    parser = argparse.ArgumentParser(os.path.basename(__file__))
    parser.add_argument('--deso-file')
    parser.add_argument('--deso-layer', default='deso_2018_v2')
    parser.add_argument('--deso-id', default='deso')
    parser.add_argument('--deso-pop', default='befolkning_191231')

    parser.add_argument('--work-file')
    parser.add_argument('--work-cols', default='deso,working,nonworking,total')
    parser.add_argument('--work-skip-rows', default=5)

    parser.add_argument('--edu-file')
    parser.add_argument('--edu-cols', default='deso,gr,gy,ho,uni,na')
    parser.add_argument('--edu-skip-rows', default=4)

    parser.add_argument('--econ-file')
    parser.add_argument('--econ-cols', default='deso,frac100,n,frac')
    parser.add_argument('--econ-skip-rows', default=5)

    parser.add_argument('--health-file')
    parser.add_argument('--health-cols', default='deso,days,n,oh')
    parser.add_argument('--health-skip-rows', default=8)

    parser.add_argument('--div-file')
    parser.add_argument('--div-cols', default='deso,sv,foreign,total')
    parser.add_argument('--div-skip-rows', default=5)

    parser.add_argument('--index-file')

    args = parser.parse_args()

    print(args)

    gdf = gpd.read_file(args.deso_file, layer=args.deso_layer).set_index('deso')

    #
    # Socio prep
    #

    # work
    work = pd.read_excel(
        args.work_file,
        header=None,
        names=args.work_cols.split(','),
        skiprows=args.work_skip_rows,
    )
    mask = work.deso.str.match(DESO_PATTERN, na=False)
    work = work[mask].set_index('deso')
    print(work, work.dtypes)

    work_frac = work['working'] / work['total']
    work_frac.name = 'work_frac'
    # s_work = points(work_frac)

    # tmp idx
    df = pd.DataFrame(index=work.index)

    # edu
    edu = pd.read_excel(
        args.edu_file,
        header=None,
        names=args.edu_cols.split(','),
        skiprows=args.edu_skip_rows,
    )
    mask = edu.deso.str.match(DESO_PATTERN, na=False)
    edu = edu[mask].set_index('deso')
    print(edu, edu.dtypes)

    edu_frac = (edu[['gy', 'ho', 'uni']]).sum(axis=1) / edu.sum(axis=1)
    edu_frac.name = 'edu_frac'
    # s_edu = points(edu_frac)

    # econ
    econ = pd.read_excel(
        args.econ_file,
        header=None,
        names=args.econ_cols.split(','),
        skiprows=args.econ_skip_rows,
    )
    mask = econ.deso.str.match(DESO_PATTERN, na=False)
    econ = econ[mask].set_index('deso')
    print(econ, econ.dtypes)

    econ_frac = 1 - econ['frac']
    econ_frac.name = 'econ_frac'
    # s_econ = points(econ_frac)

    #
    # Other
    #

    # health
    health = pd.read_excel(
        args.health_file,
        header=None,
        names=args.health_cols.split(','),
        skiprows=args.health_skip_rows,
    )
    mask = health.deso.str.match(DESO_PATTERN, na=False)
    health = health[mask].set_index('deso')
    print(health, health.dtypes)

    health_val = health['oh']
    health_val.name = 'health_val'

    # diversity
    print('diversity')
    div = pd.read_excel(
        args.div_file,
        header=None,
        names=args.div_cols.split(','),
        skiprows=args.div_skip_rows,
    )
    print(len(div))
    mask = div.deso.str.match(DESO_PATTERN, na=False)
    div = div[mask].set_index('deso')
    print(div, div.dtypes)

    div_frac = div['foreign'] / div['total']
    div_frac.name = 'div_frac'

    #
    # Agg
    #
    df = pd.concat(
        [gdf, work_frac, edu_frac, econ_frac, health_val, div_frac],
        join='inner',
        axis=1,
    )
    print(df)

    df['s_work'] = points(df['work_frac'])
    df['s_edu'] = points(df['edu_frac'])
    df['s_econ'] = points(df['econ_frac'])

    s_cols = ['s_work', 's_edu', 's_econ']

    df['s'] = df[s_cols].sum(axis=1) / df[s_cols].sum(axis=1).mean()
    df['h'] = df['health_val'] / df['health_val'].mean()
    df['d'] = df['div_frac'] / df['div_frac'].mean()
    df['a'] = df[['s', 'h', 'd']].mean(axis=1)

    print(df)

    df.to_file('deso_index.fgb', driver='FlatGeobuf')
