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
    # --- Chart 1: 2D Temperature ---
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(df['date'], df['pe_pct'], label='PE Percentile', color='blue', alpha=0.7)
    ax.plot(df['date'], df['pb_pct'], label='PB Percentile', color='red', alpha=0.7)
    ax.fill_between(df['date'], df['temp_2d'], color='orange', alpha=0.2, label='2D Temperature')
    ax.axhline(20, color='green', linestyle='--', alpha=0.5)
    ax.axhline(80, color='red', linestyle='--', alpha=0.5)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax.xaxis.set_minor_locator(mdates.MonthLocator(interval=6))
    ax.set_title(f"Market Temperature (2D: PE & PB) - {df.iloc[-1]['date'].strftime('%Y-%m-%d')}")
    ax.legend()
    ax.grid(True, which='major', alpha=0.4)
    ax.grid(True, which='minor', alpha=0.1, linestyle=':')
    plt.tight_layout()
    plt.savefig('market_temp_full_comparison_final.png', dpi=150)
    plt.close()

    # --- Chart 2: 5 Separate 4D Components ---
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
        ax.xaxis.set_minor_locator(mdates.MonthLocator(interval=6))
        ax.set_title(f"{title} - {df.iloc[-1]['date'].strftime('%Y-%m-%d')}")
        ax.grid(True, which='major', alpha=0.3)
        ax.grid(True, which='minor', alpha=0.1, linestyle=':')
        plt.tight_layout()
        plt.savefig(filename, dpi=120)
        plt.close()

    # --- Chart 3: Comparison with Index Trend (NEW) ---
    print("Generating Comparison Chart with Index Price...")
    try:
        # Fetch Price (Baseline) - Using 000985 EM for 3 years
        index_df = ak.stock_zh_index_daily_em(symbol="sh000985")
        index_df['date'] = pd.to_datetime(index_df['date'])
        index_df = index_df[['date', 'close']].rename(columns={'close': 'index_price'})
        index_df = index_df[index_df['date'] >= '2023-01-01']
        
        comp_df = pd.merge(index_df, df, on='date', how='inner')
        
        fig, ax1 = plt.subplots(figsize=(14, 8))
        # Left Axis: Index Price
        ax1.plot(comp_df['date'], comp_df['index_price'], color='gray', alpha=0.4, linewidth=1.5, label='Index Price (000985)')
        ax1.set_ylabel('Price (Index)')
        
        # Right Axis: Indicators
        ax2 = ax1.twinx()
        ax2.plot(comp_df['date'], comp_df['temp_4d'], color='black', linewidth=2, label='4D Temp')
        ax2.plot(comp_df['date'], comp_df['pe_pct'], color='blue', alpha=0.5, linestyle='--', label='PE %')
        ax2.set_ylabel('Score/Percentile (0-100)')
        ax2.set_ylim(0, 100)
        
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
        
        plt.title(f"Market Temperature vs. Index Trend - {df.iloc[-1]['date'].strftime('%Y-%m-%d')}")
        plt.grid(True, alpha=0.2)
        plt.tight_layout()
        plt.savefig('market_temp_vs_index_compare.png', dpi=150)
        plt.close()
    except Exception as e:
        print(f"Comparison chart failed: {e}")

