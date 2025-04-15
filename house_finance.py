import pandas as pd
import numpy as np
import numpy_financial as npf
import plotly.express as px
import streamlit as st
from datetime import datetime

st.set_page_config(layout="wide")

def format_number(num):
    if isinstance(num, (int, float)):
        return f"{num:,.0f}".replace(",", " ") if not np.isnan(num) else "0"
    return str(num)

st.sidebar.header("Допущения")

# Основные параметры
price_per_m2 = st.sidebar.number_input("Цена продажи за м² (руб.)", 
                                     min_value=15000, 
                                     max_value=45000, 
                                     value=25000,
                                     step=1000,
                                     format="%d")

sales_m2 = st.sidebar.number_input("Продажи (м²/мес.)", 
                                 min_value=10, 
                                 max_value=2000, 
                                 value=50,
                                 step=10,
                                 format="%d")

growth_rate = st.sidebar.slider("Месячный прирост продаж (%)", 
                              0.0, 30.0, 10.0, step=1.0) / 100

# Переменные затраты
st.sidebar.subheader("Переменные затраты")
material_percent = st.sidebar.number_input("Сырьё (% от выручки)", 
                                         min_value=0, 
                                         max_value=100, 
                                         value=30,
                                         format="%d",
                                         step=1)

labor_percent = st.sidebar.number_input("Производ. персонал (% от выручки)", 
                                      min_value=0, 
                                      max_value=30, 
                                      value=10,
                                      format="%d",
                                      step=1)

total_variable_percent = material_percent + labor_percent
progress_value = min(total_variable_percent / 100, 1.0)
color = "red" if total_variable_percent > 100 else "green"
warning = " ⚠️ Превышение 100%" if total_variable_percent > 100 else ""

st.sidebar.progress(progress_value)
st.sidebar.markdown(
    f"<p style='font-size:14px; color:{color}; margin-top: -15px;'>"
    f"Итого переменные затраты: <b>{total_variable_percent}%</b> от выручки"
    f"{warning}</p>", 
    unsafe_allow_html=True
)

# Постоянные затраты
st.sidebar.subheader("Постоянные затраты (руб./мес.)")
rent_warehouse = st.sidebar.number_input("Аренда склада", 1000, 1000000, 300000, step=10000)
rent_office = st.sidebar.number_input("Аренда офиса", 1000, 1000000, 50000, step=10000)
utilities = st.sidebar.number_input("Коммуналка", 1000, 1000000, 50000, step=1000)
salary_management = st.sidebar.number_input("ЗП АУП", 1000, 1000000, 300000, step=50000)
salary_other = st.sidebar.number_input("ЗП прочего персонала", 1000, 1000000, 300000, step=50000)
office_supplies = st.sidebar.number_input("Канцелярия, хозрасходы", 1000, 1000000, 10000, step=1000)
communication = st.sidebar.number_input("Связь", 1000, 1000000, 15000, step=1000)
bank_charges = st.sidebar.number_input("Банковские расходы", 1000, 1000000, 10000, step=1000)

# Процентные параметры
salary_tax_percent = st.sidebar.slider("Зарплатные налоги (%)", 0, 50, 30) / 100
delivery_percent = st.sidebar.slider("Доставка от поставщика (%)", 0, 10, 5) / 100

# Финансовые параметры
st.sidebar.subheader("Финансовые параметры")
initial_investment = st.sidebar.number_input("Инвестиции (руб.)", 
                                           value=2_000_000,
                                           format="%d",
                                           step=500_000)

loan_amount = st.sidebar.number_input("Кредит (руб.)", 
                                     value=2_000_000,
                                     format="%d",
                                     step=500_000)

interest_rate = st.sidebar.slider("Процентная ставка кредита (%)", 10.0, 40.0, 25.0) / 100
tax_rate = st.sidebar.slider("Налог на прибыль (%)", 6.0, 20.0, 20.0) / 100
months = st.sidebar.number_input("Срок прогноза (месяцев)", 
                                value=24, 
                                min_value=6, 
                                max_value=60)

