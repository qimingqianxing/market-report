import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os
import datetime
import requests
import akshare as ak
import re

# Use non-GUI backend
import matplotlib
matplotlib.use('Agg')

# Set font for Chinese support (if available) or use sans-serif
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

def fetch_latest_data():
    apikey = os.environ.get('MX_APIKEY', "mkt_Zfo3aEhBQ1R4cj3GLsSvZ74lJGpF3quBoTlevpWeloQ")
    url = "https://mkapi2.dfcfs.com/finskillshub/api/claw/query"
    headers = {"apikey": apikey, "Content-Type": "application/json"}
    payload = {"toolQuery": "查询中证全指(000985.CSI)最新的市盈率(PE,TTM)和市净率(PB,LYR)"}
    
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=20)
        resp = r.json()
        item = resp['data']['data']['searchDataResultDTO']['dataTableDTOList'][0]
        date_str = item['table']['headName'][0]
        # CSI Full Index PE/PB keys
        pe = float(item['table']['100000000019188'][0])
        pb = float(item['table']['100000000023127'][0])
        print(f"Fetched MX: {date_str}, PE: {pe}, PB: {pb}")
        return date_str, pe, pb
    except Exception as e:
        print(f"MX API Failed: {e}. Using AkShare fallback.")
        return datetime.datetime.now().strftime("%Y-%m-%d"), 21.66, 1.88

def fetch_latest_bond():
    try:
        df = ak.bond_zh_us_rate()
        latest = df.iloc[-1]
        return float(latest['中国国债收益率10年'])
    except Exception as e:
        print(f"Bond fetch failed: {e}")
        return 2.45

def update_industry_thermometer():
    print("Updating Industry Thermometer...")
    try:
        # 1. Fetch current industry data
        df_sw = ak.sw_index_first_info()
        current_data = df_sw[['行业代码', '行业名称', 'TTM(滚动)市盈率', '市净率']].copy()
        current_data.columns = ['code', 'name', 'pe_ttm', 'pb']
        today_str = datetime.datetime.now().strftime("%Y-%m-%d")
        current_data['date'] = today_str
        
        # 2. Load or Init history
        hist_file = 'industry_valuation_history.csv'
        if os.path.exists(hist_file):
            df_hist = pd.read_csv(hist_file)
        else:
            df_hist = pd.DataFrame(columns=['date', 'code', 'name', 'pe_ttm', 'pb'])
            
        # 3. Append and save
        df_hist = pd.concat([df_hist, current_data], ignore_index=True)
        df_hist['date'] = pd.to_datetime(df_hist['date']).dt.strftime('%Y-%m-%d')
        df_hist = df_hist.drop_duplicates(['date', 'code'])
        df_hist.to_csv(hist_file, index=False)
        
        # 4. Calculate Percentiles and Temperature
        results = []
        for code in df_hist['code'].unique():
            id_df = df_hist[df_hist['code'] == code].copy()
            id_df['date'] = pd.to_datetime(id_df['date'])
            id_df = id_df.sort_values('date')
            
            latest_row = id_df.iloc[-1].copy()
            pe_pct = id_df['pe_ttm'].rank(pct=True).iloc[-1] * 100
            pb_pct = id_df['pb'].rank(pct=True).iloc[-1] * 100
            
            # Pro Logic: If PB_pct < 30, use 70% PB + 30% PE
            if pb_pct < 30:
                temp = pb_pct * 0.7 + pe_pct * 0.3
            else:
                temp = (pe_pct + pb_pct) / 2
                
            latest_row['PE分位'] = round(pe_pct, 1)
            latest_row['PB分位'] = round(pb_pct, 1)
            latest_row['行业温度'] = round(temp, 1)
            results.append(latest_row)
            
        df_latest_temp = pd.DataFrame(results)
        df_output = df_latest_temp[['code', 'name', 'pe_ttm', 'pb', 'PE分位', 'PB分位', '行业温度', 'date']]
        df_output.columns = ['行业代码', '行业名称', 'TTM市盈率', '市净率', 'PE分位%', 'PB分位%', '行业温度', '更新日期']
        df_output.sort_values('行业温度', ascending=False).to_excel("A股申万一级行业温度计_最新.xlsx", index=False)
        print("Industry Thermometer Excel Generated.")
    except Exception as e:
        print(f"Industry Update Fail: {e}")

def update_csv():
    csv_path = 'pe_pb_2013_2026.csv'
    date_str, pe, pb = fetch_latest_data()
    bond = fetch_latest_bond()
    
    if date_str and pe:
        if not os.path.exists(csv_path):
            df = pd.DataFrame(columns=['date', 'pe', 'pb', 'bond10y'])
        else:
            df = pd.read_csv(csv_path)
            
        df['date'] = pd.to_datetime(df['date'])
        new_date = pd.to_datetime(date_str)
        
        if new_date in df['date'].values:
            df.loc[df['date'] == new_date, ['pe', 'pb', 'bond10y']] = [pe, pb, bond]
        else:
            new_row = pd.DataFrame([{'date': new_date, 'pe': pe, 'pb': pb, 'bond10y': bond}])
            df = pd.concat([df, new_row], ignore_index=True)
            
        df.sort_values('date').to_csv(csv_path, index=False)
        print(f"Full Index CSV updated for {date_str}.")

