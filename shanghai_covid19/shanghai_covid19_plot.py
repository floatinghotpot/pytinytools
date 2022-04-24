#!/usr/bin/env python3

import os, sys, requests, time, re
from py import process
import datetime as dt
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
import tabulate as tb
from html.parser import HTMLParser

from scipy.optimize import curve_fit

__version__ = '1.0.0'

HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
SHANGHAI_GOV_URL = 'https://wsjkw.sh.gov.cn/xwfb/index{1}.html'
PARSE_PAGES = 50
COLS = ['新增本土确诊','新增本土无症状','新增输入确诊','新增输入无症状','治愈出院','解除观察','在院治疗','新增死亡','转归病例','管控确诊','管控无症状']
PATTERNS = ['新增本土新冠肺炎确诊病例','新增本土无症状感染者','新增境外输入性新冠肺炎确诊病例','新增境外输入性无症状感染者','治愈出院','解除医学观察无症状感染者/解除医学观察本土无症状感染者','在院治疗','新增本土死亡病例/新增本土死亡']
YESTERDAY_PATTERN = '昨日新增本土新冠肺炎确诊病例96例、无症状感染者4381例，新增境外输入性确诊病例11例、无症状感染者1例'
CSV_FILE = 'shanghai_covid19_data.csv'
SINCE_DATE = '2022-02-26'
PLOT_SINCE_DATE = '2022-02-28'
FIT_END_DATE = '2022-03-30'
PREDICT_DAYS = 5

def _handle_data(self, data):
    self.text += data

HTMLParser.handle_data = _handle_data

def get_html_text(html: str):
    parser = HTMLParser()
    parser.text = ''
    parser.feed(html)
    return parser.text.strip()

def parse_html_to_csv(since_date, test= False):
    df_old = None
    since_date = (dt.datetime.strptime(since_date, '%Y-%m-%d')).date()

    if os.path.exists(CSV_FILE):
        df_old = pd.read_csv(CSV_FILE)
        if '/' in df_old['日期'].iloc[-1]:
            df_old['日期'] = pd.to_datetime(df_old['日期'], format='%m/%d/%Y').dt.date
        elif '-' in df_old['日期'].iloc[-1]:
            df_old['日期'] = pd.to_datetime(df_old['日期'], format='%Y-%m-%d').dt.date
        since_date = df_old['日期'].iloc[-1]

    table = []
    for i in range(PARSE_PAGES):
        page_id = ('_' + str(i+1)) if (i>0) else ''
        url = SHANGHAI_GOV_URL.replace('{1}', page_id)
        print(url)
        r = requests.get(url, headers=HEADERS)
        r.encoding = 'utf-8'
        lines = r.text.split('\n')
        for line in lines:
            line = line.strip()
            if not line.startswith('<li><a href="/xwfb/'):
                continue

            url_findings = re.findall('<a href=".*" title=', line)
            url = url_findings[0].replace('<a href="','').replace('" title=','') if len(url_findings)>0 else ''
            title_findings = re.findall('title=".*" target=', line)
            title = title_findings[0].replace('title="','').replace('" target=','') if (len(title_findings)>0) else ''
            date_findings = re.findall('class="time">.*</span></li>', line)
            date_str = date_findings[0].replace('class="time">','').replace('</span></li>','') if (len(date_findings)>0) else ''

            if title.startswith('昨日新增本土新冠肺炎确诊病例'):
                date = (dt.datetime.strptime(date_str, '%Y-%m-%d') - dt.timedelta(1)).date()
                title = title.replace('昨日','')
                pass
            elif title.startswith('上海2022年'):
                items = title.split('日，')
                if '年' not in items[0]:
                    continue
                date_str = items[0].replace('上海','').replace('年','-').replace('月','-').replace('日','')
                date = dt.datetime.strptime(date_str, '%Y-%m-%d').date()
                title = items[1]
            else:
                continue

            if (date is not None) and (date < since_date):
                break

            url = 'https://wsjkw.sh.gov.cn' + url
            r = requests.get(url, headers=HEADERS)
            r.encoding = 'utf-8'
            text = get_html_text(r.text)

            row = [date]
            for pattern in PATTERNS:
                n = 0
                patterns = pattern.split('/')
                for k in patterns:
                    result = re.findall(k + r'\d+' + '例', text)
                    if len(result)>0:
                        n = int(re.findall(r'\d+', result[0])[0])
                        break
                row.append(n)

            # 其中15例确诊病例为此前无症状感染者转归，12例确诊病例和19027例无症状感染者在隔离管控中发现
            # 其中17例确诊病例和2833例无症状感染者在隔离管控中发现
            result = re.findall('其中' + r'\d+' + '例确诊病例为此前无症状感染者转归', text)
            if len(result)>0:
                result = re.findall(r'\d+', result[0])
                row += result
            else:
                row += [0]

            result = re.findall(r'\d+' + '例确诊病例和' + r'\d+' + '例无症状感染者在隔离管控中发现', text)
            if len(result)>0:
                result = re.findall(r'\d+', result[0])
                row += result
            else:
                row += [0,0]

            table.append(row)

        if (date is not None) and (date < since_date):
            break

    df = pd.DataFrame(table, columns=['日期']+COLS)

    if df_old is not None:
        df = pd.concat([df_old, df[df['日期'] > since_date]]).fillna(0)

    df = df.sort_values(by='日期', ascending=True).reset_index(drop=True)
    print( tb.tabulate(df, headers='keys') )

    df.to_csv(CSV_FILE, index=False)

