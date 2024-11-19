import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objs as go
import streamlit as st

def get_stock_data(ticker, start_date, end_date):
    # 使用 yfinance 下载股票数据
    df = yf.download(ticker, start=start_date, end=end_date, interval='30m')
    return df

def find_support_resistance(df, lookback_period, min_touch, tolerance):
    supports = []
    resistances = []
    
    lookback_data = df.tail(lookback_period)

    for i in range(len(lookback_data)):
        window = lookback_data['Close'].iloc[max(0, i-10):i+10]
        local_min = window.min()
        local_max = window.max()

        if (np.abs(window - local_min) <= tolerance).sum() >= min_touch:
            if not any(abs(local_min - s[1]) <= tolerance for s in supports):
                supports.append((lookback_data.index[i], local_min))

        if (np.abs(window - local_max) <= tolerance).sum() >= min_touch:
            if not any(abs(local_max - r[1]) <= tolerance for r in resistances):
                resistances.append((lookback_data.index[i], local_max))

    return supports, resistances

def main():
    st.title('股票支撑和阻力识别')

    default_start_date = '2023-01-01'
    default_end_date = '2023-12-31'

    start_date = st.text_input('开始日期（格式：YYYY-MM-DD）', default_start_date)
    end_date = st.text_input('结束日期（格式：YYYY-MM-DD）', default_end_date)
    ticker = st.text_input('股票代码', '000300.SS')  # 例如 'AAPL' 或 '000300.SS'（沪深300）

    lookback_period = st.number_input('回溯窗口期（数据点数）', min_value=8, max_value=500, value=48, step=8)
    min_touch = st.number_input('最小触碰次数', min_value=1, max_value=20, value=3, step=1)
    tolerance = st.number_input('支撑/阻力容忍度', min_value=0.1, max_value=50.0, value=10.0, step=0.1)

    try:
        df = get_stock_data(ticker, start_date, end_date)
        if df.empty:
            st.error("未能获取到交易数据，请检查股票代码和日期范围。")
        else:
            # 支撑和阻力识别
            supports, resistances = find_support_resistance(df, lookback_period, min_touch, tolerance)

            if supports:
                st.subheader('支撑位')
                support_df = pd.DataFrame(supports, columns=['时间', '支撑价格'])
                st.table(support_df)
            else:
                st.write("没有找到支撑位")

            if resistances:
                st.subheader('阻力位')
                resistance_df = pd.DataFrame(resistances, columns=['时间', '阻力价格'])
                st.table(resistance_df)
            else:
                st.write("没有找到阻力位")

            # 使用 Plotly 绘制交互式图表
            fig = go.Figure()

            # 添加 K 线图
            fig.add_trace(go.Candlestick(
                x=df.index,
                open=df['Open'],
                high=df['High'],
                low=df['Low'],
                close=df['Close'],
                increasing_line_color='red',
                decreasing_line_color='green',
                name='K线图',
                showlegend=False)
            )

            # 添加支撑线和标注
            for support in supports:
                fig.add_hline(y=support[1],
                              line=dict(color='blue', width=1, dash='dash'),
                              annotation_text=f"支撑: {support[1]:.2f}",
                              annotation_position="right",
                              annotation=dict(font_size=10, font_color='blue'))
            
            # 添加阻力线和标注
            for resistance in resistances:
                fig.add_hline(y=resistance[1],
                              line=dict(color='red', width=1, dash='dash'),
                              annotation_text=f"阻力: {resistance[1]:.2f}",
                              annotation_position="right",
                              annotation=dict(font_size=10, font_color='red'))

            # 设置图表布局
            fig.update_layout(
                title=f'{ticker} 30分钟K线图及支撑阻力位',
                yaxis_title='价格',
                xaxis_title='日期',
                xaxis_rangeslider_visible=False,
                plot_bgcolor='white',
                xaxis=dict(
                    type='category',
                    categoryorder='category ascending',
                    tickangle=-45
                ),
                hovermode='x unified'
            )

            st.plotly_chart(fig)
    except Exception as e:
        st.error(f"数据获取或处理出错: {e}")

if __name__ == "__main__":
    main()

