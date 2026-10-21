"""Project 9: synthetic banking surveillance and explainable transaction review."""
import streamlit as st
import plotly.express as px
from monitoring import Thresholds, financial_analyses, generate_transactions, score_transactions, summary_metrics

st.set_page_config(page_title='Sentinel | Transaction Monitoring', page_icon='🏦', layout='wide')
st.markdown('''<style>
/* Streamlit's fixed toolbar overlaps content when top padding is only 2rem. */
.block-container {padding-top:5.5rem; padding-bottom:3rem; max-width:1500px}
h1 {font-size:clamp(1.8rem, 3.2vw, 2.8rem); overflow-wrap:anywhere; line-height:1.2}
[data-baseweb="tab-list"] {overflow-x:auto; gap:1rem}
[data-baseweb="tab"] {white-space:nowrap; flex-shrink:0}
.plan-card {background:#fff; border:1px solid #dce5ef; border-radius:14px; padding:1.5rem; margin-bottom:1rem}
.plan-premium {border:2px solid #087f8c; background:#edf9f8}
.plan-price {font-size:2rem; font-weight:700; color:#183153}
@media (max-width:768px) {
 .block-container {padding-top:6rem; padding-left:1rem; padding-right:1rem}
 [data-testid="stMetric"] {padding:12px}
}
h1,h2,h3 {letter-spacing:-.035em}
[data-testid="stMetric"] {background:white;border:1px solid #dce5ef;border-radius:12px;padding:20px;border-top:3px solid #087f8c}
[data-testid="stMetricLabel"] {color:#526581}
[data-testid="stSidebar"] {border-right:1px solid #dce5ef}
</style>''', unsafe_allow_html=True)
st.caption('SENTINEL  /  BANKING INTELLIGENCE  /  PROJECT 09')
st.title('Financial Fraud & Transaction Monitoring')
st.write('A transparent view of transaction activity, customer behavior, and alerts requiring review.')
st.info('SYNTHETIC DATA ONLY · Alerts do not prove fraud. Scores are rule-based review priorities, never probabilities of fraud.')
# Plan changes only affect the current Streamlit session; no billing or account data.
if 'plan' not in st.session_state:
    st.session_state.plan = 'Free'
def change_plan(plan):
    st.session_state.plan = plan
premium = st.session_state.plan == 'Premium'
st.caption('CURRENT PLAN · {} · {} · Simulated subscription, no payments'.format(
    st.session_state.plan, '$20/month' if premium else '$0/month'))
with st.sidebar:
    st.header('Detection controls')
    st.write('Current plan: **{}**'.format(st.session_state.plan))
    st.caption('Visit Pricing & subscription to switch plans. No payment required.')
    st.caption('Changes immediately update all scores and portfolio analyses.')
    count = st.number_input('Synthetic transactions', min_value=500 if premium else 250, max_value=10000 if premium else 250, value=500 if premium else 250, step=250, key='premium_count' if premium else 'free_count', disabled=not premium)
    seed = st.number_input('Random seed', min_value=0, max_value=1000000, value=9)
    st.divider()
    large = st.number_input('Large amount threshold ($)', min_value=1.0, value=5000.0, step=500.0)
    relative = st.slider('Customer-relative multiplier', 1.5, 10.0, 4.0, 0.5, disabled=not premium, key='relative_' + st.session_state.plan)
    history = st.slider('Minimum prior same-direction transactions', 1, 20, 5, disabled=not premium, key='history_' + st.session_state.plan)
    frequency = st.slider('Frequency count', 2, 30, 5)
    window = st.slider('Rolling window (minutes)', 1, 1440, 60, disabled=not premium, key='window_' + st.session_state.plan)
    cutoff = st.slider('Flag at risk score', 1, 100, 35, disabled=not premium, key='cutoff_' + st.session_state.plan)
    if not premium:
        relative, history, window, cutoff = 4.0, 5, 60, 35
        st.caption('Free includes dollar and frequency-count adjustments. Premium unlocks the remaining controls.')
    st.caption('35 amount + 25 relative amount + 30 frequency + 10 when multiple rules trigger = 100 maximum.')
try:
    data = score_transactions(generate_transactions(max(500, int(count)), int(seed)).head(int(count)),
        Thresholds(large, frequency, window, cutoff, relative, history))
    daily, accounts, channels = financial_analyses(data)
    metrics = summary_metrics(data)
except (ValueError, TypeError, OverflowError) as exc:
    st.error('Unable to analyze transactions: {}'.format(exc))
    st.stop()

cols = st.columns(4)
cols[0].metric('Transactions', '{:,}'.format(metrics['count']))
cols[1].metric('Total dollar volume', '${:,.0f}'.format(metrics['total']))
cols[2].metric('Average amount', '${:,.2f}'.format(metrics['average']))
cols[3].metric('Flagged transactions', '{:,}'.format(metrics['flagged_count']))
st.caption('{:.1f}% flagged · ${:,.2f} flagged volume · {} customers · January 2025 · USD · UTC'.format(metrics['flagged_pct'], metrics['flagged_value'], data.customer_id.nunique()))