def func(x, a, b, c):
    return a * np.exp(b * x) + c

def load_data():
    df = pd.read_csv(CSV_FILE)
    df['新增确诊'] = df['新增本土确诊'] + df['新增输入确诊']
    df['新增无症状'] = df['新增本土无症状'] + df['新增输入无症状']

    df['累计确诊'] = df['新增确诊'].cumsum()
    df['累计无症状'] = df['新增无症状'].cumsum()
    df['累计感染'] = df['累计无症状'] + df['累计确诊']
    df['累计治愈出院'] = df['治愈出院'].cumsum()
    df['累计解除观察'] = df['解除观察'].cumsum()

    df['隔离观察中'] = df['累计感染'] - df['累计解除观察']
    df['确诊率(%)'] = (df['累计确诊'] / df['累计感染'] * 100).round(1)

    df['新增确诊+无症状'] = df['新增确诊'] + df['新增无症状']
    df['新增受控确诊+无症状'] = df['转归病例'] + df['管控确诊'] + df['管控无症状'] + df['新增输入确诊'] + df['新增输入无症状']
    df['野生确诊+无症状'] = df['新增确诊+无症状'] - df['新增受控确诊+无症状']

    df['野生占比(%)'] = (df['野生确诊+无症状'] / df['新增确诊+无症状']).round(3) * 100.0

    #print( tb.tabulate(df, headers='keys') )
    return df

def draw_table( since_date ):
    df = load_data()
    df_plot = df[ df['日期'] > since_date ].copy()

    table_columns = ['日期','新增确诊','新增无症状','治愈出院','解除观察','新增死亡']
    table_array = df_plot[ table_columns ].tail(32).values

    fig, ax1 = plt.subplots(nrows=1, ncols=1, figsize = (6,8), tight_layout = True)
    ax1.axis('tight')
    ax1.axis('off')
    ax1.table(
        cellText = table_array,
        colLabels = table_columns,
        loc = 'center',
        )
    ax1.set_title('上海 2022 新冠疫情 \n(数据来源: 上海市卫健委官网)')

    # support Chinese font
    plt.rcParams['font.sans-serif'] = ['SimHei'] # Chinese font
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams["axes.unicode_minus"] = False

    plt.tight_layout()
    plt.show()

