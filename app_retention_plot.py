#!/usr/bin/env python3
# -*- coding: utf-8; py-indent-offset:4 -*-

import sys, os, io
import numpy as np
import pandas as pd
import tabulate as tb
import matplotlib.pyplot as plt

__version__ = '1.0.0'

lang_res = {
    # default lang
    'lang': 'en',
    # English
    'en': {
    },
    # Chinese Simplified
    'zh': {
        'day': '天',
        'retention': '留存率',
        'new user': '新增用户',
        'retention curve fit': '留存曲线拟合',
        'DAU rate': '日活率',
        'max DAU rate': '最大日活率',
        'loading retention data from': '读入留存数据',
        'using default sample data': '使用默认示范数据',
    }
}

def set_lang(l):
    lang_res['lang'] = l

def T(t):
    lang = lang_res['lang']
    if lang in lang_res:
        res = lang_res[lang]
        if t in res:
            return res[t]
    return t

def plot_retain_data(df_retain):
    # calc slope of linear fit
    df = df_retain.copy()
    df['delta_y'] = df['retention'].diff(1)
    df['delta_x'] = df['day'].diff(1)
    df['slope'] = df['delta_y'] / df['delta_x']
    #print(df)

    # linear interpolation
    max_day = df['day'].max()
    df2 = pd.DataFrame([i for i in range(1,max_day+1)], columns=['day'])
    df = df.set_index('day').join(df2.set_index('day'), how='outer')
    df.insert(0, 'day', df.index)
    df['delta_x'] = df['day'].diff(1)
    df['slope'] = df['slope'].fillna(method= 'backfill')
    df['delta_y'] = df['delta_x'] * df['slope']
    df.at[0, 'delta_x'] = df.at[0, 'day']
    df.at[0, 'delta_y'] = df.at[0, 'retention']
    df['retention'] = df['delta_y'].cumsum()

    # calculate DAU rate
    df['dau'] = df['retention'].cumsum()
    max_dau = np.round(df['dau'].max(), 1)
    #print( tb.tabulate(df, headers='keys') )

    # create figure 2x2
    fig, ((ax0, ax1), (ax2, ax3)) = plt.subplots(2, 2, gridspec_kw={'width_ratios': [1, 3]})

    # draw table to show the retention data
    array_retain = df_retain.values.tolist()
    n = len(array_retain)
    for i in range(0, n):
        array_retain[i][0] = int(array_retain[i][0])
        array_retain[i][1] = str(array_retain[i][1]) + ' %'
    ax0.axis('tight')
    ax0.axis('off')
    ax0.table(cellText=array_retain, colLabels=[T('day'),T('retention')], loc='center')
    ax2.axis('tight')
    ax2.axis('off')

    # plot the retention curve
    df = df[['retention','dau']]
    df.columns = [T('retention'),T('DAU rate')]
    df.index.name = T('day')
    df[[T('retention')]].plot(
        ax=ax1,
        kind= 'line',
        figsize= (9,6),
        title= T('retention curve fit'),
        ylabel= T('retention') + ' (%)',
    )
    # plot the DAU curve
    df[[T('DAU rate')]].plot(
        ax=ax3,
        kind= 'line',
        figsize= (9,6),
        title= T('max DAU rate') + ' / ' + T('new user') + ' = ' + str(max_dau) + ' %',
        ylabel= T('DAU rate') + ' (%)',
    )

    # support Chinese font
    plt.rcParams['font.sans-serif'] = ['SimHei'] # Chinese font
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams["axes.unicode_minus"] = False

    fig.tight_layout()
    plt.show()

def parse_params_options(argv):
    params = []
    options = []
    for i in range(1, len(argv)):
        str = argv[i]
        if str[0] == '-':
            options.append(str)
        else:
            params.append(str)

    return params, options

def cli_help():
    syntax_tips = '''Syntax:
    __argv0__ -v
    __argv0__ -h
    __argv0__ sample1.csv [-en | -zh]
'''.replace('__argv0__',os.path.basename(sys.argv[0]))
    print(syntax_tips)

def cli_main():
    params, options = parse_params_options(sys.argv)

    for k in options:
        if k in ['-v', '--version']:
            print(__version__, '\n')
            return
        elif k in ['-h', '--help']:
            cli_help()
            return

        k = k[1:]
        if k in lang_res:
            set_lang(k)

    if len(params)>0 and params[0].endswith('.csv'):
        retain_data_csv = params[0]
        print(T('loading retention data from'), retain_data_csv, '...')
    else:
        print(T('using default sample data'), '...')
        retain_data_csv = io.StringIO('''
day,retention
0,100.0
1,42.0
7,20.0
14,14.0
30,7.5
60,3.0
90,2.0
180,0.0
''')
    df_retain = pd.read_csv(retain_data_csv)
    df_retain.columns = ['day','retention']
    print(df_retain)

    plot_retain_data(df_retain)

cli_main()
