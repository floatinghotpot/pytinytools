#!/usr/bin/env python3

import os, sys, requests, time, re
import datetime as dt
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from scipy.optimize import curve_fit

__version__ = '1.0.0'

HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
SHANGHAI_GOV_URL = 'https://wsjkw.sh.gov.cn/xwfb/index{1}.html'
PARSE_PAGES = 50
KEYS = ['新增本土新冠肺炎确诊病例','新增本土无症状感染者','新增境外输入性新冠肺炎确诊病例','新增境外输入性无症状感染者','治愈出院','解除医学观察无症状感染者','新增境外输入']
YESTERDAY_PATTERN = '昨日新增本土新冠肺炎确诊病例96例、无症状感染者4381例，新增境外输入性确诊病例11例、无症状感染者1例'
CSV_FILE = 'shanghai_covid19_data.csv'
PLOT_SINCE_DATE = '2022-03-01'
FIT_END_DATE = '2022-03-30'
PREDICT_DAYS = 5

def parse_html_to_csv(since_date):
    since_date = (dt.datetime.strptime(since_date, '%Y-%m-%d')).date()

    table = []
    for i in range(PARSE_PAGES):
        page_id = ('_' + str(i+1)) if (i>0) else ''
        url = SHANGHAI_GOV_URL.replace('{1}', page_id)
        print(url)
        r = requests.get(url, headers=HEADERS)
        r.encoding = 'utf-8'
        lines = r.text.split('\n')
        for line in lines:
            if ' target="_blank">昨日新增本土新冠肺炎确诊病例' in line:
                line = line.split(' target="_blank">昨日新增本土新冠肺炎确诊病例')[1]
                items = line.split('</a><span class="time">')
                line = items[0]
                date_str = items[1].split('</span></li>')[0]
                date = (dt.datetime.strptime(date_str, '%Y-%m-%d') - dt.timedelta(1)).date()
                print(date, line)

                result = re.findall(r'\d+', line)
                row = [date, result[0], result[1], result[2], result[3], 0, 0, 0]
                table.append(row)

            elif ' target="_blank">上海20' in line:
                line = line.split(' target="_blank">上海')[1].split('</a><span')[0]
                line = line.replace('，',' ').replace(',',' ').replace('日','日 ').replace('  ',' ').strip()
                print(line)

                items = line.split(' ')
                if '年' not in items[0]:
                    continue

                date_str = items[0].replace('年','-').replace('月','-').replace('日','')
                date = dt.datetime.strptime(date_str, '%Y-%m-%d').date()

                row = [date]
                for k in KEYS:
                    n = 0
                    for item in items:
                        if '-' in item:
                            pass
                        elif item.startswith('无'):
                            pass
                        elif k in item:
                            n_str = item.split(k)[1].split('例')[0]
                            if n_str.isdigit():
                                n = int(n_str)
                    row.append(n)
                table.append(row)

        if (date is not None) and (date < since_date):
            break

    df = pd.DataFrame(table, columns=['日期']+KEYS)
    df = df.sort_values(by='日期', ascending=True).reset_index(drop=True)

    print(df)
    df.to_csv(CSV_FILE, index=False)

def func(x, a, b, c):
    return a * np.exp(b * x) + c

def plot_csv( since_date, fit = False ):
    df = pd.read_csv(CSV_FILE)
    df['新增境外输入'] = df['新增境外输入性新冠肺炎确诊病例'] + df['新增境外输入性无症状感染者'] + df['新增境外输入']
    df['新增本土'] = df['新增本土新冠肺炎确诊病例'] + df['新增本土无症状感染者']
    #print(df)

    df_plot = df[ df['日期'] > since_date ].copy()
    df_plot_columns = ['新增本土新冠肺炎确诊病例','新增本土无症状感染者','新增境外输入性新冠肺炎确诊病例','新增境外输入性无症状感染者']
    array_table = df_plot[['日期'] + df_plot_columns].tail(20).values

    if fit:
        df_fit = df_plot[ df_plot['日期'] < FIT_END_DATE ]
        xdata = df_fit.index - df_fit.index[0]
        ydata = df_fit['新增本土无症状感染者'] + df_fit['新增本土新冠肺炎确诊病例']
        popt, pcov = curve_fit(func, xdata, ydata)
        fit_label = ('\n拟合曲线:\ny = a * exp(b * x) + c\na=%5.3f, b=%5.3f, c=%5.3f\n' % tuple(popt))

        fit_label += '\n预估新增 (确诊+无症状):'
        fit_end_date = dt.datetime.strptime(FIT_END_DATE, '%Y-%m-%d')
        for i in range(PREDICT_DAYS):
            fit_label += '\n' + (fit_end_date + dt.timedelta(i)).strftime('%Y-%m-%d') + ': '+str(int(func((xdata[-1]+1+i), *popt)))
        fit_label += '\n\n阻断传播，将早日迎来拐点'

        xdata = df_plot.index - df_plot.index[0]
        df_plot[ fit_label ] = func(xdata, *popt)
        df_plot_columns.append(fit_label)

    df_plot.index = df_plot['日期']
    df_plot = df_plot[ df_plot_columns ]

    # create figure 2x1
    fig, (ax0, ax1) = plt.subplots(1, 2, gridspec_kw={'width_ratios': [1, 1]})

    n = len(array_table)
    ax0.axis('tight')
    ax0.axis('off')
    ax0.table(
        cellText=array_table,
        colLabels=['日期','本土确诊','本土无症状','输入确诊','输入无症状'],
        loc='center',
        )
    ax0.set_title('上海 2022 新冠疫情\n(数据来源: 上海市卫健委官网)')

    df_plot.plot(
        ax=ax1,
        title='趋势图',
        #xlabel='日期',
        #ylabel='人数',
        figsize= (12,6),
    )

    # support Chinese font
    plt.rcParams['font.sans-serif'] = ['SimHei'] # Chinese font
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams["axes.unicode_minus"] = False
    plt.xticks(rotation = 15)
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

def datetime_today():
    now = dt.datetime.now()
    return dt.datetime(now.year, now.month, now.day)

def cli_help():
    syntax_tips = '''Syntax:
    __argv0__ [-v] [-update] [-since=20220201] [-days=90] [-fit]
'''.replace('__argv0__',os.path.basename(sys.argv[0]))
    print(syntax_tips)

def out_of_date(path):
    modified = os.path.getmtime(path)
    year,month,day,hour,minute,second = time.localtime(modified)[:-3]
    modified_date = dt.datetime(year, month, day)
    return modified_date < datetime_today()

def cli_main():
    params, options = parse_params_options(sys.argv)

    plot_since_date = PLOT_SINCE_DATE
    fit = False
    for k in options:
        if k in ['-v', '--version']:
            print(__version__, '\n')
            return

        if k in ['-fit']:
            fit = True

        if k.startswith('-since='):
            since_str = k.replace('-since=','')
            plot_since_date = dt.datetime.strptime(since_str, '%Y%m%d').strftime('%Y-%m-%d')

        elif k.startswith('-days='):
            days_str = k.replace('-days=','')
            plot_since_date = (datetime_today() - dt.timedelta(days=int(days_str))).strftime('%Y-%m-%d')

    if ('-update' in options) or (not os.path.exists(CSV_FILE)) or out_of_date(CSV_FILE):
        parse_html_to_csv(plot_since_date)

    plot_csv(plot_since_date, fit)

cli_main()