COLORS = ['#087f8c', '#183153', '#e7a23b', '#cc5263']
def chart(fig):
    fig.update_layout(template='plotly_white', font=dict(color='#172b4d'),
                      paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                      margin=dict(l=10, r=10, t=30, b=10), height=320,
                      legend_title_text='')
    st.plotly_chart(fig, use_container_width=True, config={'displaylogo': False})

portfolio, review_tab, methodology, pricing = st.tabs(['Portfolio overview', 'Transaction review', 'Rules & calculations', 'Pricing & subscription'])
with portfolio:
    st.subheader('Transaction activity')
    volume = data.assign(day=data.timestamp.dt.floor('D')).groupby(['day', 'direction'], as_index=False).amount.sum()
    chart(px.bar(volume, x='day', y='amount', color='direction', color_discrete_sequence=COLORS,
                 labels={'day':'Date', 'amount':'Transaction value (USD)'}, barmode='stack'))
    left, right = st.columns(2)
    with left:
        st.subheader('Amount distribution')
        chart(px.histogram(data, x='amount', nbins=40, color_discrete_sequence=COLORS,
                           labels={'amount':'Transaction amount (USD)'}))
    if premium:
        with right:
            st.subheader('Risk score distribution')
            distribution = data.groupby('risk_score').size().reset_index(name='transactions')
            fig = px.bar(distribution, x='risk_score', y='transactions', color_discrete_sequence=COLORS,
                         labels={'risk_score':'Rule-based score (0–100)', 'transactions':'Transactions'})
            fig.add_vline(x=cutoff, line_dash='dash', line_color='#cc5263', annotation_text='Alert threshold')
            fig.update_xaxes(range=[-5, 105])
            chart(fig)
        left, right = st.columns(2)
        with left:
            st.subheader('Customer spending patterns')
            spending = data[data.direction == 'Debit'].groupby('customer_id').agg(spending=('amount','sum'), average_debit=('amount','mean'), payments=('amount','size')).sort_values('spending', ascending=False)
            chart(px.bar(spending.head(10).reset_index(), x='customer_id', y='spending', color_discrete_sequence=COLORS,
                         labels={'customer_id':'Customer', 'spending':'Debit spending (USD)'}))
            st.dataframe(spending.round(2), width='stretch')
        with right:
            st.subheader('Channel exposure')
            chart(px.bar(channels.reset_index(), x='channel', y=['total_value','flagged_value'], barmode='group', color_discrete_sequence=COLORS,
                         labels={'value':'Value (USD)', 'channel':'Channel'}))
            st.dataframe(channels.round(2), width='stretch')
    else:
        with right:
            st.info('Premium adds risk distributions, customer spending patterns, and channel exposure charts. Explore Pricing & subscription.')
    st.subheader('Cash flow & account concentration')
    a,b,c = st.columns(3)
    a.metric('Net flow', '${:,.2f}'.format(daily['Net flow'].sum()))
    b.metric('Top-five account share', '{:.1f}%'.format(accounts.head(5).value_share_pct.sum()))
    c.metric('High-frequency transactions', int(data.high_frequency.sum()))
    with st.expander('Cash flow and account detail'):
        st.dataframe(daily.round(2), width='stretch')
        st.dataframe(accounts.round(2), width='stretch')

with review_tab:
    st.subheader('Investigation queue')
    st.caption('Filters affect this table, transaction inspector, and CSV only. Portfolio metrics always include all records.')
    a,b,c,d = st.columns(4)
    customers = a.multiselect('Customer', sorted(data.customer_id.unique()), disabled=not premium)
    levels = b.multiselect('Risk level', ['Minimal','Low','Elevated','High'], disabled=not premium)
    selected_channels = c.multiselect('Transaction channel', sorted(data.channel.unique()), disabled=not premium)
    status = d.selectbox('Flag status', ['Flagged','All','Not flagged'])
    if not premium:
        customers, levels, selected_channels = [], [], []
        st.info('Premium unlocks customer, risk, and channel filters, CSV exports, and the detailed transaction inspector. Basic explanations remain available below.')
    review = data.copy()
    for column, selection in [('customer_id',customers), ('risk_level',levels), ('channel',selected_channels)]:
        if selection:
            review = review[review[column].isin(selection)]
    if status != 'All':
        review = review[review.flagged == (status == 'Flagged')]
    review = review.sort_values(['risk_score','timestamp'], ascending=[False,False])
    st.caption('{} matching records · ${:,.2f} transaction value'.format(len(review), review.amount.sum()))
    visible = ['transaction_id','customer_id','timestamp','amount','direction','channel','category','account_balance','risk_score','risk_level','flagged','explanation']
    st.dataframe(review[visible], width='stretch', hide_index=True,
                 column_config={'amount':st.column_config.NumberColumn('Amount (USD)',format='$%.2f'),
                                'account_balance':st.column_config.NumberColumn('Balance after (USD)',format='$%.2f'),
                                'risk_score':st.column_config.ProgressColumn('Risk score', min_value=0,max_value=100,format='%d')})
    if review.empty:
        st.success('No transactions match these filters. Adjust the filters to explore other records.')
    elif premium:
        st.subheader('Transaction inspector')
        tx = st.selectbox('Select transaction', review.transaction_id.tolist())
        row = review.set_index('transaction_id').loc[tx]
        st.write('**{} · {} · ${:,.2f} · Score {} / 100**'.format(tx,row.customer_id,row.amount,row.risk_score))
        st.write(row.explanation)
        st.caption('Prior same-direction records: {} · Prior mean: {} · Rolling count: {} · Demonstration scenario: {}'.format(
            row.history_count, '${:,.2f}'.format(row.prior_mean) if row.history_count else 'Unavailable', row.window_count,row.scenario))
    st.download_button('Download filtered CSV',review.to_csv(index=False).encode('utf-8'),'transaction_review.csv','text/csv', disabled=not premium)
