import argparse
import os.path
import re

import pandas as pd
import geopandas as gpd

INDICES = ['work', 'edu', 'econ', 'health', 'div']
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


def read_xlsx(filename, columns, skip_rows):
    df = pd.read_excel(
        filename,
        header=None,
        names=columns,
        skiprows=skip_rows,
    )
    mask = df.deso.str.match(DESO_PATTERN, na=False)
    return df[mask].set_index('deso')


def convert(args):
    print('convert')

    items = [
        {
            'filename': getattr(args, f'{index}_file'),
            'columns': getattr(args, f'{index}_cols', None),
            'skip_rows': getattr(args, f'{index}_skip_rows'),
        }
        for index in INDICES
        if getattr(args, f'{index}_file') is not None
    ]

    if (n := len(items)) != 1:
        print(f'Only one input file supported, found {n}')
        return 1

    df = read_xlsx(**items[0])
    print(df)
    mode = 'a' if args.append else 'w'
    df.to_csv(
        args.output_file,
        mode=mode,
        header=not (os.path.exists(args.output_file) and args.append),
    )
    return 0


def _read(filename, **kwargs):
    if filename.endswith('.csv'):
        return pd.read_csv(filename)
    elif filename.endwith('.xlsx'):
        return pd.read_excel(filename, **kwargs)
    raise ValueError('Filename must be .csv or .xlsx')