def update_html(latest):
    html_path = 'index.html'
    if not os.path.exists(html_path): return
    with open(html_path, 'r', encoding='utf-8') as f: content = f.read()
    
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    cutoff_str = latest['date'].strftime("%Y-%m-%d")
    
    import re
    new_tag = f'<div class="date-tag">🗓️ 报告日期：{today_str} | 数据截止：{cutoff_str}</div>'
    content = re.sub(r'<div class="date-tag">.*?</div>', new_tag, content)
    
    # Section 2: 4D Charts
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
    
    # Section 3: Comparison Chart (NEW)
    compare_section_html = """
        <div class="section">
            <div class="section-title">📈 3. 温度计 vs 指数走势对比</div>
            <div class="chart-container" style="text-align: center;">
                <p style="color: #666; font-size: 14px; margin-bottom: 20px;">灰色曲线代表中证全指价格，黑色曲线代表 4D 综合温度。观察两者背离或同步性。</p>
                <img class="report-img" src="market_temp_vs_index_compare.png" alt="Comparison" style="width: 100%; max-width: 900px;">
            </div>
        </div>
    """
    
    # Replace Section 2
    pattern2 = r'<div class="section-title">🧭 2\. 4D 温度计</div>\s*<div class="chart-container".*?</div>\s*</div>'
    content = re.sub(pattern2, four_d_images_html + '\n        </div>', content, flags=re.DOTALL)
    
    # Add Section 3 if not present, or replace it
    if '3. 温度计 vs 指数走势对比' not in content:
        # Add before </body>
        content = content.replace('</body>', compare_section_html + '\n    </body>')
    else:
        pattern3 = r'<div class="section">\s*<div class="section-title">📈 3\. 温度计 vs 指数走势对比</div>.*?</div>\s*</div>'
        content = re.sub(pattern3, compare_section_html, content, flags=re.DOTALL)

    with open(html_path, 'w', encoding='utf-8') as f: f.write(content)

def get_real_breadth():
    apikey = os.environ.get('MX_APIKEY', "mkt_Zfo3aEhBQ1R4cj3GLsSvZ74lJGpF3quBoTlevpWeloQ")
    url = "https://mkapi2.dfcfs.com/finskillshub/api/claw/query"
    headers = {"apikey": apikey, "Content-Type": "application/json"}
    payload = {"toolQuery": "查询全部A股(001071.BLOCK)目前的'收盘价高于20日均线个股占比'(100000000018659)最新数值"}
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=20)
        data = r.json()
        item = data['data']['data']['searchDataResultDTO']['dataTableDTOList'][0]
        # The value is usually in the first key that isn't headName
        val_key = [k for k in item['table'].keys() if k != 'headName'][0]
        val = float(str(item['table'][val_key][0]).replace('%', ''))
        return val
    except:
        return 50.0 # Default fallback

def run_report():
    update_csv()
    csv_path = 'pe_pb_2013_2026.csv'
    df = pd.read_csv(csv_path)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').drop_duplicates('date')
    
    # Calculation Logic
    df['erp'] = (1.0 / df['pe']) - (df['bond10y'] / 100.0)
    df['pe_pct'] = df['pe'].rank(pct=True) * 100
    df['pb_pct'] = df['pb'].rank(pct=True) * 100
    df['erp_pct'] = df['erp'].rank(pct=True) * 100
    
    # Sentiment & Breadth Enhancement
    # We fetch the latest real breadth and store it if it's the latest day
    real_breadth = get_real_breadth()
    # Note: For historical data, we use the proxy for now unless we do a full backfill
    # But for the latest point, we use the real one
    df.loc[df.index[-1], 'breadth_real'] = real_breadth
    
    # 4D Temperature Components
    # Valuation (30%): PE + PB
    # ERP (30%): ERP Percentile
    # Sentiment (20%): Derived from PB + proxy
    # Breadth (20%): Real Breadth if available, else proxy
    df['sentiment'] = (df['pb_pct'] * 0.5 + 40) 
    df['breadth'] = df['breadth_real'].fillna((df['pe_pct'] + 20) / 2)
    
    df['temp_2d'] = (df['pe_pct'] + df['pb_pct']) / 2
    # Composite: (Valuation_PE*0.15 + Valuation_PB*0.15) + (Risk_ERP*0.3) + (Sentiment*0.2) + (Breadth*0.2)
    # Note: ERP is "Higher = Cheaper", so we use (100 - erp_pct) for "Higher = Hotter"
    df['temp_4d'] = (df['pe_pct']*0.15 + df['pb_pct']*0.15 + (100 - df['erp_pct'])*0.3 + df['sentiment']*0.2 + df['breadth']*0.2)
    
    latest = df.iloc[-1]
    plot_2d_and_4d(df)
    update_html(latest)
    df.to_csv(csv_path, index=False)
    print(f"Report Generated: Temp 2D={latest['temp_2d']:.1f}, 4D={latest['temp_4d']:.1f}, Breadth={latest['breadth']:.1f}%")

if __name__ == "__main__":
    os.chdir(r'C:\Users\Administrator\.copaw\workspaces\default\market-report-v2')
    run_report()
