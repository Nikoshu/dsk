import pandas as pd
import numpy as np
import numpy_financial as npf
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime
from pandas.tseries.offsets import DateOffset

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

# Сезонные коэффициенты (задерживаем их действие на 9 месяцев)
seasonal_coefficients = {
    'Январь': 0.7,
    'Февраль': 0.8,
    'Март': 1.0,
    'Апрель': 1.2,
    'Май': 1.4,
    'Июнь': 1.6,
    'Июль': 1.8,
    'Август': 1.6,
    'Сентябрь': 1.4,
    'Октябрь': 1.2,
    'Ноябрь': 1.0,
    'Декабрь': 0.8
}

# Раскрывающийся блок для переменных затрат
st.sidebar.subheader("Переменные затраты")
with st.sidebar.expander("➕ Посмотреть и изменить переменные затраты", expanded=False):
    material_percent = st.number_input("Сырьё (% от выручки)",
                                       min_value=0,
                                       max_value=100,
                                       value=30,
                                       format="%d",
                                       step=1)

    labor_percent = st.number_input("Производ. персонал (% от выручки)",
                                    min_value=0,
                                    max_value=30,
                                    value=10,
                                    format="%d",
                                    step=1)

    delivery_percent = st.number_input("Доставка от поставщика (% от стоимости сырья)",
                                       min_value=0,
                                       max_value=10,
                                       value=1,  # новое стартовое значение
                                       format="%d",
                                       step=1)

total_variable_percent = material_percent + labor_percent + delivery_percent
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

# Раскрывающийся блок для постоянных расходов
st.sidebar.subheader("Постоянные расходы")
with st.sidebar.expander("➕ Посмотреть и изменить постоянные расходы", expanded=False):
    rent_warehouse = st.number_input("Аренда склада", 1000, 1000000, 300000, step=10000)
    rent_office = st.number_input("Аренда офиса", 1000, 1000000, 50000, step=10000)
    utilities = st.number_input("Коммуналка", 1000, 1000000, 50000, step=1000)
    salary_management = st.number_input("ЗП АУП", 1000, 1000000, 300000, step=50000)
    salary_other = st.number_input("ЗП прочего персонала", 1000, 1000000, 300000, step=50000)
    office_supplies = st.number_input("Канцелярия, хозрасходы", 1000, 1000000, 10000, step=1000)
    communication = st.number_input("Связь", 1000, 1000000, 15000, step=1000)
    bank_charges = st.number_input("Банковские расходы", 1000, 1000000, 10000, step=1000)
    salary_tax_percent = st.number_input("Зарплатные налоги (%)",  # теперь в раскрывающемся блоке
                                        min_value=0,
                                        max_value=100,
                                        value=43,  # новое стартовое значение
                                        format="%d",
                                        step=1) / 100

# Рассчитываем динамический рост постоянных затрат
base_rent_warehouse = rent_warehouse
base_rent_office = rent_office
base_utilities = utilities
base_salary_management = salary_management
base_salary_other = salary_other
base_office_supplies = office_supplies
base_communication = communication
base_bank_charges = bank_charges

