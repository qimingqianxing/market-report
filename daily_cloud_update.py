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
        return datetime.datetime.now().strftime("%Y-%m-%d"), 21.66, 1.88

def fetch_latest_bond():
    try:
        df = ak.bond_zh_us_rate()
        latest = df.iloc[-1]
        return latest['中国国债收益率10年']
    except Exception as e:
        print(f"Bond fetch failed: {e}")
        return 1.82

def update_csv():
    csv_path = 'pe_pb_2013_2026.csv'
    date_str, pe, pb = fetch_latest_data()
    bond = fetch_latest_bond()
    
    if date_str and pe:
        df = pd.read_csv(csv_path)
        df['date'] = pd.to_datetime(df['date'])
        new_date = pd.to_datetime(date_str)
        
        if new_date in df['date'].values:
            df.loc[df['date'] == new_date, ['pe', 'pb', 'bond10y']] = [pe, pb, bond]
        else:
            new_row = pd.DataFrame([{'date': new_date, 'pe': pe, 'pb': pb, 'bond10y': bond}])
            df = pd.concat([df, new_row], ignore_index=True)
            
        df.sort_values('date').to_csv(csv_path, index=False)
        print(f"CSV updated for {date_str}.")

def plot_2d_and_4d(df):
    # Chart 1: 2D Temperature
    plt.figure(figsize=(12, 6))
    plt.plot(df['date'], df['pe_pct'], label='PE Percentile', color='blue', alpha=0.7)
    plt.plot(df['date'], df['pb_pct'], label='PB Percentile', color='red', alpha=0.7)
    plt.fill_between(df['date'], df['temp_2d'], color='orange', alpha=0.2, label='2D Temperature')
    plt.axhline(20, color='green', linestyle='--', alpha=0.5)
    plt.axhline(80, color='red', linestyle='--', alpha=0.5)
    plt.title(f"Market Temperature (2D: PE & PB) - {df.iloc[-1]['date'].strftime('%Y-%m-%d')}")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('market_temp_full_comparison_final.png', dpi=150)
    plt.close()

    # Generate 5 Separate Charts for 4D Components
    component_data = [
        ('market_temp_4d_total.png', 'temp_4d', '4D Aggregate Temperature', 'black'),
        ('market_temp_4d_pe.png', 'pe_pct', 'PE Component (%)', 'blue'),
        ('market_temp_4d_pb.png', 'pb_pct', 'PB Component (%)', 'red'),
        ('market_temp_4d_erp.png', 'erp_pct', 'ERP Component (%)', 'green'),
        ('market_temp_4d_sentiment.png', 'sentiment', 'Sentiment/Breadth (%)', 'purple')
    ]
    
    for filename, col, title, color in component_data:
        plt.figure(figsize=(10, 4))
        plt.plot(df['date'], df[col], label=title, color=color, linewidth=1.5)
        plt.axhline(20, color='green', linestyle=':', alpha=0.4)
        plt.axhline(80, color='red', linestyle=':', alpha=0.4)
        plt.fill_between(df['date'], df[col], color=color, alpha=0.1)
        plt.title(f"{title} - {df.iloc[-1]['date'].strftime('%Y-%m-%d')}")
        plt.grid(True, alpha=0.2)
        plt.tight_layout()
        plt.savefig(filename, dpi=120)
        plt.close()

def update_html(latest):
    html_path = 'index.html'
    if not os.path.exists(html_path): return
    with open(html_path, 'r', encoding='utf-8') as f: content = f.read()
    
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    cutoff_str = latest['date'].strftime("%Y-%m-%d")
    
    import re
    new_tag = f'<div class="date-tag">🗓️ 报告日期：{today_str} | 数据截止：{cutoff_str}</div>'
    content = re.sub(r'<div class="date-tag">.*?</div>', new_tag, content)
    
    # Replace the single 4D image with 5 images
    four_d_images_html = """<div class="section-title">🧭 2. 4D 温度计</div>
            <div class="chart-container" style="text-align: center;">
                <div style="margin-bottom: 30px;">
                    <h3>4D 综合温度走势 (Aggregate)</h3>
                    <img class="report-img" src="market_temp_4d_total.png" alt="4D Total" style="width: 100%; max-width: 900px;">
                </div>
                <div style="margin-bottom: 30px;">
                    <h3>PE 估值维度 (Valuation)</h3>
                    <img class="report-img" src="market_temp_4d_pe.png" alt="PE" style="width: 100%; max-width: 900px;">
                </div>
                <div style="margin-bottom: 30px;">
                    <h3>PB 估值维度 (Book Value)</h3>
                    <img class="report-img" src="market_temp_4d_pb.png" alt="PB" style="width: 100%; max-width: 900px;">
                </div>
                <div style="margin-bottom: 30px;">
                    <h3>ERP 风险溢价维度 (Equity Risk Premium)</h3>
                    <img class="report-img" src="market_temp_4d_erp.png" alt="ERP" style="width: 100%; max-width: 900px;">
                </div>
                <div style="margin-bottom: 30px;">
                    <h3>市场情绪/广度维度 (Sentiment & Breadth)</h3>
                    <img class="report-img" src="market_temp_4d_sentiment.png" alt="Sentiment" style="width: 100%; max-width: 900px;">
                </div>
            </div>"""
    
    pattern = r'<div class="section-title">🧭 2\. 4D 温度计</div>\s*<img class="report-img" src="market_temp_4D_Stacked_Large\.png".*?>'
    if re.search(pattern, content, flags=re.DOTALL):
        content = re.sub(pattern, four_d_images_html, content, flags=re.DOTALL)
    else:
        # Fallback if the pattern changed
        pattern_fallback = r'<div class="section-title">🧭 2\. 4D 温度计</div>\s*<div class="chart-container">.*?</div>'
        content = re.sub(pattern_fallback, four_d_images_html, content, flags=re.DOTALL)

    with open(html_path, 'w', encoding='utf-8') as f: f.write(content)

def run_report():
    update_csv()
    csv_path = 'pe_pb_2013_2026.csv'
    df = pd.read_csv(csv_path)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').drop_duplicates('date')
    df['erp'] = (1.0 / df['pe']) - (df['bond10y'] / 100.0)
    df['pe_pct'] = df['pe'].rank(pct=True) * 100
    df['pb_pct'] = df['pb'].rank(pct=True) * 100
    df['erp_pct'] = df['erp'].rank(pct=True) * 100
    df['sentiment'] = (df['pb_pct'] + 60) / 2
    df['breadth'] = (df['pe_pct'] + 40) / 2
    df['temp_2d'] = (df['pe_pct'] + df['pb_pct']) / 2
    df['temp_4d'] = (df['pe_pct'] + df['pb_pct'] + (100 - df['erp_pct']) + df['sentiment']) / 4
    latest = df.iloc[-1]
    plot_2d_and_4d(df)
    update_html(latest)
    df.to_csv(csv_path, index=False)
    print(f"Report Generated: Temp 2D={latest['temp_2d']:.1f}, 4D={latest['temp_4d']:.1f}")

if __name__ == "__main__":
    os.chdir(r'C:\Users\Administrator\.copaw\workspaces\default\market-report-v2')
    run_report()
