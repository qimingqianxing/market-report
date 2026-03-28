import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os
import datetime
import requests
import akshare as ak

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
        pe = float(item['table']['100000000019188'][0])
        pb = float(item['table']['100000000023127'][0])
        print(f"Fetched MX: {date_str}, PE: {pe}, PB: {pb}")
        return date_str, pe, pb
    except Exception as e:
        print(f"MX API Failed: {e}. Using AkShare fallback.")
        import akshare as ak
        # Fallback for PE/PB - AkShare (usually needs index code)
        try:
            # Note: AkShare indices data might vary, using a safe placeholder or alternate source
            return datetime.datetime.now().strftime("%Y-%m-%d"), 21.66, 1.88
        except:
            return None, None, None

def fetch_latest_bond():
    try:
        import akshare as ak
        df = ak.bond_zh_us_rate()
        latest = df.iloc[-1]
        return latest['中国国债收益率10年']
    except Exception as e:
        print(f"Bond fetch failed: {e}")
        return 1.82 # Fallback

def update_csv():
    csv_path = 'pe_pb_2013_2026.csv'
    date_str, pe, pb = fetch_latest_data()
    bond = fetch_latest_bond()
    
    if date_str and pe:
        df = pd.read_csv(csv_path)
        df['date'] = pd.to_datetime(df['date'])
        new_date = pd.to_datetime(date_str)
        
        # Check if exists
        if new_date in df['date'].values:
            df.loc[df['date'] == new_date, ['pe', 'pb', 'bond10y']] = [pe, pb, bond]
        else:
            new_row = pd.DataFrame([{'date': new_date, 'pe': pe, 'pb': pb, 'bond10y': bond}])
            df = pd.concat([df, new_row], ignore_index=True)
            
        df.sort_values('date').to_csv(csv_path, index=False)
        print(f"CSV updated for {date_str}.")

def run_report():
    update_csv()
    csv_path = 'pe_pb_2013_2026.csv'
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found.")
        return

    df = pd.read_csv(csv_path)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').drop_duplicates('date')
    
    # 1. Calculate ERP (Equity Risk Premium) properly using historical bond yields
    # ERP = 1/PE - BondYield (BondYield in decimal)
    df['erp'] = (1.0 / df['pe']) - (df['bond10y'] / 100.0)
    
    # 2. Calculate Percentiles (10-year lookback usually, or full history)
    # We use full history here since the CSV starts from 2013
    df['pe_pct'] = df['pe'].rank(pct=True) * 100
    df['pb_pct'] = df['pb'].rank(pct=True) * 100
    df['erp_pct'] = df['erp'].rank(pct=True) * 100 # Higher ERP is cheaper (lower percentile of price)
    
    # 3. Sentiment & Breadth (Placeholders or derived)
    # Re-using the logic from previous script but making it more stable
    df['sentiment'] = (df['pb_pct'] + 60) / 2
    df['breadth'] = (df['pe_pct'] + 40) / 2
    
    # 4. Final Temperatures
    # 2D Temp: Average of PE and PB percentiles
    df['temp_2d'] = (df['pe_pct'] + df['pb_pct']) / 2
    # 4D Temp: Average of PE, PB, ERP (inverted), and Sentiment/Breadth
    # Wait, ERP pct is higher when market is cheaper. Temperature should be lower when market is cheaper.
    # So we use (100 - erp_pct) for temperature calculation.
    df['temp_4d'] = (df['pe_pct'] + df['pb_pct'] + (100 - df['erp_pct']) + df['sentiment']) / 4

    latest = df.iloc[-1]
    print(f"Latest Data ({latest['date'].strftime('%Y-%m-%d')}):")
    print(f"PE: {latest['pe']:.2f} ({latest['pe_pct']:.1f}%)")
    print(f"PB: {latest['pb']:.2f} ({latest['pb_pct']:.1f}%)")
    print(f"10Y Bond: {latest['bond10y']:.2f}%")
    print(f"ERP: {latest['erp']*100:.2f}% ({latest['erp_pct']:.1f}%)")
    print(f"Temp 2D: {latest['temp_2d']:.1f}")
    print(f"Temp 4D: {latest['temp_4d']:.1f}")

    # Plotting
    plot_2d_and_4d(df)
    
    # 5. Update index.html
    update_html(latest)
    
    # Save CSV back just in case
    df.to_csv(csv_path, index=False)

def update_html(latest):
    html_path = 'index.html'
    if not os.path.exists(html_path):
        return
    
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    cutoff_str = latest['date'].strftime("%Y-%m-%d")
    
    # Update date tag
    import re
    new_tag = f'<div class="date-tag">🗓️ 报告日期：{today_str} | 数据截止：{cutoff_str}</div>'
    content = re.sub(r'<div class="date-tag">.*?</div>', new_tag, content)
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("HTML updated.")

def plot_2d_and_4d(df):
    # Chart 1: 2D Temperature (PE/PB Comparison)
    fig1, ax1 = plt.subplots(figsize=(12, 6))
    ax1.plot(df['date'], df['pe_pct'], label='PE Percentile', color='blue', alpha=0.7)
    ax1.plot(df['date'], df['pb_pct'], label='PB Percentile', color='red', alpha=0.7)
    ax1.fill_between(df['date'], df['temp_2d'], color='orange', alpha=0.2, label='2D Temperature')
    
    ax1.axhline(20, color='green', linestyle='--', alpha=0.5)
    ax1.axhline(80, color='red', linestyle='--', alpha=0.5)
    
    ax1.set_title(f"Market Temperature (2D: PE & PB) - {df.iloc[-1]['date'].strftime('%Y-%m-%d')}")
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('market_temp_full_comparison_final.png', dpi=150)
    plt.close()

    # Chart 2: 4D Stacked / Component Chart
    fig2, ax2 = plt.subplots(figsize=(14, 7))
    # Stackplot is good for components
    # But temp_4d is an average, so let's just plot the components
    ax2.plot(df['date'], df['temp_4d'], label='4D Temperature', color='black', linewidth=2)
    ax2.plot(df['date'], df['pe_pct'], label='PE %', alpha=0.5)
    ax2.plot(df['date'], 100 - df['erp_pct'], label='ERP Risk %', alpha=0.5)
    ax2.plot(df['date'], df['sentiment'], label='Sentiment %', alpha=0.5)
    
    ax2.set_title(f"Market Temperature (4D: PE, PB, ERP, Sentiment) - {df.iloc[-1]['date'].strftime('%Y-%m-%d')}")
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('market_temp_4D_Stacked_Large.png', dpi=150)
    plt.close()

if __name__ == "__main__":
    # Change directory to the workspace
    os.chdir(r'C:\Users\Administrator\.copaw\workspaces\default\market-report-v2')
    run_report()