def build(args):
    gdf = gpd.read_file(args.deso_file, layer=args.deso_layer).set_index('deso')

    #
    # Socio prep
    #

    # work
    work = _read(
        args.work_file,
        header=None,
        names=args.work_cols,
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
    edu = _read(
        args.edu_file,
        header=None,
        names=args.edu_cols,
        skiprows=args.edu_skip_rows,
    )
    mask = edu.deso.str.match(DESO_PATTERN, na=False)
    edu = edu[mask].set_index('deso')
    print(edu, edu.dtypes)

    edu_frac = (edu[['gy', 'ho', 'uni']]).sum(axis=1) / edu.sum(axis=1)
    edu_frac.name = 'edu_frac'
    # s_edu = points(edu_frac)

    # econ
    econ = _read(
        args.econ_file,
        header=None,
        names=args.econ_cols,
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
    health = _read(
        args.health_file,
        header=None,
        names=args.health_cols,
        skiprows=args.health_skip_rows,
    )
    mask = health.deso.str.match(DESO_PATTERN, na=False)
    health = health[mask].set_index('deso')
    print(health, health.dtypes)

    health_val = health['oh']
    health_val.name = 'health_val'

    # diversity
    print('diversity')
    div = _read(
        args.div_file,
        header=None,
        names=args.div_cols,
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
    df = gdf.join(
        [work_frac, edu_frac, econ_frac, health_val, div_frac],
        how='left',
    )
    print(df)

    def finalize(df):
        df['s_work'] = points(df['work_frac'])
        df['s_edu'] = points(df['edu_frac'])
        df['s_econ'] = points(df['econ_frac'])

        s_cols = ['s_work', 's_edu', 's_econ']

        df['s'] = df[s_cols].sum(axis=1) / df[s_cols].sum(axis=1).mean()
        df['h'] = df['health_val'] / df['health_val'].mean()
        df['d'] = df['div_frac'] / df['div_frac'].mean()
        df['a'] = df[['s', 'h', 'd']].mean(axis=1)

        print(df)

        return df

    output_file = f'{args.output_prefix}.gpkg'
    if args.intersect_file:
        igdf = gpd.read_file(args.intersect_file)
        for feat in igdf.itertuples():
            name = getattr(feat, args.intersect_id)
            print(feat)
            buffer = (
                feat.geometry.buffer(args.intersect_buffer_m)
                if args.intersect_buffer_m > 0
                else feat.geometry
            )
            mask = df.geometry.intersects(buffer)
            _df = finalize(df[mask].copy())
            _df.to_file(output_file, layer=f'{name}_indices', driver='GPKG')
            gpd.GeoDataFrame(
                [{'name': name}], geometry=[feat.geometry], crs=igdf.crs
            ).to_file(output_file, layer=f'{name}_intersect', driver='GPKG')
            gpd.GeoDataFrame(
                [{'name': name, 'buffer_m': args.intersect_buffer_m}],
                geometry=[buffer],
                crs=igdf.crs,
            ).to_file(output_file, layer=f'{name}_intersect_buffer', driver='GPKG')

    else:
        df = finalize(df)
        df.to_file(output_file, layer='indices', driver='GPKG')

    return 0


def add_parser_inputs(parser, exclusive=False, from_scb_excel=False):
    work_skip_rows = 0
    edu_skip_rows = 0
    econ_skip_rows = 0
    health_skip_rows = 0
    div_skip_rows = 0
    if from_scb_excel:
        work_skip_rows = 5
        edu_skip_rows = 4
        econ_skip_rows = 5
        health_skip_rows = 8
        div_skip_rows = 5

    def list_type(s):
        return s.lower().split(',')

    required = False if exclusive else True
    fparser = (
        parser.add_mutually_exclusive_group(required=True) if exclusive else parser
    )

    fparser.add_argument('--work-file', required=required)
    parser.add_argument(
        '--work-cols', default='deso,working,nonworking,total', type=list_type
    )
    parser.add_argument('--work-skip-rows', default=work_skip_rows, type=int)

    fparser.add_argument('--edu-file', required=required)
    parser.add_argument('--edu-cols', default='deso,gr,gy,ho,uni,na', type=list_type)
    parser.add_argument('--edu-skip-rows', default=edu_skip_rows, type=int)

    fparser.add_argument('--econ-file', required=required)
    parser.add_argument('--econ-cols', default='deso,frac100,n,frac', type=list_type)
    parser.add_argument('--econ-skip-rows', default=econ_skip_rows, type=int)

    fparser.add_argument('--health-file', required=required)
    parser.add_argument('--health-cols', default='deso,days,n,oh', type=list_type)
    parser.add_argument('--health-skip-rows', default=health_skip_rows, type=int)

    fparser.add_argument('--div-file', required=required)
    parser.add_argument('--div-cols', default='deso,sv,foreign,total', type=list_type)
    parser.add_argument('--div-skip-rows', default=div_skip_rows, type=int)


def main():
    """
    work <=> F??rv??rvsarbete <=> work
    edu <=> Utbildningsniv??
    econ <=> L??gekonomisk
    div <=> Utl??ndskbakgrund
    health <=> DeSOstatistik_Riket
    """
    parser = argparse.ArgumentParser(
        os.path.basename(__file__),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    subparsers = parser.add_subparsers(required=True, dest='command')

    convert_parser = subparsers.add_parser('convert')
    convert_parser.set_defaults(func=convert)
    convert_parser.add_argument('--output-file', required=True)
    convert_parser.add_argument('--append', action='store_true')
    add_parser_inputs(convert_parser, exclusive=True, from_scb_excel=True)

    build_parser = subparsers.add_parser('build')
    build_parser.set_defaults(func=build)
    build_parser.add_argument('--deso-file')
    build_parser.add_argument('--deso-layer', default=None)
    build_parser.add_argument('--deso-id', default='deso')
    build_parser.add_argument('--deso-pop', default='befolkning_191231')
    build_parser.add_argument('--intersect-file')
    build_parser.add_argument('--intersect-layer')
    build_parser.add_argument('--intersect-buffer-m', default=0, type=int)
    build_parser.add_argument('--intersect-id', default='Region_TRV')
    build_parser.add_argument('-o', '--output-prefix', required=True, type=str)
    add_parser_inputs(build_parser)

    args = parser.parse_args()
    print(args)

    return args.func(args)


if __name__ == '__main__':
    exit(main())
