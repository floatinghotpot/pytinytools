#!/usr/bin/env python3

import os, sys, requests, time
import datetime as dt
import pandas as pd
import matplotlib.pyplot as plt

__version__ = '1.0.0'

HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
SHANGHAI_GOV_URL = 'https://wsjkw.sh.gov.cn/xwfb/index{1}.html'
PARSE_PAGES = 50
KEYS = ['新增本土新冠肺炎确诊病例','新增本土无症状感染者','新增境外输入性新冠肺炎确诊病例','新增境外输入性无症状感染者','治愈出院','解除医学观察无症状感染者','新增境外输入']
CSV_FILE = 'data/shanghai_covid19_data.csv'
PLOT_SINCE_DATE = '2022-02-01'

def parse_html_to_csv():
    table = []
    for i in range(PARSE_PAGES):
        page_id = ('_' + str(i+1)) if (i>0) else ''
        url = SHANGHAI_GOV_URL.replace('{1}', page_id)
        print(url)
        r = requests.get(url, headers=HEADERS)
        r.encoding = 'utf-8'
        lines = r.text.split('\n')
        for line in lines:
            if ' target="_blank">上海20' in line:
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

    df = pd.DataFrame(table, columns=['日期']+KEYS)
    df = df.sort_values(by='日期', ascending=True).reset_index(drop=True)

    print(df)
    df.to_csv(CSV_FILE, index=False)

def plot_csv( after_date ):
    df = pd.read_csv(CSV_FILE)
    #df['新增境外输入'] = df['新增境外输入性新冠肺炎确诊病例'] + df['新增境外输入性无症状感染者'] + df['新增境外输入']
    #df['新增本土'] = df['新增本土新冠肺炎确诊病例'] + df['新增本土无症状感染者']
    print(df)

    df_plot = df[ df['日期'] > after_date ]
    df_plot.index = df_plot['日期']
    df_plot = df_plot[ ['新增境外输入性新冠肺炎确诊病例','新增境外输入性无症状感染者','新增本土新冠肺炎确诊病例','新增本土无症状感染者'] ]

    df_plot.plot(
        title='上海新冠疫情趋势\n(数据来源: 上海市卫健委官网)',
        xlabel='日期',
        ylabel='人数',
        figsize= (9,6),
    )

    # support Chinese font
    plt.rcParams['font.sans-serif'] = ['SimHei'] # Chinese font
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams["axes.unicode_minus"] = False

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
    __argv0__ [-v] [-update] [-since=20220201] [-days=90]
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
    for k in options:
        if k in ['-v', '--version']:
            print(__version__, '\n')
            return

        if k.startswith('-since='):
            since_str = k.replace('-since=','')
            plot_since_date = dt.datetime.strptime(since_str, '%Y%m%d').strftime('%Y-%m-%d')

        elif k.startswith('-days='):
            days_str = k.replace('-days=','')
            plot_since_date = (datetime_today() - dt.timedelta(days=int(days_str))).strftime('%Y-%m-%d')

    if ('-update' in options) or (not os.path.exists(CSV_FILE)) or out_of_date(CSV_FILE):
        parse_html_to_csv()

    plot_csv(plot_since_date)

cli_main()