def generate_financials(price=price_per_m2, sales=sales_m2, growth=growth_rate):
    df = pd.DataFrame(index=pd.date_range(start='2024-01-01', periods=months, freq='M'))
    
    df['Период'] = df.index.strftime('%b %y')
    
    # Расчет продаж с учетом роста
    current_sales = sales
    sales_growth = []
    for _ in range(months):
        sales_growth.append(current_sales)
        current_sales *= (1 + growth)
    
    df['Продажи м²'] = np.floor(sales_growth)
    df['Выручка'] = df['Продажи м²'] * price
    
    # Переменные затраты
    df['Сырьё'] = df['Выручка'] * (material_percent / 100)
    df['Произв. персонал'] = df['Выручка'] * (labor_percent / 100)
    df['Переменные затраты'] = df['Сырьё'] + df['Произв. персонал']
    
    # Постоянные затраты
    df['Аренда склада'] = rent_warehouse
    df['Аренда офиса'] = rent_office
    df['Коммуналка'] = utilities
    df['ЗП АУП'] = salary_management
    df['ЗП прочего персонала'] = salary_other
    df['Канцелярия'] = office_supplies
    df['Связь'] = communication
    df['Банковские расходы'] = bank_charges
    
    df['Зарплатные налоги'] = (df['ЗП АУП'] + df['ЗП прочего персонала']) * salary_tax_percent
    df['Доставка'] = df['Сырьё'] * delivery_percent
    
    df['Постоянные затраты'] = df[[
        'Аренда склада', 'Аренда офиса', 'Коммуналка',
        'ЗП АУП', 'ЗП прочего персонала', 'Канцелярия',
        'Связь', 'Банковские расходы', 'Зарплатные налоги', 'Доставка'
    ]].sum(axis=1)
    
    df['Амортизация'] = initial_investment / 60
    
    # Финансовые показатели
    df['Валовая прибыль'] = df['Выручка'] - df['Переменные затраты'] - df['Постоянные затраты']
    df['EBITDA'] = df['Валовая прибыль'] - df['Амортизация']
    
    # Расчет кредита
    monthly_rate = interest_rate / 12
    loan_payments = npf.pmt(monthly_rate, months, -loan_amount)
    principal = npf.ppmt(monthly_rate, np.arange(1, months+1), months, -loan_amount)
    interest = npf.ipmt(monthly_rate, np.arange(1, months+1), months, -loan_amount)
    
    df['Проценты'] = interest
    df['Погашение кредита'] = principal
    df['Прибыль до налога'] = df['EBITDA'] - df['Проценты']
    df['Налог'] = df['Прибыль до налога'].apply(lambda x: x * tax_rate if x > 0 else 0)
    df['Чистая прибыль'] = df['Прибыль до налога'] - df['Налог']
    
    # Денежные потоки
    df['Операционный поток'] = df['Чистая прибыль'] + df['Амортизация']
    df['Инвестиционный поток'] = -initial_investment / months
    df['Финансовый поток'] = 0
    df.loc[df.index[0], 'Финансовый поток'] = loan_amount  
    # Полный кредит в первом месяце
    df['Финансовый поток'] -= (df['Погашение кредита'] + df['Проценты'])    
    return df

df = generate_financials()

# Визуализация
st.title("🏠 Финансовая модель производителя домокомплектов")

col1, col2, col3 = st.columns(3)
col1.metric("Суммарная выручка", f"{df['Выручка'].sum()/1e6:.1f} млн руб.")
col2.metric("Общая чистая прибыль", f"{df['Чистая прибыль'].sum()/1e6:.1f} млн руб.")

cash_flows = [-initial_investment] + df['Чистая прибыль'].tolist()
npv_value = npf.npv(interest_rate/12, cash_flows)
col3.metric("NPV проекта", f"{npv_value/1e6:.1f} млн руб.")

fig1 = px.line(
    df, 
    x='Период',
    y=['Выручка', 'Чистая прибыль'],
    title="📈 Динамика выручки и прибыли",
    labels={'value': 'Рубли', 'variable': 'Показатель'}
)
st.plotly_chart(fig1, use_container_width=True)

fig2 = px.area(
    df, 
    x='Период',
    y=['Сырьё', 'Произв. персонал', 'Постоянные затраты', 'Проценты'],
    title="📉 Детализация затрат",
    labels={'value': 'Рубли', 'variable': 'Тип затрат'}
)
st.plotly_chart(fig2, use_container_width=True)

st.subheader("📊 Детальные данные")
display_df = df[['Период', 'Продажи м²', 'Выручка', 'Чистая прибыль', 
                'Сырьё', 'Произв. персонал', 'Постоянные затраты',
                'Проценты', 'Финансовый поток']].copy()

numeric_cols = display_df.select_dtypes(include=[np.number]).columns
format_dict = {col: lambda x: format_number(x) for col in numeric_cols}

st.dataframe(
    display_df.style.format(format_dict),
    height=400,
    use_container_width=True
)

# Анализ чувствительности
st.sidebar.header("🔍 Анализ чувствительности")
price_sens = st.sidebar.slider("Изменение цены за м² (%)", -20, 20, 0) / 100
sales_sens = st.sidebar.slider("Изменение объема продаж (%)", -30, 30, 0) / 100

if st.sidebar.button("Рассчитать сценарий"):
    new_price = price_per_m2 * (1 + price_sens)
    new_sales = sales_m2 * (1 + sales_sens)
    
    df_sens = generate_financials(
        price=new_price,
        sales=new_sales,
        growth=growth_rate
    )
    
    st.subheader(f"📌 Сценарий: Цена {price_sens*100:+.0f}%, Объем {sales_sens*100:+.0f}%")
    
    col1, col2 = st.columns(2)
    col1.metric("Новая выручка", 
               f"{df_sens['Выручка'].sum()/1e6:.1f} млн руб.",
               f"{(df_sens['Выручка'].sum() - df['Выручка'].sum())/1e6:+.1f} млн руб.")
    
    col2.metric("Новая чистая прибыль", 
               f"{df_sens['Чистая прибыль'].sum()/1e6:.1f} млн руб.",
               f"{(df_sens['Чистая прибыль'].sum() - df['Чистая прибыль'].sum())/1e6:+.1f} млн руб.")