with methodology:
    st.subheader('Transparent rules. Reviewable decisions.')
    st.markdown('''| Rule | Trigger | Points |
|---|---|---|
| Large amount | Amount ≥ selected dollar threshold | 35 |
| Customer-relative amount | Amount ≥ multiplier × prior same-direction customer mean; minimum history required | 25 |
| High frequency | Customer count in inclusive trailing window ≥ selected count | 30 |
| Multiple signals | At least two rules trigger | 10 |

Flag when score ≥ selected risk threshold. Scores are not probabilities. Risk labels: Minimal = 0, Low = 1–39, Elevated = 40–69, High = 70–100; labels are independent of the adjustable flag cutoff.

The customer baseline uses strictly earlier timestamps of the same direction. Simultaneous records cannot inflate their own baseline. With limited history, the relative rule is inactive; amount and frequency rules remain active. Frequency includes the current record and simultaneous records.

**Financial calculations**
- Gross dollar volume = sum of all positive transaction amounts, including credits and debits. Average amount = gross volume ÷ transaction count.
- Flag percentage = flagged count ÷ total count × 100. Flagged dollar volume = sum of amounts on flagged records; this is not a loss estimate.
- Customer spending = sum of debit amounts per customer. Average debit = customer spending ÷ debit count.
- Net flow = credits − debits; it is not a balance. Account concentration = account gross value ÷ portfolio gross value × 100.

**Synthetic assumptions:** fixed seed 9 by default; 30 customers, one account each, 30 days in January 2025. Most payments are debits. Ordinary amounts follow a capped lognormal distribution. Eight large payments and twelve rapid transfers are planted. Each account starts at $50,000; balance after each transaction adds credits and subtracts debits. Negative balances represent an illustrative credit facility. Scenario labels and balances do not contribute to scoring.

**Limitations:** illustrative rules and weights; no trained model, real fraud labels, performance claims, currency conversion, or real customer data. Prior means can be affected by earlier unusual payments. This prototype is for coursework, not production banking decisions. AI assisted implementation and testing; the student should review the methods, validate the results, and follow course disclosure requirements.''')

with pricing:
    st.subheader('Choose your monitoring plan')
    st.info('College project demonstration: subscriptions and payments are simulated. No charges, credit cards, or payment information. Selection lasts only for this browser session.')
    free_column, premium_column = st.columns(2)
    with free_column:
        st.markdown("""<div class="plan-card"><h3>Free Plan</h3><div class="plan-price">$0<span style="font-size:1rem"> / month</span></div><p>Explore the essentials of transaction monitoring.</p><ul><li>Up to 250 simulated transactions</li><li>Basic fraud monitoring and standard risk scoring</li><li>Basic charts and financial summaries</li><li>Dollar and frequency-count customization</li><li>Basic explanations for flagged records</li></ul></div>""", unsafe_allow_html=True)
        st.button('Switch to Free Plan', on_click=change_plan, args=('Free',), disabled=not premium, width='stretch')
    with premium_column:
        st.markdown("""<div class="plan-card plan-premium"><p><strong>FULL MONITORING WORKSPACE</strong></p><h3>Premium Plan</h3><div class="plan-price">$20<span style="font-size:1rem"> / month</span></div><p>Deeper insight. More control. Clearer investigations.</p><ul><li>Up to 10,000 simulated transactions</li><li>Advanced detection and all risk thresholds</li><li>Detailed financial and customer spending analytics</li><li>Additional charts and risk breakdowns</li><li>Full transaction filtering and CSV exports</li><li>Detailed individual alert inspector</li></ul></div>""", unsafe_allow_html=True)
        st.button('Upgrade to Premium — $20/month', on_click=change_plan, args=('Premium',), disabled=premium, type='primary', width='stretch')
    st.caption('Active plan: {}. Switching plans does not alter scoring weights or delete data. Free displays the first 250 chronological records from the reproducible 500-record source; Premium defaults to the full 500 and supports larger simulations.'.format(st.session_state.plan))