def calculate_fixed_expense(row_idx):
    # Повышаем затраты каждые 6 месяцев, начиная с 13-го месяца
    multiplier = 1 + ((max(row_idx - 12, 0)) // 6) * 1.0
    return [
        base_rent_warehouse * multiplier,
        base_rent_office * multiplier,
        base_utilities * multiplier,
        base_salary_management * multiplier,
        base_salary_other * multiplier,
        base_office_supplies * multiplier,
        base_communication * multiplier,
        base_bank_charges * multiplier
    ]

# Раскрывающийся блок для финансовых параметров
st.sidebar.subheader("Финансовые параметры")
with st.sidebar.expander("➕ Посмотреть и изменить финансовые параметры", expanded=False):
    initial_investment = st.number_input("Инвестиции (руб.)",
                                        value=2_000_000,
                                        format="%d",
                                        step=500_000)

    loan_amount = st.number_input("Кредит (руб.)",
                                 value=2_000_000,
                                 format="%d",
                                 step=500_000)

    loan_term_years = st.number_input("Срок кредита (лет)",
                                min_value=1,
                                max_value=5,
                                value=1,  # уменьшенный срок кредита
                                step=1)
    loan_term_months = loan_term_years * 12

    years = st.number_input("Период прогноза (лет)",
                            value=3,  # увеличенный период прогноза
                            min_value=1,
                            max_value=5,
                            step=1)

# Преобразуем годы в месяцы
months = years * 12

# Гарантированно делаем период прогноза не меньше срока кредита
if months < loan_term_months:
    months = loan_term_months

interest_rate = st.sidebar.slider("Процентная ставка кредита (%)",
                                10.0, 40.0, 25.0, step=1.0) / 100

tax_rate = st.sidebar.slider("Налог на прибыль (%)",
                           5.0, 20.0, 6.0, step=1.0) / 100

def generate_financials(price=price_per_m2, sales=sales_m2, growth=growth_rate):
    start_date = pd.Timestamp.now() + DateOffset(months=1)
    df = pd.DataFrame(index=pd.date_range(start=start_date, periods=months, freq='M'))
    
    df['Дата'] = df.index
    df['Период'] = df.index.strftime('%b %y')
    
    # Применение сезонных коэффициентов с задержкой на 9 месяцев
    df['Месяц'] = df['Дата'].dt.month.map({i+1: month for i, month in enumerate(list(seasonal_coefficients.keys()))})
    df['Сезонный коэффициент'] = df.apply(lambda row: seasonal_coefficients.get(row['Месяц'], 1.0) if row.name >= df.index[9] else 1.0, axis=1)
    
    # Расчет продаж
    current_sales = sales
    sales_growth = []
    for i in range(months):
        # Начинаем снижать прирост продаж с 24-го месяца
        effective_growth = growth_rate * (1 - 0.3) if i >= 24 else growth_rate
        sales_growth.append(current_sales)
        current_sales *= (1 + effective_growth)
    
    df['Продажи м²'] = np.floor(sales_growth) * df['Сезонный коэффициент']  # применяем сезонность
    df['Выручка'] = df['Продажи м²'] * price
    
    # Переменные затраты
    df['Сырьё'] = df['Выручка'] * (material_percent / 100)
    df['Произв. персонал'] = df['Выручка'] * (labor_percent / 100)
    df['Доставка'] = df['Сырьё'] * delivery_percent  # доставка от поставщика — переменный расход
    df['Переменные затраты'] = df['Сырьё'] + df['Произв. персонал'] + df['Доставка']
    
    # Постоянные затраты с увеличением каждые 6 месяцев после 12-го месяца
    fixed_expenses = [calculate_fixed_expense(idx) for idx in range(len(df))]
    df['Аренда склада'] = [expense[0] for expense in fixed_expenses]
    df['Аренда офиса'] = [expense[1] for expense in fixed_expenses]
    df['Коммуналка'] = [expense[2] for expense in fixed_expenses]
    df['ЗП АУП'] = [expense[3] for expense in fixed_expenses]
    df['ЗП прочего персонала'] = [expense[4] for expense in fixed_expenses]
    df['Канцелярия'] = [expense[5] for expense in fixed_expenses]
    df['Связь'] = [expense[6] for expense in fixed_expenses]
    df['Банковские расходы'] = [expense[7] for expense in fixed_expenses]
    
    df['Зарплатные налоги'] = (df['ЗП АУП'] + df['ЗП прочего персонала']) * salary_tax_percent
    df['Постоянные затраты'] = df[[
        'Аренда склада', 'Аренда офиса', 'Коммуналка',
        'ЗП АУП', 'ЗП прочего персонала', 'Канцелярия',
        'Связь', 'Банковские расходы', 'Зарплатные налоги'
    ]].sum(axis=1)
    
    # Финансовые показатели
    df['Валовая прибыль'] = df['Выручка'] - df['Переменные затраты']
    df['Амортизация'] = initial_investment / 60
    df['EBITDA'] = df['Валовая прибыль'] - df['Амортизация']
    
    # Профицит по кредиту
    monthly_rate = interest_rate / 12
    loan_payments = npf.pmt(monthly_rate, loan_term_months, -loan_amount)
    principal = npf.ppmt(monthly_rate, np.arange(1, loan_term_months+1), loan_term_months, -loan_amount)
    interest = npf.ipmt(monthly_rate, np.arange(1, loan_term_months+1), loan_term_months, -loan_amount)
    
    # Массивы полных платежей имеют длину равную прогнозу
    full_principal = np.zeros(months)
    full_interest = np.zeros(months)
    
    # Копируем погашение кредита и проценты только на месяцы кредита
    full_principal[:loan_term_months] = principal
    full_interest[:loan_term_months] = interest
    
    df['Проценты'] = full_interest
    df['Погашение кредита'] = full_principal
    
    # Прибыль до налогообложения
    df['Прибыль до налогообложения'] = df['EBITDA'] - df['Постоянные затраты'] - df['Проценты']
    
    # Налог на прибыль
    df['Налог на прибыль'] = df['Прибыль до налогообложения'].apply(lambda x: x * tax_rate if x > 0 else 0)
    
    # Чистая прибыль
    df['Чистая прибыль'] = df['Прибыль до налогообложения'] - df['Налог на прибыль']
    
    # Денежные потоки
    df['Операционный поток'] = df['Чистая прибыль'] + df['Амортизация']
    df['Инвестиционный поток'] = -initial_investment / months
    
    df['Финансовый поток'] = 0
    df.loc[df.index[0], 'Финансовый поток'] = loan_amount
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

# 1. Добавляем чистый доход рядом с выручкой в одном графике
fig1 = go.Figure(data=[
    go.Bar(name="Выручка", x=df["Период"], y=df["Выручка"]),
    go.Bar(name="Чистая прибыль", x=df["Период"], y=df["Чистая прибыль"], marker_color="green")
])
fig1.update_layout(barmode='group', title_text="Динамика выручки и прибыли")
st.plotly_chart(fig1, use_container_width=True)

# 2. Диаграмма затрат по месяцам (без группировки по кварталам)
fig2 = px.bar(
    df,
    x='Период',
    y=['Сырьё', 'Произв. персонал', 'Постоянные затраты', 'Проценты'],
    title="Подробная детализация затрат по месяцам",
    labels={'value': 'Рубли', 'Период': 'Месяцы'},
    barmode='stack'
)
st.plotly_chart(fig2, use_container_width=True)

# Исправленная секция таблицы
st.subheader("📊 Детальные данные")
display_df = df[[
    'Период',
    'Продажи м²',
    'Выручка',
    'Чистая прибыль',
    'Сырьё',
    'Произв. персонал',
    'Постоянные затраты',
    'Проценты',
    'Финансовый поток'
]].copy()

numeric_cols = display_df.select_dtypes(include=[np.number]).columns
format_dict = {col: lambda x: format_number(x) for col in numeric_cols}

formatted_df = display_df.style.format(format_dict)
formatted_df.hide(axis="index")  # Скрытие индекса с помощью .hide()
st.dataframe(formatted_df, height=400, use_container_width=True)

# Анализ чувствительности
st.sidebar.header("🔍 Анализ чувствительности")
price_sens = st.sidebar.slider("Изменение цены за м² (%)",
                              -20, 20, 0, step=1) / 100

sales_sens = st.sidebar.slider("Изменение объема продаж (%)",
                              -30, 30, 0, step=1) / 100

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
    