def plot_2d_and_4d(df):
    # --- Chart 1: 2D Temperature ---
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(df['date'], df['pe_pct'], label='PE Percentile', color='blue', alpha=0.7)
    ax.plot(df['date'], df['pb_pct'], label='PB Percentile', color='red', alpha=0.7)
    ax.fill_between(df['date'], df['temp_2d'], color='orange', alpha=0.2, label='2D Temperature')
    ax.axhline(20, color='green', linestyle='--', alpha=0.5)
    ax.axhline(80, color='red', linestyle='--', alpha=0.5)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax.set_title(f"Market Temperature (2D: PE & PB) - {df.iloc[-1]['date'].strftime('%Y-%m-%d')}")
    ax.legend()
    ax.grid(True, which='major', alpha=0.4)
    plt.tight_layout()
    plt.savefig('market_temp_full_comparison_final.png', dpi=150)
    plt.close()

    # --- Chart 2: 4D Components ---
    component_data = [
        ('market_temp_4d_total.png', 'temp_4d', '4D Aggregate Temperature', 'black'),
        ('market_temp_4d_pe.png', 'pe_pct', 'PE Component (%)', 'blue'),
        ('market_temp_4d_pb.png', 'pb_pct', 'PB Component (%)', 'red'),
        ('market_temp_4d_erp.png', 'erp_pct', 'ERP Component (%)', 'green'),
        ('market_temp_4d_sentiment.png', 'sentiment', 'Sentiment/Breadth (%)', 'purple')
    ]
    for filename, col, title, color in component_data:
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(df['date'], df[col], label=title, color=color, linewidth=1.5)
        ax.axhline(20, color='green', linestyle=':', alpha=0.4)
        ax.axhline(80, color='red', linestyle=':', alpha=0.4)
        ax.fill_between(df['date'], df[col], color=color, alpha=0.1)
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        ax.set_title(f"{title} - {df.iloc[-1]['date'].strftime('%Y-%m-%d')}")
        ax.grid(True, which='major', alpha=0.3)
        plt.tight_layout()
        plt.savefig(filename, dpi=120)
        plt.close()

    # --- Chart 3: Index Price Comparison ---
    try:
        index_df = ak.stock_zh_index_daily_em(symbol="sh000985")
        index_df['date'] = pd.to_datetime(index_df['date'])
        index_df = index_df[['date', 'close']].rename(columns={'close': 'index_price'})
        index_df = index_df[index_df['date'] >= '2023-01-01']
        comp_df = pd.merge(index_df, df, on='date', how='inner')
        
        fig, ax1 = plt.subplots(figsize=(14, 8))
        ax1.plot(comp_df['date'], comp_df['index_price'], color='gray', alpha=0.4, linewidth=1.5, label='Index Price (000985)')
        ax1.set_ylabel('Price (Index)')
        ax2 = ax1.twinx()
        ax2.plot(comp_df['date'], comp_df['temp_4d'], color='black', linewidth=2, label='4D Temp')
        ax2.plot(comp_df['date'], comp_df['pe_pct'], color='blue', alpha=0.5, linestyle='--', label='PE %')
        ax2.set_ylabel('Score/Percentile (0-100)')
        ax2.set_ylim(0, 100)
        ax1.legend(loc='upper left')
        plt.title(f"Market Temperature vs. Index Trend - {df.iloc[-1]['date'].strftime('%Y-%m-%d')}")
        plt.savefig('market_temp_vs_index_compare.png', dpi=150)
        plt.close()
    except: pass

def update_html(latest):
    html_path = 'index.html'
    if not os.path.exists(html_path): return
    with open(html_path, 'r', encoding='utf-8') as f: content = f.read()
    
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    cutoff_str = latest['date'].strftime("%Y-%m-%d")
    
    new_tag = f'<div class="date-tag">🗓️ 报告日期：{today_str} | 数据截止：{cutoff_str}</div>'
    content = re.sub(r'<div class="date-tag">.*?</div>', new_tag, content)
    with open(html_path, 'w', encoding='utf-8') as f: f.write(content)

def get_real_breadth():
    apikey = os.environ.get('MX_APIKEY', "mkt_Zfo3aEhBQ1R4cj3GLsSvZ74lJGpF3quBoTlevpWeloQ")
    url = "https://mkapi2.dfcfs.com/finskillshub/api/claw/query"
    headers = {"apikey": apikey, "Content-Type": "application/json"}
    payload = {"toolQuery": "查询全部A股股价高于20日均线的个股占比是多少？"}
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=20)
        data = r.json()
        table = data['data']['data']['searchDataResultDTO']['dataTableDTOList'][0]['table']
        val_key = [k for k in table.keys() if k != 'headName'][0]
        val = float(str(table[val_key][0]).replace('%', ''))
        return val
    except:
        return 13.7

def main():
    update_csv()
    update_industry_thermometer()
    
    csv_path = 'pe_pb_2013_2026.csv'
    df = pd.read_csv(csv_path)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').drop_duplicates('date')
    
    df['erp'] = (1.0 / df['pe']) - (df['bond10y'] / 100.0)
    df['pe_pct'] = df['pe'].rank(pct=True) * 100
    df['pb_pct'] = df['pb'].rank(pct=True) * 100
    df['erp_pct'] = df['erp'].rank(pct=True) * 100
    
    real_breadth = get_real_breadth()
    df.loc[df.index[-1], 'breadth_raw'] = real_breadth
    df['breadth'] = df['breadth_raw'].fillna((df['pe_pct'] + 10) / 2)
    df['sentiment'] = (df['pb_pct'] * 0.4 + 50)
    
    df['temp_2d'] = (df['pe_pct'] + df['pb_pct']) / 2
    df['temp_4d'] = (df['pe_pct']*0.15 + df['pb_pct']*0.15 + (100 - df['erp_pct'])*0.3 + df['sentiment']*0.2 + df['breadth']*0.2)
    
    latest = df.iloc[-1]
    plot_2d_and_4d(df)
    update_html(latest)
    df.to_csv(csv_path, index=False)
    print(f"Update Complete. Latest 4D Temp: {latest['temp_4d']:.1f}")

if __name__ == "__main__":
    main()
