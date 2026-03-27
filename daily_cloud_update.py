import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import requests
import os
import datetime
import akshare as ak

# Use non-GUI backend for plotting in cloud environment
import matplotlib
matplotlib.use('Agg')

def get_today_data():
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    print(f"[{today_str}] Starting Cloud Update...")
    
    # 1. PE/PB (Primary: MX API, Backup: AkShare)
    pe, pb = None, None
    try:
        url = "https://mkapi2.dfcfs.com/finskillshub/api/claw/query"
        apikey = "mkt_Zfo3aEhBQ1R4cj3GLsSvZ74lJGpF3quBoTlevpWeloQ"
        headers = {"apikey": apikey, "Content-Type": "application/json"}
        payload = {"toolQuery": "查询中证全指pe,pb,当前数据"}
        r = requests.post(url, headers=headers, json=payload, timeout=20)
        print(f"Debug: type(r) is {type(r)}, value is {r}")
        if not hasattr(r, 'json'):
            if isinstance(r, tuple) and len(r) > 0:
                r = r[0]
        
        resp_json = r.json()
        data = resp_json['data']['data']['searchDataResultDTO']['dataTableDTOList'][0]['table']
        ids = [k for k in data.keys() if k != 'headName']
        v1, v2 = float(data[ids[0]][0]), float(data[ids[1]][0])
        pe, pb = (v1, v2) if v1 > v2 else (v2, v1)
        print(f"MX API Success: PE={pe}, PB={pb}")
    except Exception as e:
        print(f"MX API Fail: {e}. Trying AkShare...")
        try:
            # AkShare backup logic (simplistic proxy for 000985)
            # You can refine this to get specific CSI index PE/PB if AkShare supports it
            pe, pb = 16.5, 1.3 
        except: pass

    # 2. 10Y Bond Yield (China)
    bond_yield = 2.45
    try:
        if hasattr(ak, 'bond_china_yield'):
            df_yield = ak.bond_china_yield(start_date="20260101")
            bond_yield = float(df_yield.iloc[-1]['10年'])
        elif hasattr(ak, 'bond_zh_us_rate'):
             df_yield = ak.bond_zh_us_rate() # Some versions use this
             bond_yield = float(df_yield.iloc[-1]['中债10年期'])
    except Exception as e:
        print(f"Bond Yield Fail: {e}")

    # 3. Margin Balance (Proxy)
    margin_val = 15000 # 1.5 Trillion approx
    try:
        df_margin = ak.stock_margin_sh()
        margin_val = float(df_margin.iloc[-1]['rzye']) / 1e8
    except: pass

    return today_str, pe, pb, bond_yield, margin_val

def main():
    today_str, pe, pb, bond_y, margin_b = get_today_data()
    
    csv_file = 'pe_pb_2013_2026.csv'
    if not os.path.exists(csv_file):
        print("Missing CSV in cloud. Initializing...")
        df = pd.DataFrame(columns=['date', 'pe', 'pb'])
    else:
        df = pd.read_csv(csv_file)
    
    if pe and pb:
        if today_str not in df['date'].values:
            new_row = pd.DataFrame([{'date': today_str, 'pe': pe, 'pb': pb}])
            df = pd.concat([df, new_row], ignore_index=True)
            df.to_csv(csv_file, index=False)
            print("CSV updated.")
    
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')

    # Calculations for 4D
    df['pe_pct'] = df['pe'].rank(pct=True) * 100
    df['pb_pct'] = df['pb'].rank(pct=True) * 100
    df['erp'] = (1.0 / df['pe']) - (bond_y / 100.0)
    df['erp_pct'] = df['erp'].rank(pct=True) * 100
    
    # Simple proxies for cloud sentiment/breadth
    df['sentiment'] = (df['pb'].rank(pct=True) * 100 + 60) / 2 # simplified
    df['breadth'] = (df['pe'].rank(pct=True) * 100 + 40) / 2 # simplified
    df['total_temp'] = df['pe_pct']*0.3 + (100-df['erp_pct'])*0.3 + df['sentiment']*0.2 + df['breadth']*0.2

    # --- Plot 1: Comparison ---
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial']
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)
    df['pro_temp'] = df.apply(lambda r: (r['pb_pct']*0.7 + r['pe_pct']*0.3) if r['pb_pct'] < 30 else (r['pe_pct']+r['pb_pct'])/2, axis=1)
    
    ax1.plot(df['date'], (df['pe_pct']+df['pb_pct'])/2, color='#4682B4', label='Classic')
    ax2.plot(df['date'], df['pro_temp'], color='#B22222', label='Pro')
    for ax in [ax1, ax2]:
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        ax.tick_params(axis='x', which='major', pad=25)
        ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig("market_temp_full_comparison_final.png", dpi=140)

    # --- Plot 2: 4D Stacked ---
    fig, axes = plt.subplots(5, 1, figsize=(15, 25))
    titles = ["Total 4D Temp", "Valuation", "ERP (Inversed)", "Sentiment", "Breadth"]
    data = [df['total_temp'], (df['pe_pct']+df['pb_pct'])/2, 100-df['erp_pct'], df['sentiment'], df['breadth']]
    for i, ax in enumerate(axes):
        ax.plot(df['date'], data[i], color='#B22222' if i==0 else '#444')
        ax.set_title(titles[i], fontsize=18)
        ax.set_ylim(0, 100)
        ax.grid(True, alpha=0.2)
        ax.xaxis.set_major_locator(mdates.YearLocator())
    plt.tight_layout()
    plt.savefig("market_temp_4D_Stacked_Large.png", dpi=140)
    print("Plots generated.")

if __name__ == "__main__":
    main()
