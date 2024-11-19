import tushare as ts
import pandas as pd
import plotly.graph_objs as go
import streamlit as st
from datetime import datetime, timedelta

# 设置 Tushare 的 token
ts.set_token('315d6d929a2e9cbea02854ff12517be8c93750dcd92b1715dd13f161')

# 初始化 Tushare 的 Pro API
pro = ts.pro_api()

def get_hs300_data(start_date, end_date):
    df = ts.pro_bar(ts_code='000300.SH', freq='30min', asset='I', start_date=start_date, end_date=end_date)
    df = df.sort_values(by='trade_time')
    df['trade_time'] = pd.to_datetime(df['trade_time'])
    df.set_index('trade_time', inplace=True)
    
    # 过滤掉每个交易日的第一个bar（09:30）  
    df = df[~((df.index.time == datetime.strptime('09:30', '%H:%M').time()))]

    return df

def find_support_resistance(df, lookback_period, min_touch, tolerance):
    supports = []
    resistances = []
    
    lookback_data = df.tail(lookback_period)

    for i in range(len(lookback_data)):
        window = lookback_data['close'].iloc[max(0, i-10):i+10]
        local_min = window.min()
        local_max = window.max()

        if (window <= local_min + tolerance).sum() >= min_touch:
            if not any(abs(local_min - s[1]) <= tolerance for s in supports):
                supports.append((lookback_data.index[i], local_min))

        if (window >= local_max - tolerance).sum() >= min_touch:
            if not any(abs(local_max - r[1]) <= tolerance for r in resistances):
                resistances.append((lookback_data.index[i], local_max))

    merged_supports = merge_levels(supports, tolerance)
    merged_resistances = merge_levels(resistances, tolerance)

    # 检查支撑转阻力
    for support in merged_supports[:]:
        index = df.index.get_loc(support[0])
        if index < len(df) - 2:
            if df['close'].iloc[index+1] < support[1] and df['close'].iloc[index+2] < support[1]:
                merged_supports.remove(support)
                merged_resistances.append(support)

    return merged_supports, merged_resistances

def merge_levels(levels, tolerance):
    if not levels:
        return []

    levels.sort(key=lambda x: x[1])
    merged_levels = [levels[0]]

    for current in levels[1:]:
        previous = merged_levels[-1]
        if abs(current[1] - previous[1]) < tolerance:
            average_level = (current[1] + previous[1]) / 2
            merged_levels[-1] = (current[0], average_level)
        else:
            merged_levels.append(current)

    return merged_levels

def get_previous_trading_day(date_str):
    # 获取交易日历
    trade_cal = pro.trade_cal(exchange='SSE', start_date='20200101', end_date=date_str)
    trade_days = trade_cal[trade_cal['is_open'] == 1]['cal_date'].tolist()

    current_day = datetime.strptime(date_str, '%Y%m%d')
    current_str = date_str

    while current_str not in trade_days:
        current_day -= timedelta(days=1)
        current_str = current_day.strftime('%Y%m%d')

    return current_str

# Streamlit 应用程序
st.title('支撑和阻力识别')

now = datetime.now()

# 判断是否在交易时间内
if now.hour < 15:
    default_end_date = get_previous_trading_day(now.strftime('%Y%m%d'))
else:
    default_end_date = now.strftime('%Y%m%d')

default_start_date = (datetime.strptime(default_end_date, '%Y%m%d') - pd.DateOffset(months=3)).strftime('%Y%m%d')

start_date = st.text_input('开始日期（格式：YYYYMMDD）', default_start_date)
end_date = st.text_input('结束日期（格式：YYYYMMDD）', default_end_date)

lookback_period = st.number_input('回溯窗口期（数据点数）', min_value=8, max_value=500, value=48, step=8)
min_touch = st.number_input('最小触碰次数', min_value=1, max_value=10, value=3, step=1)
tolerance = st.number_input('支撑/阻力容忍度', min_value=1, max_value=20, value=10, step=1)

try:
    df = get_hs300_data(start_date, end_date)
    if df.empty:
        st.error("未能获取到交易数据，请检查日期范围。")
    else:
        supports, resistances = find_support_resistance(df, lookback_period, min_touch, tolerance)

        if supports:
            st.subheader('支撑位')
            st.table(pd.DataFrame(supports, columns=['时间', '支撑价格']))
        else:
            st.write("没有找到支撑位")

        if resistances:
            st.subheader('阻力位')
            st.table(pd.DataFrame(resistances, columns=['时间', '阻力价格']))
        else:
            st.write("没有找到阻力位")

        # 使用 Plotly 绘制交互式图表
        fig = go.Figure()

        # 添加 K 线图
        fig.add_trace(go.Candlestick(x=df.index,
                                     open=df['open'],
                                     high=df['high'],
                                     low=df['low'],
                                     close=df['close'],
                                     increasing_line_color='red',
                                     decreasing_line_color='blue',
                                     increasing_fillcolor='red',
                                     decreasing_fillcolor='blue',
                                     line_width=1))

        # 添加支撑线和标注
        for support in supports:
            fig.add_shape(type='line',
                          x0=df.index[0], x1=df.index[-1],
                          y0=support[1], y1=support[1],
                          line=dict(color='blue', width=1, dash='dash'))
            fig.add_annotation(x=df.index[-1], y=support[1],
                               text=f"{support[1]:.2f}",
                               showarrow=False,
                               xanchor='left',
                               yanchor='middle',
                               font=dict(color='blue'))

        # 添加阻力线和标注
        for resistance in resistances:
            fig.add_shape(type='line',
                          x0=df.index[0], x1=df.index[-1],
                          y0=resistance[1], y1=resistance[1],
                          line=dict(color='red', width=1, dash='dash'))
            fig.add_annotation(x=df.index[-1], y=resistance[1],
                               text=f"{resistance[1]:.2f}",
                               showarrow=False,
                               xanchor='left',
                               yanchor='middle',
                               font=dict(color='red'))

        # 设置图表布局
        fig.update_layout(title='HS300 30-Minute K-line with Support and Resistance',
                          yaxis_title='Price',
                          xaxis_title='Date',
                          xaxis_rangeslider_visible=False,
                          plot_bgcolor='white',  # 设置背景为白色
                          xaxis=dict(type='category'))  # 确保 x 轴为类别型数据，去掉间隙

        st.plotly_chart(fig)
except Exception as e:
    st.error(f"数据获取出错: {e}")