def plot_csv( since_date, fit = False ):
    df = load_data()
    df_plot = df[ df['日期'] > since_date ].copy()

    df_plot_columns = ['新增感染']

    if fit:
        df_fit = df_plot[ df_plot['日期'] < FIT_END_DATE ]
        xdata = df_fit.index - df_fit.index[0]
        ydata = df_fit['新增本土']
        popt, pcov = curve_fit(func, xdata, ydata)
        fit_label = ('\n原趋势 拟合曲线:\ny = a * exp(b * x) + c\na=%5.3f, b=%5.3f, c=%5.3f\n' % tuple(popt))

        fit_end_date = dt.datetime.strptime(FIT_END_DATE, '%Y-%m-%d')
        fit_today_days = (datetime_today() - fit_end_date).days
        predict_start_date = datetime_today() - dt.timedelta(days=PREDICT_DAYS)
        fit_label += '\n原趋势 预测 (确诊+无症状):'
        for i in range(fit_today_days):
            predict_date = fit_end_date + dt.timedelta(i)
            if(predict_date < predict_start_date):
                continue
            fit_label += '\n' + predict_date.strftime('%Y-%m-%d') + ': '+str(int(func((xdata[-1]+1+i), *popt)))

        y = df_plot['累计无症状'].iloc[-1]
        for i in range(100):
            dy = int(func((xdata[-1]+1+i), *popt))
            y += dy
            if y > 25000000 / 5:
                fit_label += '\n\n原趋势 将于 ' + (fit_end_date + dt.timedelta(i)).strftime('%Y-%m-%d') + '\n感染累计20%人口，\n该日将'
                fit_label += '\n感染：'+ str(dy)
                fit_label += '\n确诊: ' + str(int(dy* df['确诊率(%)'].iloc[-1]/100.0))
                break

        fit_label += '\n\n若有效阻断传播，将早日迎来拐点'

        xdata = df_plot.index - df_plot.index[0]
        df_plot[ fit_label ] = func(xdata, *popt)
        df_plot_columns.append(fit_label)

    df_plot.index = df_plot['日期']

    plt.close('all')
    fig = plt.figure()
    fig.set_figwidth(8)
    fig.set_figheight(10)
    ax1 = plt.subplot(321)
    ax2 = plt.subplot(322)
    ax3 = plt.subplot(323)
    ax4 = plt.subplot(324)
    ax5 = plt.subplot(325)
    ax6 = plt.subplot(326)

    plot_config = [
        [ax1, '确诊病例 新增', ['新增确诊','治愈出院']],
        [ax2, '无症状感染者 新增', ['新增无症状','解除观察']],
        [ax3, '野生(不在管控中)确诊+无症状', ['野生确诊+无症状']],
        [ax4, '新增确诊+无症状 野生占比(%)', ['野生占比(%)']],
        [ax5, '确诊病例 累计', ['累计确诊','累计治愈出院','在院治疗']],
        [ax6, '无症状感染者 累计', ['累计无症状','累计解除观察','隔离观察中']],
    ]
    for params in plot_config:
        ax = params[0]
        title = params[1]
        cols = params[2]
        df_plot[ cols ].plot(
            ax= ax,
            xlabel= '',
            ylabel= '',
            title= title,
        )
        ax.tick_params(axis='x', rotation= 45)

    # support Chinese font
    plt.rcParams['font.sans-serif'] = ['SimHei'] # Chinese font
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams["axes.unicode_minus"] = False

    plt.tight_layout()
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

    since_date = SINCE_DATE

    fit = False
    for k in options:
        if k in ['-v', '--version']:
            print(__version__, '\n')
            return

        if k in ['-fit']:
            fit = True

        if k.startswith('-since='):
            since_str = k.replace('-since=','')
            since_date = dt.datetime.strptime(since_str, '%Y%m%d').strftime('%Y-%m-%d')

        elif k.startswith('-days='):
            days_str = k.replace('-days=','')
            since_date = (datetime_today() - dt.timedelta(days=int(days_str))).strftime('%Y-%m-%d')

    if ('-update' in options) or (not os.path.exists(CSV_FILE)) or out_of_date(CSV_FILE):
        parse_html_to_csv(since_date, test= ('-test' in options))

    if '-test' in options:
        return

    if '-table' in options:
        draw_table(PLOT_SINCE_DATE)
        return

    plot_csv(PLOT_SINCE_DATE, fit)

cli_main()
